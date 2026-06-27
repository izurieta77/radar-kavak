from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

INVENTORY_PATH = Path("data/inventario.json")

BRAND_MAP = {
    "BMW": "Bmw",
    "MINI": "Mini",
    "Land-Rover": "Land Rover",
    "Mercedes-Benz": "Mercedes Benz",
    "Tesla": "Tesla",
    "KIA": "Kia",
    "Volvo": "Volvo",
    "Volkswagen": "Volkswagen",
    "Ford": "Ford",
}


def kavak_model_hint(model: str) -> str:
    lowered = model.lower()
    for token in ["X1", "X2", "X3", "X4", "X5", "X6", "X7", "iX3", "iX"]:
        if token.lower() in lowered:
            return token
    if "330e" in lowered:
        return "Serie 3"
    if "118i" in lowered:
        return "Serie 1"
    if "model y" in lowered:
        return "Model Y"
    if "countryman" in lowered:
        return "Countryman"
    if "cooper" in lowered:
        return "Cooper"
    return model.split()[0]


def open_browser(url: str) -> None:
    if sys.platform.startswith("win"):
        subprocess.run(["cmd", "/c", "start", "", url], check=False)
    else:
        subprocess.run(["python", "-m", "webbrowser", url], check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Open an assisted Kavak quote flow for one inventory row.")
    parser.add_argument("--no", type=int, required=True, help="Inventory row number to probe.")
    parser.add_argument("--open", action="store_true", help="Open Kavak in the default browser.")
    args = parser.parse_args()

    vehicles = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    vehicle = next((item for item in vehicles if item["no"] == args.no), None)
    if vehicle is None:
        raise SystemExit(f"No inventory row found for no={args.no}")
    if vehicle["excludedOrange"]:
        raise SystemExit(f"Row {args.no} is excluded because it is fully orange.")

    brand = BRAND_MAP.get(vehicle["brand"], vehicle["brand"])
    model_hint = kavak_model_hint(vehicle["model"])
    url = "https://www.kavak.com/mx/vender-mi-auto"
    print(json.dumps(
        {
            "row": vehicle["no"],
            "year": vehicle["year"],
            "brand": brand,
            "modelHint": model_hint,
            "kilometers": vehicle["kilometers"],
            "url": url,
            "instructions": [
                "Selecciona año, marca y modelo en Kavak.",
                "Continua hasta capturar oferta o rango.",
                "Si aparece captcha/OTP, resuelvelo manualmente.",
                "No agendes cita ni aceptes operacion desde este flujo.",
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))
    if args.open:
        open_browser(url)


if __name__ == "__main__":
    main()

