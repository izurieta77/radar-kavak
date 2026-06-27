from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Any

TARGET_DISCOUNT = 50_000
AGGRESSIVE_DISCOUNT = 70_000

INVENTORY_PATH = Path("data/inventario.json")
MARKET_LISTINGS_PATH = Path("data/market_listings.json")
KAVAK_QUOTES_PATH = Path("data/kavak_quotes.json")


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")


def vehicle_family(vehicle: dict[str, Any]) -> str | None:
    text = normalize(f"{vehicle['brand']} {vehicle['model']}")
    if "bmw" in text and "x4" in text:
        return "BMW X4"
    if "tesla" in text and "model y" in text:
        return "Tesla Model Y"
    if "land-rover" in text or "land rover" in text:
        if "velar" in text:
            return "Land Rover Velar"
    if "volvo" in text and "xc60" in text:
        return "Volvo XC60"
    if "mini" in text and "countryman" in text:
        return "MINI Countryman"
    if "kia" in text and "seltos" in text:
        return "KIA Seltos"
    if "mercedes" in text and "gls" in text:
        return "Mercedes GLS"
    if "ford" in text and "expedition" in text:
        return "Ford Expedition"
    return None


def load_market_listings() -> list[dict[str, Any]]:
    if not MARKET_LISTINGS_PATH.exists():
        return []
    listings = json.loads(MARKET_LISTINGS_PATH.read_text(encoding="utf-8"))
    valid: list[dict[str, Any]] = []
    for listing in listings:
        if not listing.get("url") or not str(listing["url"]).startswith("http"):
            continue
        if not isinstance(listing.get("price"), int) or listing["price"] <= 0:
            continue
        if not listing.get("family") or not listing.get("year"):
            continue
        valid.append(listing)
    return valid


def load_kavak_quotes() -> dict[int, dict[str, Any]]:
    if not KAVAK_QUOTES_PATH.exists():
        return {}
    quotes = json.loads(KAVAK_QUOTES_PATH.read_text(encoding="utf-8"))
    valid: dict[int, dict[str, Any]] = {}
    for quote in quotes:
        vehicle_no = quote.get("vehicleNo")
        sell_offer = quote.get("sellOffer")
        if not isinstance(vehicle_no, int):
            continue
        if not isinstance(sell_offer, int) or sell_offer <= 0:
            continue
        if not quote.get("url") or not str(quote["url"]).startswith("https://www.kavak.com/"):
            continue
        valid[vehicle_no] = quote
    return valid


def matching_listings(vehicle: dict[str, Any], listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family = vehicle_family(vehicle)
    if family is None:
        return []
    matches = [
        listing
        for listing in listings
        if listing.get("family") == family and int(listing.get("year", 0)) == int(vehicle["year"])
    ]
    return sorted(matches, key=lambda item: item["price"], reverse=True)


def search_url(vehicle: dict[str, Any], zone: str) -> str:
    query = f"{vehicle['brand']} {vehicle['model']} {vehicle['year']} {zone} seminuevo"
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def evidence_from_listing(listing: dict[str, Any]) -> dict[str, Any]:
    zone = listing.get("searchZone") if listing.get("searchZone") in {"Toluca", "CDMX", "Metepec"} else "Nacional"
    return {
        "source": listing["source"],
        "label": f"{listing['title']} publicado en {listing['location']}",
        "url": listing["url"],
        "price": listing["price"],
        "kilometers": None,
        "zone": zone,
        "status": "publicado",
        "observedAt": listing.get("observedAt"),
        "publicationId": listing.get("publicationId"),
    }


def evidence_from_kavak_quote(quote: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "Kavak",
        "label": f"Venta directa Kavak capturada; vigente hasta {quote.get('validUntil')}",
        "url": quote["url"],
        "price": quote["sellOffer"],
        "kilometers": None,
        "zone": "Nacional",
        "status": "capturado",
        "observedAt": quote.get("capturedAt"),
        "publicationId": quote.get("flowId"),
    }


def build_opportunity(
    vehicle: dict[str, Any], market_listings: list[dict[str, Any]], kavak_quotes: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    list_price = vehicle["inventoryPrice"]
    target_price = max(0, list_price - TARGET_DISCOUNT) if list_price is not None else None
    aggressive_price = max(0, list_price - AGGRESSIVE_DISCOUNT) if list_price is not None else None
    listings = matching_listings(vehicle, market_listings)
    kavak_quote = kavak_quotes.get(vehicle["no"])
    kavak_offer = kavak_quote["sellOffer"] if kavak_quote is not None else None

    evidence = [evidence_from_listing(listing) for listing in listings[:8]]
    if kavak_quote is not None:
        evidence.insert(0, evidence_from_kavak_quote(kavak_quote))
    market_reference = max((listing["price"] for listing in listings), default=None)
    if kavak_quote is not None and len(listings) >= 1:
        confidence = 0.95
    elif kavak_quote is not None:
        confidence = 0.88
    else:
        confidence = 0.9 if len(listings) >= 2 else 0.78 if len(listings) == 1 else 0.0

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

    real_reference = max(
        (price for price in [market_reference, kavak_offer] if price is not None),
        default=None,
    )
    spread = real_reference - target_price if real_reference is not None and target_price is not None else None
    aggressive_spread = (
        real_reference - aggressive_price if real_reference is not None and aggressive_price is not None else None
    )
    has_real_reference = real_reference is not None
    status_multiplier = 1.2 if kavak_quote is not None else 1
    score = round(max(0, spread or 0) / 1000 * confidence * status_multiplier) if has_real_reference else 0

    notes = ["Precio lista ajustado con descuento fin de mes de 50k; escenario agresivo usa 70k."]
    if kavak_quote is not None:
        trade_in_offer = kavak_quote.get("tradeInOffer")
        loan_offer = kavak_quote.get("loanOffer")
        valid_until = kavak_quote.get("validUntil")
        notes.append(
            f"Kavak venta directa capturado: ${kavak_offer:,}; cambio/trueque: ${trade_in_offer:,}; "
            f"prestamo: ${loan_offer:,}; vigente hasta {valid_until}."
        )
        if list_price is not None and trade_in_offer is not None and trade_in_offer > list_price:
            notes.append(f"Kavak cambio/trueque queda ${trade_in_offer - list_price:,} arriba del precio de lista.")
        if list_price is not None and kavak_offer is not None and kavak_offer < list_price:
            notes.append(f"Kavak venta directa queda ${list_price - kavak_offer:,} debajo del precio de lista.")
    else:
        notes.append("Kavak pendiente: capturar oferta real antes de comprar.")
    if market_reference is not None:
        notes.append("Referencia de mercado usa publicaciones reales capturadas; no es precio vendido.")
        if spread is not None and spread > 0:
            notes.append("Spread positivo contra precio objetivo de fin de mes.")
    else:
        notes.append("Sin publicacion real capturada para este anio/modelo; links asistidos no suman spread.")

    return {
        "vehicle": vehicle,
        "kavakStatus": "capturado" if kavak_quote is not None else "pendiente",
        "kavakOffer": kavak_offer,
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
    market_listings = load_market_listings()
    kavak_quotes = load_kavak_quotes()
    opportunities = [
        build_opportunity(vehicle, market_listings, kavak_quotes)
        for vehicle in inventory
        if not vehicle["excludedOrange"]
    ]
    opportunities.sort(key=lambda item: (item["score"], item["spread"] or -10**9), reverse=True)

    for output in [Path("data/opportunities.json"), Path("src/data/opportunities.json")]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(opportunities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "opportunities": len(opportunities),
                "publishedMarketListings": len(market_listings),
                "capturedKavakQuotes": len(kavak_quotes),
                "withMarketReference": sum(1 for item in opportunities if item["marketReference"] is not None),
                "withKavakOffer": sum(1 for item in opportunities if item["kavakOffer"] is not None),
                "positiveSpread": sum(1 for item in opportunities if (item["spread"] or 0) > 0),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
