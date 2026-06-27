from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INVENTORY_PATH = Path("data/inventario.json")
OUTPUT_PATH = Path("data/kavak_catalog_listings.json")

BRAND_SLUGS = {
    "BMW": "bmw",
    "MINI": "mini",
    "Mercedes-Benz": "mercedes-benz",
    "Land-Rover": "land-rover",
    "Volvo": "volvo",
    "KIA": "kia",
    "Ford": "ford",
    "Volkswagen": "volkswagen",
    "Tesla": "tesla",
}


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")


def vehicle_query(vehicle: dict[str, Any]) -> str:
    return f"{vehicle['brand']} {vehicle['model']} {vehicle['year']}"


def model_slug(vehicle: dict[str, Any]) -> str | None:
    text = normalize(vehicle["model"])
    brand = vehicle["brand"]
    if brand == "BMW":
        if "330" in text:
            return "serie-3"
        if "118" in text:
            return "serie-1"
        if "ix3" in text:
            return "ix3"
        if re.search(r"\bix\b", text):
            return "ix"
        for slug in ["x1", "x2", "x3", "x4", "x5", "xm", "m5"]:
            if slug in text:
                return slug
    if brand == "MINI":
        if "countryman" in text:
            return "countryman"
        if "cooper" in text:
            return "cooper"
    if brand == "Mercedes-Benz":
        if "gls" in text:
            return "gls"
        if "a 35" in text or "amg" in text:
            return "clase-a"
    if brand == "Land-Rover":
        if "velar" in text:
            return "range-rover-velar"
        if "sport" in text:
            return "range-rover-sport"
    if brand == "Volvo":
        if "xc60" in text:
            return "xc60"
        if "ex30" in text:
            return "ex30"
    if brand == "KIA" and "seltos" in text:
        return "seltos"
    if brand == "Ford" and "expedition" in text:
        return "expedition"
    if brand == "Volkswagen" and "terramont" in text:
        return "teramont"
    if brand == "Tesla" and "model y" in text:
        return "model-y"
    return None


def catalog_url(vehicle: dict[str, Any]) -> str | None:
    brand_slug = BRAND_SLUGS.get(vehicle["brand"])
    slug = model_slug(vehicle)
    if not brand_slug or not slug:
        return None
    return f"https://www.kavak.com/mx/seminuevos/{brand_slug}/{slug}/{vehicle['year']}"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def extract_cars(page_text: str) -> list[dict[str, Any]]:
    marker = 'cars\\":['
    start = page_text.find(marker)
    if start < 0:
        return []
    index = start + len(marker) - 1
    depth = 0
    for offset in range(index, len(page_text)):
        char = page_text[offset]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                raw = page_text[index : offset + 1]
                return json.loads(raw.replace('\\"', '"'))
    return []


def has_terms(text: str, *terms: str) -> bool:
    normalized = normalize(text)
    return all(term in normalized for term in terms)


def is_exact_match(vehicle: dict[str, Any], car: dict[str, Any]) -> bool:
    title = car.get("title") or ""
    subtitle = car.get("subtitle") or ""
    text = f"{title} {subtitle}"
    normalized = normalize(text)
    if str(vehicle["year"]) not in normalized:
        return False

    model = normalize(vehicle["model"])
    brand = vehicle["brand"]
    if brand == "BMW":
        if "m5" in model:
            return has_terms(text, "m5")
        if "118" in model:
            return has_terms(text, "serie 1", "118")
        if "330" in model:
            return has_terms(text, "serie 3", "330")
        if "ix3" in model:
            return has_terms(text, "ix3")
        if re.search(r"\bix\b", model):
            trim = "xdrive50" if "50" in model else "xdrive40" if "40" in model else "ix"
            return has_terms(text, "ix", trim)
        for slug in ["x1", "x2", "x3", "x4", "x5", "xm"]:
            if slug in model:
                if slug == "x4" and "m40" in model:
                    return has_terms(text, "x4", "m40")
                if slug == "x4" and "30i" in model:
                    return has_terms(text, "x4", "30i")
                if slug == "x5" and "40i" in model:
                    return has_terms(text, "x5", "40i")
                if slug == "x5" and "45e" in model:
                    return has_terms(text, "x5", "45e")
                if slug == "x5" and "50e" in model:
                    return has_terms(text, "x5", "50e")
                if slug == "x3" and "30e" in model:
                    return has_terms(text, "x3", "30e")
                return has_terms(text, slug)
    if brand == "MINI":
        if "convertible" in model:
            return has_terms(text, "cooper", "convertible")
        if "countryman" in model:
            return has_terms(text, "countryman")
        if "cooper se" in model:
            return has_terms(text, "cooper", "se")
        return has_terms(text, "cooper")
    if brand == "Mercedes-Benz":
        if "gls" in model:
            return has_terms(text, "gls", "450")
        return has_terms(text, "a 35") or has_terms(text, "amg", "35")
    if brand == "Land-Rover":
        if "velar" in model:
            return has_terms(text, "velar")
        return has_terms(text, "range rover", "sport")
    if brand == "Volvo":
        return has_terms(text, "xc60") if "xc60" in model else has_terms(text, "ex30")
    if brand == "KIA":
        return has_terms(text, "seltos")
    if brand == "Ford":
        return has_terms(text, "expedition")
    if brand == "Volkswagen":
        return has_terms(text, "terramont") or has_terms(text, "teramont")
    if brand == "Tesla":
        return has_terms(text, "model y")
    return False


def parse_price(car: dict[str, Any]) -> int | None:
    analytics_price = car.get("analytics", {}).get("car_price")
    if isinstance(analytics_price, str) and analytics_price.isdigit():
        return int(analytics_price)
    main_price = car.get("mainPrice")
    if isinstance(main_price, str):
        digits = re.sub(r"\D", "", main_price)
        return int(digits) if digits else None
    return None


def listing_from_car(vehicle: dict[str, Any], url: str, car: dict[str, Any], observed_at: str) -> dict[str, Any] | None:
    price = parse_price(car)
    if price is None:
        return None
    analytics = car.get("analytics", {})
    return {
        "vehicleNo": vehicle["no"],
        "source": "Kavak Catalogo",
        "query": vehicle_query(vehicle),
        "title": f"{car.get('title')} {car.get('subtitle')}",
        "price": price,
        "location": analytics.get("car_location") or car.get("footerInfo") or "Kavak",
        "searchZone": "Nacional",
        "url": car.get("url") or url,
        "searchUrl": url,
        "publicationId": str(car.get("id") or analytics.get("car_id") or ""),
        "observedAt": observed_at,
        "evidenceType": "html",
    }


def main() -> None:
    vehicles = [vehicle for vehicle in json.loads(INVENTORY_PATH.read_text(encoding="utf-8")) if not vehicle["excludedOrange"]]
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    listings: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []

    for vehicle in vehicles:
        url = catalog_url(vehicle)
        if url is None:
            misses.append({"vehicleNo": vehicle["no"], "reason": "sin_url_catalogo"})
            continue
        try:
            cars = extract_cars(fetch(url))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            misses.append({"vehicleNo": vehicle["no"], "url": url, "reason": str(error)})
            continue

        exact = [car for car in cars if is_exact_match(vehicle, car)]
        for car in exact[:6]:
            listing = listing_from_car(vehicle, url, car, observed_at)
            if listing is not None:
                listings.append(listing)
        if not exact:
            misses.append({"vehicleNo": vehicle["no"], "url": url, "reason": "sin_match_exacto"})
        time.sleep(0.15)

    OUTPUT_PATH.write_text(json.dumps({"listings": listings, "misses": misses}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"kavakCatalogListings": len(listings), "misses": len(misses)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
