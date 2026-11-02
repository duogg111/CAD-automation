"""Parse a small, explicit subset of Vietnamese part descriptions.

This module creates a validated CAD plan. SOLIDWORKS geometry execution is
kept separate so unsupported or ambiguous features cannot silently create a wrong model.
"""
from __future__ import annotations
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

NUMBER = r"(\d+(?:[.,]\d+)?)"

class ParseError(ValueError):
    """Raised when a description lacks enough unambiguous data."""

@dataclass
class Feature:
    kind: str
    parameters: dict[str, float | int | str]

@dataclass
class CADPlan:
    source_text: str
    shape: str
    dimensions_mm: dict[str, float]
    features: list[Feature] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["execution_status"] = {
            "base_solid": "supported_by_existing_com_script",
            "fillet": "supported_on_four_vertical_outer_edges",
            "chamfer": "preview_only",
            "holes": "preview_only",
        }
        return data

def _normalise(text: str) -> str:
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip()

def _number(value: str) -> float:
    return float(value.replace(",", "."))

def _labelled_dimension(text: str, labels: str) -> float | None:
    pattern = rf"\b(?:{labels})\s*(?:la|:|=)?\s*{NUMBER}\s*(?:mm|milimet(?:er)?)?\b"
    match = re.search(pattern, text)
    return _number(match.group(1)) if match else None

def _parse_dimensions(text: str) -> dict[str, float]:
    dimensions = {
        "length": _labelled_dimension(text, r"dai|chieu dai"),
        "width": _labelled_dimension(text, r"rong|chieu rong"),
        "height": _labelled_dimension(text, r"cao|chieu cao"),
    }
    if any(value is None for value in dimensions.values()):
        tuple_match = re.search(
            rf"\b{NUMBER}\s*[x×]\s*{NUMBER}\s*[x×]\s*{NUMBER}\s*(?:mm)?\b",
            text,
        )
        if tuple_match:
            values = [_number(tuple_match.group(i)) for i in (1, 2, 3)]
            for key, value in zip(("length", "width", "height"), values):
                if dimensions[key] is None:
                    dimensions[key] = value
    missing = [key for key, value in dimensions.items() if value is None]
    if missing:
        raise ParseError(
            "Thieu kich thuoc: " + ", ".join(missing)
            + ". Hay ghi ro dai, rong, cao hoac dung dang 100 x 60 x 30 mm."
        )
    result = {key: float(value) for key, value in dimensions.items()}
    invalid = [key for key, value in result.items() if value <= 0]
    if invalid:
        raise ParseError("Kich thuoc phai lon hon 0: " + ", ".join(invalid))
    return result

def _parse_features(text: str) -> tuple[list[Feature], list[str]]:
    features: list[Feature] = []
    warnings: list[str] = []
    fillet = re.search(
        rf"\bbo\s*(?:tron\s*)?(?:goc|canh)?\s*(?:ban kinh\s*)?(?:r\s*)?{NUMBER}\s*(?:mm)?\b",
        text,
    )
    if fillet:
        radius = _number(fillet.group(1))
        if radius <= 0:
            raise ParseError("Ban kinh Fillet phai lon hon 0 mm.")
        features.append(
            Feature("fillet", {"radius_mm": radius, "target": "four_vertical_outer_edges"})
        )

    chamfer = re.search(
        rf"\b(?:vat canh|chamfer)\s*(?:kich thuoc\s*)?{NUMBER}\s*(?:mm)?\b",
        text,
    )
    if chamfer:
        distance = _number(chamfer.group(1))
        if distance <= 0:
            raise ParseError("Kich thuoc Chamfer phai lon hon 0 mm.")
        features.append(Feature("chamfer", {"distance_mm": distance}))

    holes = re.search(
        rf"(?:\b(\d+)\s*lo\b|\blo\s*(\d+)\b).*?"
        rf"(?:duong kinh|phi|d\s*=?\s*)\s*{NUMBER}\s*(?:mm)?\b",
        text,
    )
    if holes:
        count = int(holes.group(1) or holes.group(2))
        diameter = _number(holes.group(3))
        if count <= 0 or diameter <= 0:
            raise ParseError("So luong lo va duong kinh phai lon hon 0.")
        features.append(Feature("holes", {"count": count, "diameter_mm": diameter}))

    unsupported = [feature.kind for feature in features if feature.kind != "fillet"]
    if unsupported:
        warnings.append(
            "Chamfer va holes moi chi duoc phan tich; chua duoc gui len SOLIDWORKS."
        )
    return features, warnings

def parse_description(description: str) -> CADPlan:
    """Convert a Vietnamese description into a validated, previewable CAD plan."""
    if not isinstance(description, str) or not description.strip():
        raise ParseError("Mo ta khong duoc de trong.")
    text = _normalise(description)
    if not re.search(r"\b(hop|khoi hop|box|block)\b", text):
        raise ParseError("Phien ban nay chi ho tro khoi hop chu nhat.")
    dimensions = _parse_dimensions(text)
    features, warnings = _parse_features(text)

    for feature in features:
        if feature.kind == "fillet":
            radius = float(feature.parameters["radius_mm"])
            max_radius = min(dimensions["length"], dimensions["width"]) / 2.0
            if radius >= max_radius:
                raise ParseError(
                    f"Fillet R{radius:g} mm qua lon. "
                    f"Voi hop nay, ban kinh phai nho hon {max_radius:g} mm "
                    "de bo bon canh dung."
                )
    return CADPlan(description.strip(), "rectangular_prism", dimensions, features, warnings)

def plan_as_json(description: str) -> str:
    return json.dumps(parse_description(description).to_dict(), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import argparse
    cli = argparse.ArgumentParser(description="Vietnamese text-to-CAD plan preview")
    cli.add_argument("description", nargs="?")
    args = cli.parse_args()
    user_text = args.description or input("Mo ta chi tiet can ve: ")
    try:
        print(plan_as_json(user_text))
    except ParseError as exc:
        cli.error(str(exc))
