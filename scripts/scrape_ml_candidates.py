from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "data" / "inventario.json"
KAVAK_QUOTES_PATH = ROOT / "data" / "kavak_quotes.json"
EXTERNAL_BARGAINS_PATH = ROOT / "src" / "data" / "external_bargains.json"
EXTERNAL_QUOTES_PATH = ROOT / "src" / "data" / "external_kavak_quotes.json"
DIRECT_TARGETS_PATH = ROOT / "src" / "data" / "direct_sale_market_targets.json"
OUTPUT_JSON = ROOT / "data" / "ml_candidates.json"
OUTPUT_DIRECT_JSON = ROOT / "data" / "direct_sale_market_targets.json"
OUTPUT_DIR = ROOT / "output" / "evidence"

ALLOWED_REGION_KEYS = {
    "distrito federal": "CDMX",
    "ciudad de mexico": "CDMX",
    "cdmx": "CDMX",
    "estado de mexico": "Edomex",
    "edomex": "Edomex",
    "morelos": "Morelos",
    "puebla": "Puebla",
    "queretaro": "Queretaro",
}
BLOCKED_REGION_KEYS = {"michoacan", "michoacan de ocampo"}
BADGES = {
    "auto verificado",
    "vehiculo verificado",
    "publicacion pausada",
    "promocionado",
    "vendido por",
}
GENERIC_VERSION_TOKENS = {
    "auto",
    "automatico",
    "automatica",
    "at",
    "dct",
    "suv",
    "sedan",
    "hatchback",
    "4wd",
    "awd",
    "mhev",
    "phev",
    "bev",
    "fsi",
    "aut",
    "electrico",
    "hibrido",
    "xdrive",
    "sdrive",
    "mini",
    "countryman",
    "model",
    "autonomia",
    "mayor",
    "sport",
    "line",
}
REQUIRED_TRIM_TOKENS = {
    "sdrive18i",
    "sdrive20i",
    "xdrive30i",
    "xdrive30e",
    "xdrive40i",
    "xdrive40",
    "xdrive45e",
    "xdrive50e",
    "xdrive50",
    "m40i",
    "m50i",
    "highline",
    "trendline",
    "stealth",
    "performance",
    "330e",
    "118i",
    "classic",
    "iconic",
    "all4",
    "ultra",
    "ultimate",
    "gls450",
    "gle450",
    "glc300",
    "a35",
    "inscription",
    "xle",
}
STATUS_ORDER = {
    "below_offer": 0,
    "needs_quote": 1,
    "near_offer": 2,
    "blocked_kavak_inventory": 3,
    "rejected": 4,
}


@dataclass
class KavakTarget:
    target_id: str
    origin: str
    vehicle_no: int | None
    external_id: str | None
    brand: str
    family: str
    model: str
    year: int
    kilometers: int | None
    selected_version: str
    sell_offer: int
    kavak_url: str | None
    valid_until: str | None
    query: str
    trim_tokens: list[str]


@dataclass
class Listing:
    publication_id: str
    title: str
    seller_name: str
    seller_type: str
    url: str
    price: int
    year: int | None
    kilometers: int | None
    location: str
    city: str
    region: str | None
    raw_text: str
    query: str
    search_url: str
    observed_at: str


@dataclass
class Candidate:
    id: str
    target: KavakTarget
    listing: Listing
    delta_to_kavak: int
    target_drop_needed: int
    fit: str
    status: str
    reason: str
    confidence: str


def normalize(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value.lower())
        .encode("ascii", "ignore")
        .decode("ascii")
        .replace("&", " ")
    )


def repair_mojibake(value: str) -> str:
    if "Ã" not in value and "Â" not in value:
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize(value))


def positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value > 0 else None


def money(value: int | None) -> str:
    return f"${value:,}" if value is not None else "sin dato"


def clean_url(url: str) -> str:
    return url.split("#", 1)[0]


def publication_id(url: str) -> str:
    match = re.search(r"MLM[-_](\d+)", url)
    if match:
        return f"MLM-{match.group(1)}"
    return re.sub(r"\W+", "-", url)[-40:]


def source_identity(url: str) -> str:
    if "mercadolibre.com.mx" in url:
        return publication_id(url)
    return clean_url(url)


def read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def family_from_text(brand: str, model: str, selected_version: str = "") -> str:
    text = normalize(f"{brand} {model} {selected_version}")
    if "bmw" in text:
        for family in ["x1", "x2", "x3", "x4", "x5", "x7", "xm", "m5", "ix3", "ix"]:
            if re.search(rf"\b{family}\b", text):
                return f"BMW {family.upper() if family.startswith('x') or family in {'xm', 'm5'} else family}"
        if "330e" in text or "serie 3" in text:
            return "BMW 330e"
        if "118" in text:
            return "BMW 118i"
    if "mini" in text:
        if "countryman" in text:
            return "MINI Countryman"
        if "cooper se" in text or "33kwh" in text:
            return "MINI Cooper SE"
        return "MINI Cooper"
    if "volkswagen" in text or re.search(r"\bvw\b", text):
        if "teramont" in text or "terramont" in text:
            return "Volkswagen Teramont"
    if "mercedes" in text:
        if "gls" in text:
            return "Mercedes-Benz GLS"
        if "gle" in text:
            return "Mercedes-Benz GLE"
        if "glc" in text:
            return "Mercedes-Benz GLC"
        if "a 35" in text or "a35" in text:
            return "Mercedes-Benz A 35"
    if "land" in text and "rover" in text:
        if "velar" in text:
            return "Land Rover Velar"
        if "sport" in text:
            return "Land Rover Range Rover Sport"
    if "volvo" in text:
        if "xc60" in text:
            return "Volvo XC60"
        if "ex30" in text:
            return "Volvo EX30"
    if "kia" in text and "seltos" in text:
        return "KIA Seltos"
    if "ford" in text and "expedition" in text:
        return "Ford Expedition"
    if "toyota" in text and "rav4" in text:
        return "Toyota RAV4"
    words = [word for word in normalize(f"{brand} {model}").split() if word]
    return " ".join(words[:3]).title()


def family_tokens(family: str) -> list[str]:
    text = normalize(family)
    if "volkswagen teramont" in text:
        return ["volkswagen", "teramont"]
    if "mercedes" in text:
        words = [word for word in text.split() if word not in {"benz"}]
        return words[-1:]
    if "land rover" in text:
        return [word for word in text.split() if word not in {"land", "rover", "range"}][-2:]
    if "mini cooper se" in text:
        return ["mini", "cooper", "se"]
    words = text.split()
    return words[-1:] if len(words) > 1 else words


def has_model_token(text: str, compact_text: str, token: str) -> bool:
    token_text = normalize(token)
    token_compact = compact(token)
    if token_text in {"x1", "x2", "x3", "x4", "x5", "x7"}:
        return re.search(rf"\bx\s*{token_text[1]}\b", text) is not None or re.search(rf"\b{token_text}\b", text) is not None
    if token_text in {"a35", "a 35"}:
        return re.search(r"\ba\s*35\b", text) is not None or re.search(r"\ba35\b", text) is not None
    if token_text == "model y":
        return re.search(r"\bmodel\s*y\b", text) is not None
    if len(token_compact) <= 2:
        return re.search(rf"\b{re.escape(token_text)}\b", text) is not None
    return token_compact in compact_text


def family_matches_listing(family: str, listing_text: str) -> bool:
    text = normalize(listing_text)
    compact_text = compact(text)
    family_text = normalize(family)

    if family_text.startswith("bmw "):
        if "bmw" not in text:
            return False
        if "330e" in family_text:
            return "330e" in compact_text
        if "118i" in family_text:
            return "118i" in compact_text or "118ia" in compact_text
        if "ix3" in family_text:
            return re.search(r"\bix\s*3\b", text) is not None or re.search(r"\bix3\b", text) is not None
        if family_text.endswith("ix"):
            return re.search(r"\bix\b", text) is not None and not re.search(r"\bix\s*3\b|\bix3\b", text)
        for token in ["x1", "x2", "x3", "x4", "x5", "x7", "xm", "m5"]:
            if token in family_text:
                return has_model_token(text, compact_text, token)
        return False

    if family_text.startswith("mini "):
        if "mini" not in text:
            return False
        if "countryman" in family_text:
            return "countryman" in text
        if "cooper se" in family_text:
            return "cooper" in text and (re.search(r"\bse\b", text) is not None or "33kwh" in compact_text)
        return "cooper" in text

    if "volkswagen teramont" in family_text:
        return ("volkswagen" in text or re.search(r"\bvw\b", text) is not None) and (
            "teramont" in text or "terramont" in text
        )

    if family_text.startswith("mercedes"):
        if "mercedes" not in text:
            return False
        if "gls" in family_text:
            return re.search(r"\bgls\b", text) is not None
        if "gle" in family_text:
            return re.search(r"\bgle\b", text) is not None
        if "glc" in family_text:
            return re.search(r"\bglc\b", text) is not None
        if "a 35" in family_text:
            return has_model_token(text, compact_text, "a35")
        return False

    if family_text.startswith("land rover"):
        if "land" not in text or "rover" not in text:
            return False
        if "velar" in family_text:
            return "velar" in text
        if "sport" in family_text:
            return "sport" in text
        return False

    if family_text.startswith("volvo "):
        if "volvo" not in text:
            return False
        if "xc60" in family_text:
            return "xc60" in compact_text
        if "ex30" in family_text:
            return "ex30" in compact_text
        return False

    if "tesla model y" in family_text:
        return "tesla" in text and has_model_token(text, compact_text, "model y")
    if "kia seltos" in family_text:
        return "kia" in text and "seltos" in text
    if "ford expedition" in family_text:
        return "ford" in text and "expedition" in text
    if "toyota rav4" in family_text:
        return "toyota" in text and "rav4" in compact_text

    return all(token in compact_text for token in compact(family).split())


def trim_tokens(model: str, selected_version: str) -> list[str]:
    text = normalize(f"{model} {selected_version}")
    compact_text = compact(text)
    known = [
        "sdrive18i",
        "sdrive20i",
        "xdrive30i",
        "xdrive40i",
        "xdrive45e",
        "xdrive50e",
        "xdrive50",
        "m40i",
        "m50i",
        "highline",
        "trendline",
        "stealth",
        "performance",
        "330e",
        "118i",
        "classic",
        "iconic",
        "cooper",
        "all4",
        "ultra",
        "ultimate",
        "dark",
        "gls450",
        "gle450",
        "glc300",
        "a35",
        "r_dynamic",
        "dynamic",
        "inscription",
        "xle",
    ]
    tokens = [token for token in known if token.replace("_", "") in compact_text]
    for token in text.split():
        token = token.strip()
        clean_token = re.sub(r"[^a-z0-9]+", "", token)
        if len(clean_token) < 3 or clean_token in GENERIC_VERSION_TOKENS:
            continue
        if re.fullmatch(r"\d+(\.\d+)?", token) or clean_token.isdigit():
            continue
        if clean_token not in tokens and len(tokens) < 6:
            tokens.append(clean_token)
    return tokens[:6]


def is_required_trim_token(token: str) -> bool:
    return compact(token) in REQUIRED_TRIM_TOKENS


def search_brand(brand: str) -> str:
    text = normalize(brand)
    if "land" in text and "rover" in text:
        return "Land Rover"
    if "mercedes" in text:
        return "Mercedes Benz"
    if "volkswagen" in text:
        return "Volkswagen"
    return brand


def query_for_target(target: KavakTarget, include_trim: bool) -> str:
    family = target.family
    if family == "Volkswagen Teramont":
        family_query = "Teramont"
    else:
        family_query = re.sub(r"^(BMW|MINI|KIA|Volvo|Volkswagen|Mercedes-Benz|Land Rover|Ford|Toyota)\s+", "", family)
    pieces = [search_brand(target.brand), family_query, str(target.year)]
    if include_trim:
        for token in target.trim_tokens[:2]:
            if token not in {"cooper", "classic", "automatico"}:
                pieces.append(token.replace("_", " "))
    return " ".join(piece for piece in pieces if piece).strip()


def search_url(query: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", query).strip("-")
    return f"https://listado.mercadolibre.com.mx/{urllib.parse.quote(slug)}_OrderId_PRICE_NoIndex_True"


def build_targets() -> list[KavakTarget]:
    inventory = {vehicle["no"]: vehicle for vehicle in read_json(INVENTORY_PATH, [])}
    quotes = read_json(KAVAK_QUOTES_PATH, [])
    targets: list[KavakTarget] = []

    for quote in quotes:
        sell_offer = positive_int(quote.get("sellOffer"))
        vehicle_no = quote.get("vehicleNo")
        vehicle = inventory.get(vehicle_no)
        if sell_offer is None or vehicle is None:
            continue
        selected_version = quote.get("selectedVersion") or vehicle.get("model") or ""
        family = family_from_text(vehicle["brand"], vehicle["model"], selected_version)
        target = KavakTarget(
            target_id=f"inventory-{vehicle_no}",
            origin="inventory",
            vehicle_no=vehicle_no,
            external_id=None,
            brand=vehicle["brand"],
            family=family,
            model=vehicle["model"],
            year=int(vehicle["year"]),
            kilometers=vehicle.get("kilometers"),
            selected_version=selected_version,
            sell_offer=sell_offer,
            kavak_url=quote.get("url"),
            valid_until=quote.get("validUntil"),
            query="",
            trim_tokens=trim_tokens(vehicle["model"], selected_version),
        )
        target.query = query_for_target(target, include_trim=True)
        targets.append(target)

    external_bargains = {item["id"]: item for item in read_json(EXTERNAL_BARGAINS_PATH, [])}
    external_quotes = read_json(EXTERNAL_QUOTES_PATH, [])
    for quote in external_quotes:
        sell_offer = positive_int(quote.get("sellOffer"))
        deal = external_bargains.get(quote.get("externalId"))
        if sell_offer is None or deal is None:
            continue
        selected_version = quote.get("selectedVersion") or deal.get("version") or deal.get("name") or ""
        family = family_from_text(deal.get("name", ""), deal.get("version", ""), selected_version)
        brand = deal["name"].split()[0] if deal.get("name") else family.split()[0]
        target = KavakTarget(
            target_id=f"external-{deal['id']}",
            origin="external",
            vehicle_no=None,
            external_id=deal["id"],
            brand=brand,
            family=family,
            model=deal["name"],
            year=int(deal["year"]),
            kilometers=deal.get("km"),
            selected_version=selected_version,
            sell_offer=sell_offer,
            kavak_url=quote.get("url"),
            valid_until=quote.get("validUntil"),
            query="",
            trim_tokens=trim_tokens(deal.get("version", ""), selected_version),
        )
        target.query = query_for_target(target, include_trim=True)
        targets.append(target)

    unique: dict[tuple[str, int, str, int | None], KavakTarget] = {}
    for target in targets:
        key = (target.family, target.year, compact(" ".join(target.trim_tokens[:2])), target.vehicle_no)
        unique[key] = target
    return list(unique.values())


def parse_price(lines: list[str], text: str) -> int | None:
    for index, line in enumerate(lines):
        if line == "$" and index + 1 < len(lines):
            value = re.sub(r"[^\d]", "", lines[index + 1])
            if value:
                return int(value)
    match = re.search(r"\$\s*([\d,]+)", text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def parse_year(lines: list[str], text: str) -> int | None:
    for line in lines:
        if re.fullmatch(r"20\d{2}", line):
            return int(line)
    match = re.search(r"\b(20\d{2})\b", text)
    return int(match.group(1)) if match else None


def parse_km(text: str) -> int | None:
    match = re.search(r"([\d,]+)\s*km\b", normalize(text), re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else None


def region_from_location(location: str, raw_text: str) -> str | None:
    text = normalize(f"{location} {raw_text}")
    if any(blocked in text for blocked in BLOCKED_REGION_KEYS):
        return None
    for key, region in ALLOWED_REGION_KEYS.items():
        if key in text:
            return region
    return None


def city_from_location(location: str) -> str:
    if " - " in location:
        return location.split(" - ", 1)[0].strip()
    return location.strip() or "sin ciudad"


def parse_listing(raw: dict[str, str], query: str, url: str, observed_at: str) -> Listing | None:
    href = raw.get("href") or ""
    text = repair_mojibake(raw.get("text") or "")
    if not href or "MLM" not in href:
        return None
    if "auto.mercadolibre.com.mx" not in href:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    price = parse_price(lines, text)
    if price is None:
        return None

    title = ""
    seller = "vendedor no identificado"
    price_index = next((index for index, line in enumerate(lines) if line == "$" or re.search(r"\$\s*[\d,]+", line)), -1)
    before_price = lines[:price_index] if price_index >= 0 else lines[:3]
    clean_before = [line for line in before_price if normalize(line) not in BADGES]
    if clean_before:
        title = clean_before[0]
    if len(clean_before) >= 2:
        seller = clean_before[-1]
    location = next((line for line in reversed(lines) if " - " in line), "")
    if not title:
        title = lines[0]

    full_text = " | ".join(lines)
    year = parse_year(lines, text)
    kilometers = parse_km(text)
    if year is None or kilometers is None:
        return None
    region = region_from_location(location, "")
    seller_text = normalize(f"{seller} {full_text}")
    seller_type = "kavak" if re.search(r"\bkavak\b", seller_text) else "unknown"
    return Listing(
        publication_id=publication_id(href),
        title=title,
        seller_name=seller,
        seller_type=seller_type,
        url=clean_url(href),
        price=price,
        year=year,
        kilometers=kilometers,
        location=location or "sin ubicacion",
        city=city_from_location(location),
        region=region,
        raw_text=full_text,
        query=query,
        search_url=url,
        observed_at=observed_at,
    )


def listing_matches_target(listing: Listing, target: KavakTarget) -> tuple[bool, str, str]:
    text = normalize(f"{listing.title} {listing.raw_text}")
    compact_text = compact(text)
    if listing.year != target.year:
        return False, "rejected", f"anio distinto: publicado {listing.year}, objetivo {target.year}"
    if not family_matches_listing(target.family, f"{listing.title} {listing.raw_text}"):
        return False, "rejected", f"familia no coincide con {target.family}"
    trim_required = [token for token in target.trim_tokens[:4] if is_required_trim_token(token)]
    matched_required_trim = [token for token in trim_required if compact(token) and compact(token) in compact_text]
    if trim_required and not matched_required_trim:
        return True, "same_model_unquoted", "mismo modelo/anio, version no confirmada en el texto"
    if listing.kilometers is not None and target.kilometers is not None:
        km_gap = listing.kilometers - target.kilometers
        if km_gap > 20_000:
            return True, "same_version_higher_km", f"misma familia/version probable, pero {km_gap:,} km arriba del benchmark"
        if km_gap < -20_000:
            return True, "same_version_comparable", f"misma familia/version probable y {abs(km_gap):,} km abajo del benchmark"
    return True, "same_version_comparable", "misma familia/anio/version probable por titulo"


def classify_candidate(listing: Listing, target: KavakTarget, fit: str, reason: str) -> Candidate:
    delta = target.sell_offer - listing.price
    drop_needed = max(0, listing.price - target.sell_offer)
    if listing.seller_type == "kavak":
        status = "blocked_kavak_inventory"
        confidence = "bloqueado"
        reason = "vendedor Kavak; no es compra externa operable"
    elif delta > 0 and fit == "same_version_comparable":
        status = "below_offer"
        confidence = "alta"
    elif delta > 0:
        status = "needs_quote"
        confidence = "media"
    elif drop_needed <= 30_000:
        status = "near_offer"
        confidence = "media"
    else:
        status = "rejected"
        confidence = "baja"
    return Candidate(
        id=f"{listing.publication_id.lower()}-{target.target_id}",
        target=target,
        listing=listing,
        delta_to_kavak=delta,
        target_drop_needed=drop_needed,
        fit=fit,
        status=status,
        reason=reason,
        confidence=confidence,
    )


def extract_cards(page: Any) -> list[dict[str, str]]:
    return page.evaluate(
        """
        () => {
          const nodes = [...document.querySelectorAll('li.ui-search-layout__item, .poly-card')];
          const fallback = [...document.querySelectorAll('a[href*="MLM-"]')].map((a) => a.closest('li, .poly-card, div'));
          const all = [...nodes, ...fallback].filter(Boolean);
          return all.map((el) => {
            const link = [...el.querySelectorAll('a[href*="MLM-"]')][0];
            return { href: link ? link.href : '', text: el.innerText || '' };
          }).filter((item) => item.href && item.text);
        }
        """
    )


def page_has_captcha(page: Any) -> bool:
    current_url = page.url.lower()
    if "captcha" in current_url:
        return True
    try:
        body = normalize(page.locator("body").inner_text(timeout=3000))
    except Exception:
        return False
    return "captcha" in body or "validar que eres" in body


def scrape_searches(args: argparse.Namespace, targets: list[KavakTarget]) -> tuple[list[Listing], list[dict[str, Any]]]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise SystemExit("Playwright no esta instalado. Corre: pip install playwright && python -m playwright install chromium") from exc

    observed_at = date.today().isoformat()
    listings: dict[str, Listing] = {}
    access_issues: list[dict[str, Any]] = []
    target_slice = targets[: args.max_targets] if args.max_targets else targets

    with sync_playwright() as playwright:
        launch_kwargs = {
            "headless": not args.headed,
            "slow_mo": args.slow_ms,
        }
        browser = playwright.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            locale="es-MX",
            viewport={"width": 1365, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        seen_urls: set[str] = set()
        for index, target in enumerate(target_slice, start=1):
            queries = [query_for_target(target, include_trim=False)]
            trim_query = query_for_target(target, include_trim=True)
            if trim_query not in queries:
                queries.append(trim_query)
            for query in queries:
                url = search_url(query)
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                print(f"[{index}/{len(target_slice)}] MercadoLibre: {query}", flush=True)
                try:
                    page.goto(url, wait_until="load", timeout=args.timeout_ms)
                    try:
                        page.wait_for_selector("li.ui-search-layout__item, .poly-card, a[href*='MLM-']", timeout=args.timeout_ms)
                    except PlaywrightTimeoutError:
                        pass
                    page.wait_for_timeout(args.wait_ms)
                except Exception as exc:
                    access_issues.append({"query": query, "url": url, "error": str(exc)[:500]})
                    continue
                if page_has_captcha(page):
                    access_issues.append({"query": query, "url": url, "error": "MercadoLibre captcha"})
                    if args.stop_on_captcha:
                        context.close()
                        browser.close()
                        return list(listings.values()), access_issues
                    continue
                try:
                    raw_cards = extract_cards(page)
                except Exception as exc:
                    access_issues.append({"query": query, "url": url, "error": f"extract failed: {exc}"[:500]})
                    continue
                for raw in raw_cards:
                    listing = parse_listing(raw, query, url, observed_at)
                    if listing is None:
                        continue
                    if listing.region is None:
                        continue
                    key = listing.publication_id
                    if key not in listings or listing.price < listings[key].price:
                        listings[key] = listing
                time.sleep(args.pause)
        context.close()
        browser.close()

    return list(listings.values()), access_issues


def build_candidates(listings: list[Listing], targets: list[KavakTarget], include_rejected: bool) -> list[Candidate]:
    candidates: dict[str, Candidate] = {}
    for listing in listings:
        for target in targets:
            ok, fit, reason = listing_matches_target(listing, target)
            if not ok:
                continue
            candidate = classify_candidate(listing, target, fit, reason)
            if candidate.status == "rejected" and not include_rejected:
                continue
            key = f"{listing.publication_id}-{target.target_id}"
            current = candidates.get(key)
            if current is None or candidate.delta_to_kavak > current.delta_to_kavak:
                candidates[key] = candidate

    return sorted(
        candidates.values(),
        key=lambda item: (
            STATUS_ORDER.get(item.status, 9),
            -item.delta_to_kavak if item.status == "blocked_kavak_inventory" else item.target_drop_needed,
            -item.delta_to_kavak,
            item.listing.price,
        ),
    )


def target_title(candidate: Candidate) -> str:
    target = candidate.target
    trim = " ".join(target.trim_tokens[:2]).strip()
    return f"{target.family} {target.year}{(' ' + trim) if trim else ''}"


def direct_status(candidate: Candidate) -> str:
    return candidate.status


def action_text(candidate: Candidate) -> str:
    if candidate.status == "blocked_kavak_inventory":
        return "No perseguir: el vendedor es Kavak, no una compra externa para revenderle."
    if candidate.status == "below_offer":
        return f"Comprar/cotizar ya: precio publicado {money(candidate.delta_to_kavak)} debajo de Kavak venta directa."
    if candidate.status == "needs_quote":
        return "Cotizar esta unidad exacta en Kavak antes de decidir; precio publicado esta debajo, pero version/km no quedan amarrados."
    if candidate.status == "near_offer":
        return f"Pedir rebaja minima de {money(candidate.target_drop_needed)} mas costos; a precio actual no queda debajo."
    return "No usar sin validar version, kilometraje, factura y precio total real."


def candidate_to_direct_target(candidate: Candidate, priority: int) -> dict[str, Any]:
    target = candidate.target
    listing = candidate.listing
    payload: dict[str, Any] = {
        "id": candidate.id,
        "origin": target.origin,
        "priority": priority,
        "status": direct_status(candidate),
        "fit": candidate.fit,
        "title": target_title(candidate),
        "subtitle": f"{listing.city}, {listing.region}; {candidate.reason}",
        "source": "MercadoLibre",
        "sellerName": listing.seller_name,
        "sellerType": listing.seller_type,
        "sourceUrl": listing.url,
        "observedAt": listing.observed_at,
        "region": listing.region,
        "city": listing.city,
        "candidatePrice": listing.price,
        "candidateKm": listing.kilometers,
        "candidateVersion": listing.title,
        "kavakSellOffer": target.sell_offer,
        "deltaToKavak": candidate.delta_to_kavak,
        "targetDropNeeded": candidate.target_drop_needed,
        "action": action_text(candidate),
        "evidence": (
            f"MercadoLibre visible: {listing.seller_name}, {money(listing.price)}, "
            f"{listing.kilometers if listing.kilometers is not None else 'km sin dato'} km, "
            f"{listing.city}, {listing.region}. Oferta Kavak "
            f"{'#' + str(target.vehicle_no) if target.vehicle_no is not None else target.external_id}: "
            f"{money(target.sell_offer)} para {target.selected_version}"
            f"{' de ' + str(target.kilometers) + ' km' if target.kilometers is not None else ''}."
        ),
        "notes": [
            "Solo venta directa de Kavak; no se usa oferta para entregar otro auto.",
            "El precio publicado no incluye inspeccion, traslado, adeudos ni castigo final de Kavak.",
        ],
    }
    if target.vehicle_no is not None:
        payload["vehicleNos"] = [target.vehicle_no]
    if target.external_id is not None:
        payload["externalId"] = target.external_id
    return payload


def stable_existing_targets() -> list[dict[str, Any]]:
    existing = read_json(DIRECT_TARGETS_PATH, [])
    stable: list[dict[str, Any]] = []
    for item in existing:
        source_url = item.get("sourceUrl", "")
        if item.get("source") != "MercadoLibre":
            stable.append(item)
            continue
        if "auto.mercadolibre.com.mx" not in source_url:
            continue
        if item.get("status") in {"below_offer", "needs_quote", "near_offer", "blocked_kavak_inventory"}:
            stable.append(item)
            continue
        if "facebook.com" in source_url:
            stable.append(item)
    return stable


def merge_direct_targets(generated: list[dict[str, Any]], merge_existing: bool, limit: int) -> list[dict[str, Any]]:
    rows = generated[:]
    if merge_existing:
        rows.extend(stable_existing_targets())
    deduped: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = (source_identity(row["sourceUrl"]), int(row["kavakSellOffer"]))
        current = deduped.get(key)
        if current is None:
            deduped[key] = row
            continue
        if STATUS_ORDER.get(row["status"], 9) < STATUS_ORDER.get(current["status"], 9):
            deduped[key] = row
        elif row.get("deltaToKavak", -10**9) > current.get("deltaToKavak", -10**9):
            deduped[key] = row
        elif (
            row.get("deltaToKavak") == current.get("deltaToKavak")
            and "?" in row.get("sourceUrl", "")
            and "?" not in current.get("sourceUrl", "")
        ):
            deduped[key] = row
    sorted_rows = sorted(
        deduped.values(),
        key=lambda item: (
            STATUS_ORDER.get(item["status"], 9),
            -int(item.get("deltaToKavak", -10**9)),
            int(item.get("candidatePrice", 10**12)),
        ),
    )
    for index, row in enumerate(sorted_rows[:limit], start=1):
        row["priority"] = index
    return sorted_rows[:limit]


def write_outputs(
    candidates: list[Candidate],
    direct_targets: list[dict[str, Any]],
    listings: list[Listing],
    targets: list[KavakTarget],
    access_issues: list[dict[str, Any]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "allowedRegions": sorted(set(ALLOWED_REGION_KEYS.values())),
        "targetsScanned": len(targets),
        "listingsCaptured": len(listings),
        "candidates": [
            {
                "id": candidate.id,
                "status": candidate.status,
                "fit": candidate.fit,
                "confidence": candidate.confidence,
                "deltaToKavak": candidate.delta_to_kavak,
                "targetDropNeeded": candidate.target_drop_needed,
                "reason": candidate.reason,
                "target": asdict(candidate.target),
                "listing": asdict(candidate.listing),
            }
            for candidate in candidates
        ],
        "accessIssues": access_issues,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for path in [DIRECT_TARGETS_PATH, OUTPUT_DIRECT_JSON]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(direct_targets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = OUTPUT_DIR / f"ml_candidates_{date.today().isoformat()}.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = [
            "status",
            "fit",
            "title",
            "seller",
            "region",
            "city",
            "price",
            "km",
            "kavakOffer",
            "deltaToKavak",
            "url",
            "reason",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in direct_targets:
            writer.writerow(
                {
                    "status": row["status"],
                    "fit": row["fit"],
                    "title": row["title"],
                    "seller": row["sellerName"],
                    "region": row["region"],
                    "city": row["city"],
                    "price": row["candidatePrice"],
                    "km": row["candidateKm"],
                    "kavakOffer": row["kavakSellOffer"],
                    "deltaToKavak": row["deltaToKavak"],
                    "url": row["sourceUrl"],
                    "reason": row["action"],
                }
            )
    print(f"Wrote {OUTPUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {DIRECT_TARGETS_PATH.relative_to(ROOT)}")
    print(f"Wrote {csv_path.relative_to(ROOT)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Busca MercadoLibre debajo de ofertas Kavak de venta directa.")
    parser.add_argument("--headed", action="store_true", help="abre Chromium visible para resolver captcha si aparece")
    parser.add_argument("--stop-on-captcha", action="store_true", help="detiene el barrido en el primer captcha")
    parser.add_argument("--max-targets", type=int, default=0, help="0 = todos los targets con oferta Kavak")
    parser.add_argument("--limit", type=int, default=60, help="maximo de filas para la app")
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-ms", type=int, default=2500)
    parser.add_argument("--slow-ms", type=int, default=0)
    parser.add_argument("--pause", type=float, default=0.35)
    parser.add_argument("--include-rejected", action="store_true")
    parser.add_argument("--no-merge-existing", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])
    targets = build_targets()
    if not targets:
        raise SystemExit("No hay targets con oferta Kavak venta directa.")
    listings, access_issues = scrape_searches(args, targets)
    candidates = build_candidates(listings, targets, include_rejected=args.include_rejected)
    direct_generated = [candidate_to_direct_target(candidate, index + 1) for index, candidate in enumerate(candidates)]
    direct_targets = merge_direct_targets(direct_generated, merge_existing=not args.no_merge_existing, limit=args.limit)
    write_outputs(candidates, direct_targets, listings, targets, access_issues)
    below = [row for row in direct_targets if row["sellerType"] != "kavak" and row["deltaToKavak"] > 0 and row["status"] != "rejected"]
    print(
        json.dumps(
            {
                "targets": len(targets),
                "listings": len(listings),
                "candidates": len(candidates),
                "appRows": len(direct_targets),
                "belowKavakRows": len(below),
                "captchaOrAccessIssues": len(access_issues),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
