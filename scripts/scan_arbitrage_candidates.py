"""
Barrido de candidatas a arbitraje real vs Kavak.

FLUJO:
  1. Este script genera links de búsqueda por modelo (MercadoLibre, Seminuevos, Facebook).
  2. Tú abres cada link, anotas candidatas baratas en data/arbitrage_candidates.json.
  3. Luego cotizas cada candidata en kavak.com/mx/cotizar-auto manualmente.
  4. Llenas kavakSellOffer en el mismo JSON.
  5. Corres este script con --score para que calcule spread y genere el ranking.

REGLA CENTRAL: no se inventa ningún precio. Solo entra al ranking lo que tiene
URL pública verificable Y oferta Kavak capturada manualmente.

Uso:
  python scripts/scan_arbitrage_candidates.py --links     # genera links de busqueda
  python scripts/scan_arbitrage_candidates.py --score     # calcula spreads y ranking
  python scripts/scan_arbitrage_candidates.py --validate  # valida el JSON antes de subir
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import date
from pathlib import Path

INVENTORY_PATH = Path("data/inventario.json")
CANDIDATES_PATH = Path("data/arbitrage_candidates.json")
LINKS_PATH = Path("data/arbitrage_search_links.json")

SOURCES = ["MercadoLibre", "Seminuevos", "Facebook Marketplace"]

CANDIDATE_SCHEMA = {
    "id": "string — identificador único, ej: ml-123456789",
    "source": "MercadoLibre | Seminuevos | Facebook Marketplace",
    "observedAt": "YYYY-MM-DD",
    "region": "CDMX | Edomex | Queretaro | Hidalgo | Puebla | Morelos | Michoacan",
    "city": "string",
    "year": "int",
    "brand": "string",
    "model": "string",
    "version": "string — version exacta de Kavak para cotizar correctamente",
    "km": "int | null",
    "publishedPrice": "int — precio publicado en pesos MXN",
    "url": "string — URL pública de la publicación",
    "kavakSellOffer": "int | null — oferta venta directa Kavak; null si aun no cotizado",
    "kavakQuoteUrl": "string | null — URL usada en kavak.com/mx/cotizar-auto",
    "kavakCapturedAt": "YYYY-MM-DD | null",
    "kavakValidUntil": "YYYY-MM-DD | null",
    "notes": "string — observaciones, version dudosa, km distinto, etc.",
}


def load_inventory() -> list[dict]:
    return [v for v in json.loads(INVENTORY_PATH.read_text()) if not v["excludedOrange"]]


def unique_models(vehicles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for v in vehicles:
        key = f"{v['brand']}|{v['model']}"
        if key not in seen:
            seen.add(key)
            result.append({"brand": v["brand"], "model": v["model"], "year": v["year"]})
    return sorted(result, key=lambda x: (x["brand"], x["model"]))


def search_url(source: str, brand: str, model: str, year: int) -> str:
    query = f"{brand} {model} {year}"
    if source == "MercadoLibre":
        slug = urllib.parse.quote_plus(query)
        return f"https://autos.mercadolibre.com.mx/{slug}"
    if source == "Seminuevos":
        slug = urllib.parse.quote_plus(query)
        return f"https://www.seminuevos.com/search?q={slug}"
    # Facebook Marketplace — abre búsqueda textual
    slug = urllib.parse.quote_plus(query + " seminuevo")
    return f"https://www.facebook.com/marketplace/search/?query={slug}&categoryId=vehicles"


def cmd_links() -> None:
    vehicles = load_inventory()
    models = unique_models(vehicles)
    links: list[dict] = []
    for m in models:
        for source in SOURCES:
            links.append({
                "brand": m["brand"],
                "model": m["model"],
                "year": m["year"],
                "source": source,
                "url": search_url(source, m["brand"], m["model"], m["year"]),
            })

    LINKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LINKS_PATH.write_text(json.dumps(links, ensure_ascii=False, indent=2))
    print(f"[links] {len(links)} búsquedas generadas → {LINKS_PATH}")
    print()
    print("SIGUIENTE PASO:")
    print("  Abre cada URL, busca publicaciones baratas (precio publicado < estimado Kavak).")
    print(f"  Registra candidatas en {CANDIDATES_PATH} siguiendo este esquema:")
    print()
    for field, desc in CANDIDATE_SCHEMA.items():
        print(f"    {field}: {desc}")
    print()
    print("  Luego cotiza cada una en kavak.com/mx/cotizar-auto y llena kavakSellOffer.")
    print(f"  Finalmente corre: python scripts/scan_arbitrage_candidates.py --score")


def cmd_validate(candidates: list[dict]) -> list[str]:
    errors: list[str] = []
    required = ["id", "source", "observedAt", "year", "brand", "model",
                "publishedPrice", "url"]
    for i, c in enumerate(candidates):
        for field in required:
            if field not in c or c[field] is None:
                errors.append(f"[{i}] {c.get('id', '?')} — falta campo '{field}'")
        if c.get("url", "").startswith("http") is False:
            errors.append(f"[{i}] {c.get('id', '?')} — url inválida: {c.get('url')}")
        if c.get("kavakSellOffer") is not None and c.get("kavakCapturedAt") is None:
            errors.append(f"[{i}] {c.get('id', '?')} — tiene kavakSellOffer pero falta kavakCapturedAt")
    return errors


def _is_expired(valid_until: str | None) -> bool:
    if not valid_until:
        return False
    try:
        return date.fromisoformat(valid_until) < date.today()
    except ValueError:
        return False


def cmd_score(candidates: list[dict]) -> None:
    today = date.today()
    results: list[dict] = []

    for c in candidates:
        offer = c.get("kavakSellOffer")
        published = c.get("publishedPrice")

        if offer is None or published is None:
            status = "pendiente_kavak" if offer is None else "sin_precio"
            results.append({**c, "status": status, "spread": None, "spreadPct": None})
            continue

        if _is_expired(c.get("kavakValidUntil")):
            results.append({**c, "status": "cotizacion_expirada", "spread": None, "spreadPct": None})
            continue

        spread = offer - published          # positivo = arbitraje real
        spread_pct = round(spread / published, 4)
        status = "arbitraje" if spread > 0 else "sin_margen"
        results.append({**c, "status": status, "spread": spread, "spreadPct": spread_pct})

    arbitraje = [r for r in results if r["status"] == "arbitraje"]
    pendiente = [r for r in results if r["status"] == "pendiente_kavak"]
    sin_margen = [r for r in results if r["status"] == "sin_margen"]
    expiradas = [r for r in results if r["status"] == "cotizacion_expirada"]

    arbitraje.sort(key=lambda r: r["spread"], reverse=True)

    print(f"[score] Fecha: {today}")
    print(f"[score] Total candidatas: {len(candidates)}")
    print(f"[score] Arbitraje real (precio < Kavak):   {len(arbitraje)}")
    print(f"[score] Pendientes de cotizar:             {len(pendiente)}")
    print(f"[score] Sin margen (precio >= Kavak):      {len(sin_margen)}")
    print(f"[score] Cotización expirada:               {len(expiradas)}")
    print()

    if arbitraje:
        print("=== RANKING ARBITRAJE ===")
        for rank, r in enumerate(arbitraje, 1):
            print(
                f"  #{rank} {r['year']} {r['brand']} {r['model']}"
                f" | pub: ${r['publishedPrice']:,}"
                f" | kavak: ${r['kavakSellOffer']:,}"
                f" | spread: +${r['spread']:,} ({r['spreadPct']*100:.1f}%)"
                f" | {r['city'] if r.get('city') else r['source']}"
            )
    else:
        print("  Sin arbitraje confirmado aún. Agrega más candidatas o cotiza las pendientes.")

    if pendiente:
        print()
        print(f"=== PENDIENTES DE COTIZAR ({len(pendiente)}) ===")
        for r in pendiente:
            print(f"  {r['year']} {r['brand']} {r['model']} — {r['url']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Barrido candidatas arbitraje Kavak")
    parser.add_argument("--links", action="store_true", help="Genera links de búsqueda")
    parser.add_argument("--score", action="store_true", help="Calcula spreads y ranking")
    parser.add_argument("--validate", action="store_true", help="Valida el JSON de candidatas")
    args = parser.parse_args()

    if args.links:
        cmd_links()
        return

    if not CANDIDATES_PATH.exists():
        print(f"[error] No existe {CANDIDATES_PATH}")
        print("  Corre primero: python scripts/scan_arbitrage_candidates.py --links")
        print(f"  Luego crea {CANDIDATES_PATH} con la lista de candidatas.")
        return

    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))

    if args.validate:
        errors = cmd_validate(candidates)
        if errors:
            print(f"[validate] {len(errors)} errores:")
            for e in errors:
                print(f"  {e}")
        else:
            print(f"[validate] OK — {len(candidates)} candidatas válidas")
        return

    if args.score:
        errors = cmd_validate(candidates)
        if errors:
            print(f"[score] Errores de validación ({len(errors)}), corrígelos primero:")
            for e in errors:
                print(f"  {e}")
            return
        cmd_score(candidates)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
