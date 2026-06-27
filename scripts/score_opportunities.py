from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TARGET_DISCOUNT = 50_000
AGGRESSIVE_DISCOUNT = 70_000
LIVE_MARKET_LIMIT = int(os.environ.get("RADAR_KAVAK_LIVE_MARKET_LIMIT", "0"))

KNOWN_REFERENCES: dict[str, dict[str, int]] = {
    "https://www.seminuevos.com/precio/autos/bmw/x4/2024": {
        "ideal": 1_024_281,
        "low": 849_000,
        "high": 1_589_000,
    }
}

INVENTORY_PATH = Path("data/inventario.json")


@dataclass(frozen=True)
class MarketKey:
    brand_slug: str
    model_slug: str
    confidence: float
    label: str


def slugify(value: str) -> str:
    normalized = (
        value.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized


def market_key(vehicle: dict[str, Any]) -> MarketKey | None:
    brand = vehicle["brand"].strip()
    model = vehicle["model"].strip()
    text = f"{brand} {model}".lower()

    brand_map = {
        "BMW": "bmw",
        "MINI": "mini",
        "Mini": "mini",
        "Land-Rover": "land-rover",
        "Mercedes-Benz": "mercedes-benz",
        "Tesla": "tesla",
        "KIA": "kia",
        "Volvo": "volvo",
        "Volkswagen": "volkswagen",
        "Ford": "ford",
    }
    brand_slug = brand_map.get(brand)
    if not brand_slug:
        return None

    patterns: list[tuple[str, str, float]] = [
        (r"\bx1\b", "x1", 0.9),
        (r"\bx2\b", "x2", 0.9),
        (r"\bx3\b", "x3", 0.9),
        (r"\bx4\b", "x4", 0.95),
        (r"\bx5\b", "x5", 0.95),
        (r"\bx7\b", "x7", 0.9),
        (r"\bix3\b", "ix3", 0.85),
        (r"\bix\b", "ix", 0.85),
        (r"\b330e\b", "serie-3", 0.72),
        (r"\b118i\b", "serie-1", 0.72),
        (r"\bm5\b", "serie-5", 0.65),
        (r"\bmodel y\b", "model-y", 0.9),
        (r"\bcooper\b", "cooper", 0.78),
        (r"\bcountryman\b", "countryman", 0.86),
        (r"\bseltos\b", "seltos", 0.9),
        (r"\bxc60\b", "xc60", 0.9),
        (r"\bex30\b", "ex30", 0.85),
        (r"\bgls\b", "gls", 0.82),
        (r"\ba 35\b", "clase-a", 0.65),
        (r"\bterramont\b", "terramont", 0.9),
        (r"\bexpedition\b", "expedition", 0.9),
        (r"\bvelar\b", "range-rover-velar", 0.78),
        (r"\brange-rover sport\b", "range-rover-sport", 0.82),
    ]
    for pattern, slug, confidence in patterns:
        if re.search(pattern, text):
            return MarketKey(brand_slug, slug, confidence, f"{brand} {slug}")
    return MarketKey(brand_slug, slugify(model.split()[0]), 0.45, f"{brand} {model}")


def seminuevos_url(key: MarketKey, year: int) -> str:
    return f"https://www.seminuevos.com/precio/autos/{key.brand_slug}/{key.model_slug}/{year}"


def parse_money(value: str) -> int:
    return int(re.sub(r"[^\d]", "", value))


def fetch_seminuevos_reference(url: str) -> dict[str, int] | None:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RadarKavak/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            html = response.read().decode("utf-8", "ignore")
    except Exception:
        return None

    ideal_index = html.find("Precio ideal")
    if ideal_index == -1:
        return None

    chunk = html[ideal_index : ideal_index + 1200]
    amounts = [parse_money(match.group(0)) for match in re.finditer(r"\$[0-9,]+", chunk)]
    if len(amounts) < 3:
        return None
    return {
        "ideal": amounts[0],
        "low": min(amounts[1], amounts[2]),
        "high": max(amounts[1], amounts[2]),
    }


def search_url(vehicle: dict[str, Any], zone: str) -> str:
    query = f"{vehicle['brand']} {vehicle['model']} {vehicle['year']} {zone}"
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def build_opportunity(
    vehicle: dict[str, Any],
    reference_cache: dict[str, dict[str, int] | None],
    fetch_budget: dict[str, int],
) -> dict[str, Any]:
    list_price = vehicle["inventoryPrice"]
    target_price = max(0, list_price - TARGET_DISCOUNT) if list_price is not None else None
    aggressive_price = max(0, list_price - AGGRESSIVE_DISCOUNT) if list_price is not None else None
    key = market_key(vehicle)

    evidence: list[dict[str, Any]] = []
    market_reference = None
    confidence = 0.28

    if key:
        url = seminuevos_url(key, vehicle["year"])
        cache_key = url
        if cache_key not in reference_cache:
            if cache_key in KNOWN_REFERENCES:
                reference_cache[cache_key] = KNOWN_REFERENCES[cache_key]
            elif fetch_budget["remaining"] > 0:
                reference_cache[cache_key] = fetch_seminuevos_reference(url)
                fetch_budget["remaining"] -= 1
                time.sleep(0.15)
            else:
                reference_cache[cache_key] = None
        reference = reference_cache[cache_key]
        if reference:
            market_reference = reference["ideal"]
            confidence = min(0.92, key.confidence)
            evidence.append(
                {
                    "source": "Seminuevos",
                    "label": f"Precio ideal {key.label} {vehicle['year']}",
                    "url": url,
                    "price": reference["ideal"],
                    "kilometers": None,
                    "zone": "Nacional",
                    "status": "scrapeable",
                }
            )
            evidence.append(
                {
                    "source": "Seminuevos",
                    "label": f"Rango bajo-alto {reference['low']:,}-{reference['high']:,}",
                    "url": url,
                    "price": reference["low"],
                    "kilometers": None,
                    "zone": "Nacional",
                    "status": "scrapeable",
                }
            )
        else:
            evidence.append(
                {
                    "source": "Seminuevos",
                    "label": f"Referencia pendiente {key.label} {vehicle['year']}",
                    "url": url,
                    "price": None,
                    "kilometers": None,
                    "zone": "Nacional",
                    "status": "pendiente",
                }
            )

    for zone in ["Toluca", "CDMX", "Metepec"]:
        evidence.append(
            {
                "source": "Busqueda",
                "label": f"Buscar comparables en {zone}",
                "url": search_url(vehicle, zone),
                "price": None,
                "kilometers": None,
                "zone": zone,
                "status": "asistido",
            }
        )

    spread = market_reference - target_price if market_reference is not None and target_price is not None else None
    aggressive_spread = (
        market_reference - aggressive_price if market_reference is not None and aggressive_price is not None else None
    )
    status_factor = 0.72
    score = round(max(0, spread or 0) / 1000 * confidence * status_factor)

    notes = [
        "Kavak pendiente: capturar oferta real antes de comprar.",
        "Precio lista ajustado con descuento fin de mes de 50k; escenario agresivo usa 70k.",
    ]
    if market_reference is None:
        notes.append("Sin referencia scrapeable; usar links asistidos por zona.")
    elif spread is not None and spread > 0:
        notes.append("Spread positivo contra precio objetivo de fin de mes.")

    return {
        "vehicle": vehicle,
        "kavakStatus": "pendiente",
        "kavakOffer": None,
        "marketReference": market_reference,
        "targetBuyPrice": target_price,
        "aggressiveBuyPrice": aggressive_price,
        "spread": spread,
        "aggressiveSpread": aggressive_spread,
        "confidence": confidence,
        "score": score,
        "evidence": evidence,
        "notes": notes,
    }


def main() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    reference_cache: dict[str, dict[str, int] | None] = {}
    fetch_budget = {"remaining": LIVE_MARKET_LIMIT}
    opportunities = [
        build_opportunity(vehicle, reference_cache, fetch_budget)
        for vehicle in inventory
        if not vehicle["excludedOrange"]
    ]
    opportunities.sort(key=lambda item: (item["score"], item["aggressiveSpread"] or -10**9), reverse=True)

    for output in [Path("data/opportunities.json"), Path("src/data/opportunities.json")]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(opportunities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "opportunities": len(opportunities),
                "withMarketReference": sum(1 for item in opportunities if item["marketReference"] is not None),
                "positiveSpread": sum(1 for item in opportunities if (item["spread"] or 0) > 0),
                "liveMarketFetchLimit": LIVE_MARKET_LIMIT,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
