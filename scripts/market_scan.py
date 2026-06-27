from __future__ import annotations

import csv
import json
import urllib.parse
from pathlib import Path

INVENTORY_PATH = Path("data/inventario.json")
OUTPUT_PATH = Path("data/market_links.csv")
ZONES = ["Toluca", "CDMX", "Metepec"]


def search_url(brand: str, model: str, year: int, zone: str) -> str:
    query = f"{brand} {model} {year} {zone} seminuevo"
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)


def main() -> None:
    vehicles = [
        vehicle
        for vehicle in json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
        if not vehicle["excludedOrange"]
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["no", "brand", "model", "year", "zone", "url"])
        writer.writeheader()
        for vehicle in vehicles:
            for zone in ZONES:
                writer.writerow(
                    {
                        "no": vehicle["no"],
                        "brand": vehicle["brand"],
                        "model": vehicle["model"],
                        "year": vehicle["year"],
                        "zone": zone,
                        "url": search_url(vehicle["brand"], vehicle["model"], vehicle["year"], zone),
                    }
                )
    print(f"wrote {OUTPUT_PATH} with {len(vehicles) * len(ZONES)} links")


if __name__ == "__main__":
    main()

