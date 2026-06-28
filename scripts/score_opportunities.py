from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any

TARGET_DISCOUNT = 50_000
AGGRESSIVE_DISCOUNT = 70_000

INVENTORY_PATH = Path("data/inventario.json")
MARKET_LISTINGS_PATH = Path("data/market_listings.json")
KAVAK_CATALOG_LISTINGS_PATH = Path("data/kavak_catalog_listings.json")
MANUAL_MARKET_REFERENCES_PATH = Path("data/manual_market_references.json")
KAVAK_QUOTES_PATH = Path("data/kavak_quotes.json")
KAVAK_STATUS_RESULTS = {"capturado", "solo_prestamo", "modelo_no_disponible"}
MARKET_SOURCES = ["Facebook Marketplace", "MercadoLibre", "Kavak Catalogo", "Seminuevos", "Google"]


def positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def format_money(value: int | None) -> str:
    return f"${value:,}" if value is not None else "sin dato"


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


def vehicle_query(vehicle: dict[str, Any]) -> str:
    return f"{vehicle['brand']} {vehicle['model']} {vehicle['year']}"


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


def load_kavak_catalog_listings() -> list[dict[str, Any]]:
    if not KAVAK_CATALOG_LISTINGS_PATH.exists():
        return []
    payload = json.loads(KAVAK_CATALOG_LISTINGS_PATH.read_text(encoding="utf-8"))
    listings = payload.get("listings", payload if isinstance(payload, list) else [])
    valid: list[dict[str, Any]] = []
    for listing in listings:
        if not isinstance(listing.get("vehicleNo"), int):
            continue
        if not isinstance(listing.get("price"), int) or listing["price"] <= 0:
            continue
        if not listing.get("url") or not str(listing["url"]).startswith("http"):
            continue
        valid.append(listing)
    return valid


def load_manual_market_references() -> list[dict[str, Any]]:
    if not MANUAL_MARKET_REFERENCES_PATH.exists():
        return []
    references = json.loads(MANUAL_MARKET_REFERENCES_PATH.read_text(encoding="utf-8"))
    valid: list[dict[str, Any]] = []
    for reference in references:
        if not isinstance(reference.get("vehicleNo"), int):
            continue
        if not isinstance(reference.get("price"), int) or reference["price"] <= 0:
            continue
        if not reference.get("url") or not str(reference["url"]).startswith("http"):
            continue
        valid.append(reference)
    return valid


def _is_expired(valid_until: str, today: date) -> bool:
    try:
        return date.fromisoformat(valid_until) < today
    except ValueError:
        return False


def load_kavak_quotes() -> dict[int, dict[str, Any]]:
    if not KAVAK_QUOTES_PATH.exists():
        return {}
    quotes = json.loads(KAVAK_QUOTES_PATH.read_text(encoding="utf-8"))
    valid: dict[int, dict[str, Any]] = {}
    today = date.today()
    for quote in quotes:
        vehicle_no = quote.get("vehicleNo")
        status = quote.get("status") or "capturado"
        if not isinstance(vehicle_no, int):
            continue
        if not quote.get("url") or not str(quote["url"]).startswith("https://www.kavak.com/"):
            continue
        has_any_offer = any(positive_int(quote.get(field)) is not None for field in ["sellOffer", "tradeInOffer", "loanOffer"])
        if status not in KAVAK_STATUS_RESULTS and not has_any_offer:
            continue
        valid_until = quote.get("validUntil")
        if valid_until and _is_expired(valid_until, today):
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


def matching_catalog_listings(vehicle: dict[str, Any], listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [listing for listing in listings if listing.get("vehicleNo") == vehicle["no"]],
        key=lambda item: item["price"],
        reverse=True,
    )


def matching_manual_references(vehicle: dict[str, Any], references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [reference for reference in references if reference.get("vehicleNo") == vehicle["no"]],
        key=lambda item: item["price"],
        reverse=True,
    )


def search_url(vehicle: dict[str, Any], source: str, zone: str | None = None) -> str:
    query = vehicle_query(vehicle)
    if zone:
        query = f"{query} {zone}"
    if source == "Facebook Marketplace":
        return "https://www.facebook.com/marketplace/search/?query=" + urllib.parse.quote_plus(query)
    if source == "MercadoLibre":
        return "https://listado.mercadolibre.com.mx/" + urllib.parse.quote_plus(query)
    if source == "Kavak Catalogo":
        return "https://www.kavak.com/mx/seminuevos?keyword=" + urllib.parse.quote_plus(query)
    if source == "Seminuevos":
        return "https://www.seminuevos.com/buscar?keyword=" + urllib.parse.quote_plus(query)
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(f"{query} seminuevo precio")


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
        "query": listing.get("query"),
        "evidenceType": listing.get("evidenceType", "manual"),
        "screenshot": listing.get("screenshot"),
    }


def assisted_reference(vehicle: dict[str, Any], source: str) -> dict[str, Any]:
    query = vehicle_query(vehicle)
    return {
        "source": source,
        "label": f"Buscar {query} en {source}",
        "url": search_url(vehicle, source),
        "price": None,
        "kilometers": vehicle.get("kilometers"),
        "zone": "Nacional",
        "status": "asistido",
        "query": query,
        "evidenceType": "busqueda",
    }


def build_market_references(vehicle: dict[str, Any], listings: list[dict[str, Any]], catalog_listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query = vehicle_query(vehicle)
    references = [evidence_from_listing(listing) | {"query": query} for listing in listings[:8]]
    references.extend(evidence_from_listing(listing) | {"query": query} for listing in catalog_listings[:6])
    present_sources = {reference["source"] for reference in references}
    for source in MARKET_SOURCES:
        if source not in present_sources:
            references.append(assisted_reference(vehicle, source))
    return references


def market_price_range(references: list[dict[str, Any]]) -> dict[str, int] | None:
    prices = sorted(reference["price"] for reference in references if reference["price"] is not None)
    if not prices:
        return None
    middle_index = (len(prices) - 1) // 2
    return {
        "low": prices[0],
        "mid": prices[middle_index],
        "high": prices[-1],
        "count": len(prices),
    }


def deal_analysis(
    vehicle: dict[str, Any],
    target_price: int | None,
    aggressive_price: int | None,
    kavak_offer: int | None,
    price_range: dict[str, int] | None,
) -> dict[str, Any]:
    list_price = vehicle.get("inventoryPrice")
    kavak_best_offer = kavak_offer
    kavak_best_type = "venta" if kavak_offer is not None else None

    analysis = {
        "kavakBestOffer": kavak_best_offer,
        "kavakBestOfferType": kavak_best_type,
        "kavakVsList": kavak_best_offer - list_price if kavak_best_offer is not None and list_price is not None else None,
        "kavakVsListPct": round((kavak_best_offer - list_price) / list_price, 4)
        if kavak_best_offer is not None and list_price
        else None,
        "marketLowVsList": None,
        "marketMidVsList": None,
        "marketHighVsList": None,
        "marketLowVsTarget": None,
        "marketMidVsTarget": None,
        "marketHighVsTarget": None,
        "marketLowVsAggressive": None,
    }
    if price_range is None or list_price is None:
        return analysis

    analysis.update(
        {
            "marketLowVsList": price_range["low"] - list_price,
            "marketMidVsList": price_range["mid"] - list_price,
            "marketHighVsList": price_range["high"] - list_price,
            "marketLowVsTarget": price_range["low"] - target_price if target_price is not None else None,
            "marketMidVsTarget": price_range["mid"] - target_price if target_price is not None else None,
            "marketHighVsTarget": price_range["high"] - target_price if target_price is not None else None,
            "marketLowVsAggressive": price_range["low"] - aggressive_price if aggressive_price is not None else None,
        }
    )
    return analysis


def evidence_from_kavak_quote(quote: dict[str, Any]) -> dict[str, Any]:
    status = quote.get("status") or "capturado"
    sell_offer = positive_int(quote.get("sellOffer"))
    loan_offer = positive_int(quote.get("loanOffer"))
    if status == "modelo_no_disponible":
        label = quote.get("rawText") or "Kavak no mostro modelo/version compatible; no se sustituyo por otro modelo"
        price = None
    elif status == "solo_prestamo":
        label = f"Kavak solo ofrecio prestamo por {format_money(loan_offer)}; sin oferta de venta directa"
        price = None
    else:
        offer_label = "Venta en 7 dias" if quote.get("sellOfferType") == "venta_7_dias" else "Venta directa"
        label = f"{offer_label} Kavak capturada; vigente hasta {quote.get('validUntil')}"
        price = sell_offer

    return {
        "source": "Kavak",
        "label": label,
        "url": quote["url"],
        "price": price,
        "kilometers": None,
        "zone": "Nacional",
        "status": status,
        "observedAt": quote.get("capturedAt"),
        "publicationId": quote.get("flowId"),
    }


def build_opportunity(
    vehicle: dict[str, Any],
    market_listings: list[dict[str, Any]],
    catalog_listings: list[dict[str, Any]],
    manual_references: list[dict[str, Any]],
    kavak_quotes: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    list_price = vehicle["inventoryPrice"]
    target_price = max(0, list_price - TARGET_DISCOUNT) if list_price is not None else None
    aggressive_price = max(0, list_price - AGGRESSIVE_DISCOUNT) if list_price is not None else None
    listings = matching_listings(vehicle, market_listings)
    catalog_matches = matching_catalog_listings(vehicle, catalog_listings)
    manual_matches = matching_manual_references(vehicle, manual_references)
    kavak_quote = kavak_quotes.get(vehicle["no"])
    kavak_status = (kavak_quote.get("status") or "capturado") if kavak_quote is not None else "pendiente"
    kavak_offer = positive_int(kavak_quote.get("sellOffer")) if kavak_quote is not None else None
    kavak_trade_offer = positive_int(kavak_quote.get("tradeInOffer")) if kavak_quote is not None else None
    kavak_loan_offer = positive_int(kavak_quote.get("loanOffer")) if kavak_quote is not None else None

    market_references = build_market_references(vehicle, listings + manual_matches, catalog_matches)
    evidence = list(market_references)
    if kavak_quote is not None:
        evidence.insert(0, evidence_from_kavak_quote(kavak_quote))
    price_range = market_price_range(market_references)
    market_reference = price_range["mid"] if price_range is not None else None
    analysis = deal_analysis(
        vehicle,
        target_price,
        aggressive_price,
        kavak_offer,
        price_range,
    )
    priced_market_count = sum(1 for reference in market_references if reference["price"] is not None)
    if kavak_offer is not None and priced_market_count >= 1:
        confidence = 0.95
    elif kavak_offer is not None:
        confidence = 0.88
    else:
        confidence = 0.9 if priced_market_count >= 2 else 0.78 if priced_market_count == 1 else 0.0

    real_reference = max(
        (price for price in [market_reference, kavak_offer] if price is not None),
        default=None,
    )
    spread = real_reference - target_price if real_reference is not None and target_price is not None else None
    aggressive_spread = (
        real_reference - aggressive_price if real_reference is not None and aggressive_price is not None else None
    )
    has_real_reference = real_reference is not None
    status_multiplier = 1.2 if kavak_offer is not None else 1
    score = round(max(0, spread or 0) / 1000 * confidence * status_multiplier) if has_real_reference else 0

    notes = ["Precio lista ajustado con descuento fin de mes de 50k; escenario agresivo usa 70k."]
    if kavak_quote is not None:
        valid_until = kavak_quote.get("validUntil")
        if kavak_offer is not None:
            offer_label = "Kavak venta en 7 dias capturado" if kavak_quote.get("sellOfferType") == "venta_7_dias" else "Kavak venta directa capturado"
            parts = [f"{offer_label}: {format_money(kavak_offer)}"]
            if kavak_loan_offer is not None:
                parts.append(f"prestamo: {format_money(kavak_loan_offer)}")
            if valid_until:
                parts.append(f"vigente hasta {valid_until}")
            notes.append("; ".join(parts) + ".")
        elif kavak_status == "solo_prestamo":
            parts = [f"Kavak no dio oferta de venta directa; solo prestamo: {format_money(kavak_loan_offer)}"]
            if valid_until:
                parts.append(f"vigente hasta {valid_until}")
            notes.append("; ".join(parts) + ".")
        elif kavak_status == "modelo_no_disponible":
            notes.append(quote_text if (quote_text := kavak_quote.get("rawText")) else "Kavak no mostro modelo/version compatible; no se sustituyo por otro modelo.")
        else:
            notes.append("Kavak tiene resultado capturado sin oferta de venta utilizable.")
        if list_price is not None and kavak_offer is not None and kavak_offer < list_price:
            notes.append(f"Kavak venta directa queda ${list_price - kavak_offer:,} debajo del precio de lista.")
    else:
        notes.append("Kavak sin resultado capturado.")
    if market_reference is not None:
        notes.append("Referencia de mercado usa publicaciones reales capturadas; no es precio vendido.")
        if spread is not None and spread > 0:
            notes.append("Spread positivo contra precio objetivo de fin de mes.")
    else:
        notes.append(f"Sin precio de venta capturado para {vehicle_query(vehicle)}; las referencias asistidas no suman spread.")

    return {
        "vehicle": vehicle,
        "kavakStatus": kavak_status,
        "kavakOffer": kavak_offer,
        "kavakTradeOffer": None,
        "kavakLoanOffer": kavak_loan_offer,
        "kavakSellOfferType": kavak_quote.get("sellOfferType") if kavak_quote is not None else None,
        "marketReference": market_reference,
        "marketPriceRange": price_range,
        "targetBuyPrice": target_price,
        "aggressiveBuyPrice": aggressive_price,
        "spread": spread,
        "aggressiveSpread": aggressive_spread,
        "confidence": confidence,
        "score": score,
        "dealAnalysis": analysis,
        "marketReferences": market_references,
        "evidence": evidence,
        "notes": notes,
    }


def main() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    market_listings = load_market_listings()
    catalog_listings = load_kavak_catalog_listings()
    manual_references = load_manual_market_references()
    kavak_quotes = load_kavak_quotes()
    opportunities = [
        build_opportunity(vehicle, market_listings, catalog_listings, manual_references, kavak_quotes)
        for vehicle in inventory
        if not vehicle["excludedOrange"]
    ]
    opportunities.sort(key=lambda item: (item["score"], item["spread"] or -10**9), reverse=True)

    for output in [Path("data/opportunities.json"), Path("src/data/opportunities.json")]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(opportunities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    all_quotes_raw = json.loads(KAVAK_QUOTES_PATH.read_text(encoding="utf-8")) if KAVAK_QUOTES_PATH.exists() else []
    today = date.today()
    expired_quotes = sum(
        1 for q in all_quotes_raw
        if q.get("validUntil") and _is_expired(q["validUntil"], today)
    )
    print(
        json.dumps(
            {
                "opportunities": len(opportunities),
                "publishedMarketListings": len(market_listings),
                "kavakCatalogListings": len(catalog_listings),
                "manualMarketReferences": len(manual_references),
                "capturedKavakQuotes": len(kavak_quotes),
                "expiredKavakQuotes": expired_quotes,
                "loanOnlyKavakQuotes": sum(1 for quote in kavak_quotes.values() if quote.get("status") == "solo_prestamo"),
                "noModelKavakResults": sum(1 for quote in kavak_quotes.values() if quote.get("status") == "modelo_no_disponible"),
                "withMarketReference": sum(1 for item in opportunities if item["marketReference"] is not None),
                "withKavakOffer": sum(1 for item in opportunities if item["kavakOffer"] is not None),
                "positiveSpread": sum(1 for item in opportunities if (item["spread"] or 0) > 0),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
