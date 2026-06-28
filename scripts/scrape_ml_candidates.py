"""
Barrido MercadoLibre seminuevos: CDMX, Edomex, Morelos, Puebla, Querétaro.
Ordena por precio ascendente por modelo/marca y extrae los listings más baratos.
Guarda candidatas (sin oferta Kavak aún) en data/arbitrage_candidates.json.

Uso:
  python scripts/scrape_ml_candidates.py
  python scripts/scrape_ml_candidates.py --max-per-model 5
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

CANDIDATES_PATH = Path("data/arbitrage_candidates.json")

# MercadoLibre Mexico state IDs (seminuevos autos)
# Obtenidos inspeccionando los filtros del sitio
STATES = {
    "CDMX":     "TUxNREZFREVSQUwxNDk1NQ",
    "Edomex":   "TUxNUkVTVEFET01FWElDTzE1",
    "Morelos":  "TUxNUk1PUkVMT1MxNzU0Mw",
    "Puebla":   "TUxNUlBVRUJMQTIxNTc1",
    "Queretaro":"TUxNUlFVRVJFVEFSTzIyNTc2",
}

# Modelos target: marcas/segmentos con buena demanda Kavak
# Formato: (marca, modelo_ml) donde modelo_ml es el slug que usa ML
TARGET_MODELS = [
    ("BMW",          "x3"),
    ("BMW",          "x4"),
    ("BMW",          "x5"),
    ("BMW",          "x1"),
    ("BMW",          "x2"),
    ("Mercedes-Benz","clase-glc"),
    ("Mercedes-Benz","clase-gle"),
    ("Mercedes-Benz","clase-gls"),
    ("Mercedes-Benz","clase-a"),
    ("Volvo",        "xc60"),
    ("Volvo",        "xc90"),
    ("Audi",         "q5"),
    ("Audi",         "q7"),
    ("Audi",         "a3"),
    ("Porsche",      "cayenne"),
    ("Porsche",      "macan"),
    ("Toyota",       "rav4"),
    ("Toyota",       "highlander"),
    ("Honda",        "cr-v"),
    ("Volkswagen",   "tiguan"),
    ("Volkswagen",   "teramont"),
    ("Land Rover",   "range-rover-sport"),
    ("Land Rover",   "discovery-sport"),
    ("Tesla",        "model-y"),
    ("Tesla",        "model-3"),
    ("MINI",         "countryman"),
    ("Jeep",         "grand-cherokee"),
    ("Jeep",         "wrangler"),
    ("Ford",         "expedition"),
    ("Chevrolet",    "suburban"),
    ("Infiniti",     "qx50"),
    ("Infiniti",     "qx60"),
    ("KIA",          "sorento"),
    ("KIA",          "carnival"),
]

PRICE_RE  = re.compile(r"\$[\d,]+")
KM_RE     = re.compile(r"([\d,]+)\s*km", re.IGNORECASE)
YEAR_RE   = re.compile(r"\b(20\d{2})\b")


def parse_price(text: str) -> int | None:
    m = PRICE_RE.search(text)
    if not m:
        return None
    return int(m.group().replace("$", "").replace(",", ""))


def parse_km(text: str) -> int | None:
    m = KM_RE.search(text)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def parse_year(text: str) -> int | None:
    m = YEAR_RE.search(text)
    return int(m.group(1)) if m else None


def scrape_model(page: Page, brand: str, model_slug: str,
                 state_id: str, state_name: str, max_items: int) -> list[dict]:
    brand_slug = brand.lower().replace(" ", "-").replace(".", "")
    url = (
        f"https://autos.mercadolibre.com.mx/autos-camionetas/{brand_slug}/{model_slug}/"
        f"_DisplayType_LF_StateId_{state_id}_ITEM_CONDITION_2230284_OrderId_PRICE"
    )
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        page.wait_for_timeout(2_000)
    except Exception:
        return []

    results: list[dict] = []
    cards = page.query_selector_all("li.ui-search-layout__item")
    if not cards:
        cards = page.query_selector_all("div.andes-card")

    for card in cards[:max_items]:
        try:
            title_el   = card.query_selector("h2, h3, .ui-search-item__title")
            price_el   = card.query_selector(".price-tag-fraction, .andes-money-amount__fraction")
            link_el    = card.query_selector("a")
            attr_texts = " ".join(
                el.inner_text()
                for el in card.query_selector_all(".ui-search-item__attributes-list li, .ui-search-card-attributes__attribute")
            )

            title = title_el.inner_text().strip() if title_el else ""
            price_text = price_el.inner_text().strip() if price_el else ""
            href  = link_el.get_attribute("href") if link_el else ""

            price = parse_price("$" + price_text.replace(",", "")) if price_text else None
            km    = parse_km(attr_texts + " " + title)
            year  = parse_year(title)

            if not title or price is None or price < 50_000:
                continue
            if href and "?" in href:
                href = href.split("?")[0]

            results.append({
                "id":            f"ml-{hash(href) & 0xFFFFFFFF}",
                "source":        "MercadoLibre",
                "observedAt":    str(date.today()),
                "region":        state_name,
                "city":          state_name,
                "year":          year,
                "brand":         brand,
                "model":         model_slug.replace("-", " ").title(),
                "version":       title,
                "km":            km,
                "publishedPrice": price,
                "url":           href or url,
                "kavakSellOffer":  None,
                "kavakQuoteUrl":   None,
                "kavakCapturedAt": None,
                "kavakValidUntil": None,
                "notes":           f"Barrido auto {date.today()} — precio más bajo {state_name}",
            })
        except Exception:
            continue

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-per-model", type=int, default=3,
                        help="Máximo listings por modelo/estado (default 3)")
    parser.add_argument("--brands", nargs="+", help="Filtrar solo estas marcas")
    args = parser.parse_args()

    today = str(date.today())
    models = TARGET_MODELS
    if args.brands:
        brands_lower = {b.lower() for b in args.brands}
        models = [(b, m) for b, m in TARGET_MODELS if b.lower() in brands_lower]

    # Carga candidatas existentes para no duplicar
    existing: list[dict] = []
    if CANDIDATES_PATH.exists():
        existing = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    existing_urls = {c.get("url", "") for c in existing}

    all_new: list[dict] = []
    total = len(models) * len(STATES)
    done  = 0

    with sync_playwright() as pw:
        # En Mac con Playwright instalado localmente, omite executable_path
        # y deja que Playwright use su propio Chromium descargado.
        # En el servidor remoto usa: /opt/pw-browsers/chromium-1194/chrome-linux/chrome
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="es-MX",
        )
        page = context.new_page()

        for brand, model_slug in models:
            for state_name, state_id in STATES.items():
                done += 1
                label = f"{brand} {model_slug} / {state_name}"
                print(f"[{done}/{total}] {label} ...", end=" ", flush=True)

                rows = scrape_model(page, brand, model_slug, state_id, state_name, args.max_per_model)
                new_rows = [r for r in rows if r["url"] not in existing_urls]
                for r in new_rows:
                    existing_urls.add(r["url"])

                all_new.extend(new_rows)
                print(f"{len(new_rows)} nuevas" if new_rows else "sin resultados")
                time.sleep(0.8)

        context.close()
        browser.close()

    combined = existing + all_new
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES_PATH.write_text(json.dumps(combined, ensure_ascii=False, indent=2))

    print()
    print(f"[done] {len(all_new)} candidatas nuevas encontradas")
    print(f"[done] Total en {CANDIDATES_PATH}: {len(combined)}")
    if all_new:
        print()
        print("SIGUIENTE PASO:")
        print("  Abre cada URL, verifica el precio y cotiza en kavak.com/mx/cotizar-auto.")
        print("  Llena kavakSellOffer en data/arbitrage_candidates.json.")
        print("  Luego corre: python scripts/scan_arbitrage_candidates.py --score")


if __name__ == "__main__":
    main()
