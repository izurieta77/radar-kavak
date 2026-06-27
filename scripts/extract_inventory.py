from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import fitz

PDF_PATH = Path(
    os.environ.get(
        "RADAR_KAVAK_PDF",
        r"C:\Users\WorkStation\.codex\codex-remote-attachments\019f0abe-3d00-7272-8a2a-d4bb995adcac\F57CD5E5-384C-45B2-848C-DB7E129251D7\1-INVENTARIO-GENERAL-SEMINUEVOS-BMW-CEVER-SEMINUEVOS-BMW-SANTA-FE-4-11.06.42-a.m..pdf",
    )
)

COLUMNS = [
    ("no", 17.0, 50.5),
    ("brand", 50.5, 133.7),
    ("model", 133.7, 370.3),
    ("year", 370.3, 429.4),
    ("kilometers", 429.4, 495.0),
    ("exteriorColor", 495.0, 619.0),
    ("interiorColor", 619.0, 765.0),
    ("inventoryPrice", 765.0, 874.0),
    ("invoiceTax", 874.0, 990.6),
]


def column_for(x: float) -> str | None:
    for name, x0, x1 in COLUMNS:
        if x0 <= x < x1:
            return name
    return None


def parse_int(value: str) -> int | None:
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def parse_price(value: str) -> int | None:
    cleaned = re.sub(r"[^\d.]", "", value)
    if not cleaned:
        return None
    return int(round(float(cleaned)))


def colored_rects(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    rects: list[tuple[str, fitz.Rect]] = []
    for drawing in page.get_drawings():
        fill = drawing.get("fill")
        rect = drawing.get("rect")
        if not fill or rect is None:
            continue
        rgb = tuple(round(channel, 3) for channel in fill)
        if rgb == (1.0, 0.6, 0.0):
            rects.append(("orange", rect))
        elif rgb in {(0.918, 0.82, 0.863), (0.957, 0.8, 0.8)}:
            rects.append(("pink", rect))
    return rects


def hits(rect: fitz.Rect, y_center: float, x0: float, x1: float) -> bool:
    return rect.y0 <= y_center <= rect.y1 and rect.x0 <= x1 and rect.x1 >= x0


def extract_inventory(pdf_path: Path) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    rows: list[dict[str, Any]] = []

    for page_index, page in enumerate(doc, start=1):
        words = page.get_text("words")
        anchors: list[tuple[int, float, float, float]] = []
        for word in words:
            x0, y0, x1, y1, text, *_ = word
            if 17 <= x0 <= 50.5 and re.fullmatch(r"\d+", text):
                anchors.append((int(text), (y0 + y1) / 2, y0, y1))
        anchors.sort(key=lambda item: item[1])
        rects = colored_rects(page)

        for index, (number, y_center, y0, y1) in enumerate(anchors):
            top = (anchors[index - 1][1] + y_center) / 2 if index else y0 - 3
            bottom = (y_center + anchors[index + 1][1]) / 2 if index + 1 < len(anchors) else y1 + 3
            fields: dict[str, list[tuple[float, str]]] = {name: [] for name, *_ in COLUMNS}
            for word in words:
                x0, wy0, x1, wy1, text, *_ = word
                wy_center = (wy0 + wy1) / 2
                if top <= wy_center < bottom:
                    column = column_for((x0 + x1) / 2)
                    if column:
                        fields[column].append((x0, text))

            raw = {
                column: " ".join(text for _, text in sorted(values, key=lambda item: item[0]))
                for column, values in fields.items()
            }
            orange = any(kind == "orange" and hits(rect, y_center, 50, 990.6) for kind, rect in rects)
            pink = any(kind == "pink" and hits(rect, y_center, 17, 50.5) for kind, rect in rects)

            rows.append(
                {
                    "page": page_index,
                    "no": number,
                    "brand": raw["brand"].strip(),
                    "model": raw["model"].strip(),
                    "year": parse_int(raw["year"]) or 0,
                    "kilometers": parse_int(raw["kilometers"]),
                    "exteriorColor": raw["exteriorColor"].strip(),
                    "interiorColor": raw["interiorColor"].strip(),
                    "inventoryPrice": parse_price(raw["inventoryPrice"]),
                    "invoiceTax": raw["invoiceTax"].strip(),
                    "excludedOrange": orange,
                    "pinkNumberCell": pink,
                }
            )
    return rows


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(f"PDF not found: {PDF_PATH}")

    rows = extract_inventory(PDF_PATH)
    for output in [Path("data/inventario.json"), Path("src/data/inventario.json")]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "total": len(rows),
                "excludedOrange": sum(1 for row in rows if row["excludedOrange"]),
                "analyzable": sum(1 for row in rows if not row["excludedOrange"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

