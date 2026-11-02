"""Parse Vietnamese rectangular-prism descriptions into a validated CAD plan."""
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
        requested = {feature.kind: feature for feature in self.features}
        hole_feature = requested.get("holes")
        hole_is_supported = (
            hole_feature is not None
            and hole_feature.parameters.get("layout") == "four_corners"
            and int(hole_feature.parameters.get("count", 0)) == 4
        )
        data["execution_status"] = {
            "base_solid": "supported",
            "fillet": (
                "supported_on_four_vertical_outer_edges"
                if "fillet" in requested else "not_requested"
            ),
            "chamfer": (
                "supported_on_four_top_perimeter_edges"
                if "chamfer" in requested else "not_requested"
            ),
            "holes": (
                "supported_for_four_corner_through_holes"
                if hole_is_supported
                else ("preview_only" if hole_feature is not None else "not_requested")
            ),
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
        rf"\b(?:vat\s*(?:canh|mep(?:\s+tren)?)|chamfer)\s*(?:kich thuoc\s*)?{NUMBER}\s*(?:mm)?\b",
        text,
    )
    if chamfer:
        distance = _number(chamfer.group(1))
        if distance <= 0:
            raise ParseError("Kich thuoc Chamfer phai lon hon 0 mm.")
        features.append(
            Feature("chamfer", {"distance_mm": distance, "target": "four_top_perimeter_edges"})
        )

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
        offset_match = re.search(
            rf"\bcach\s+(?:mep|canh)\s*{NUMBER}\s*(?:mm)?\b",
            text,
        )
        offset_explicit = offset_match is not None
        edge_offset = _number(offset_match.group(1)) if offset_match else 10.0
        if count == 4:
            features.append(
                Feature(
                    "holes",
                    {
                        "count": count,
                        "diameter_mm": diameter,
                        "layout": "four_corners",
                        "edge_offset_mm": edge_offset,
                        "offset_was_defaulted": not offset_explicit,
                    },
                )
            )
            if not offset_explicit:
                warnings.append(
                    "Chua ghi khoang cach lo den mep: tam 4 lo duoc dat cach moi mep 10 mm theo mac dinh."
                )
        else:
            features.append(
                Feature(
                    "holes",
                    {
                        "count": count,
                        "diameter_mm": diameter,
                        "layout": "unspecified",
                    },
                )
            )
            warnings.append(
                "Chi ho tro tao lo tu dong cho bo cuc 4 lo o bon goc; so lo khac moi chi duoc phan tich."
            )

    requested_kinds = {feature.kind for feature in features}
    if "chamfer" in requested_kinds:
        warnings.append(
            "Chamfer se duoc dat tren 4 canh bao quanh mat tren cua hop."
        )
    if "fillet" in requested_kinds:
        warnings.append(
            "Fillet se duoc dat tren 4 canh dung ngoai cua hop."
        )
    if "holes" in requested_kinds:
        warnings.append(
            "Bo cuc 4 lo tu dong la lo xuyen Through All; cac bo cuc khac chi hien preview."
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

    fillet_radius = next(
        (float(f.parameters["radius_mm"]) for f in features if f.kind == "fillet"),
        0.0,
    )
    chamfer_distance = next(
        (float(f.parameters["distance_mm"]) for f in features if f.kind == "chamfer"),
        0.0,
    )
    if fillet_radius >= min(dimensions["length"], dimensions["width"]) / 2.0:
        raise ParseError(
            f"Fillet R{fillet_radius:g} mm qua lon so voi mat day cua hop."
        )
    if chamfer_distance and (
        chamfer_distance >= min(
            dimensions["length"], dimensions["width"], dimensions["height"]
        ) / 2.0
    ):
        raise ParseError("Chamfer qua lon so voi kich thuoc hop.")

    for feature in features:
        if feature.kind == "holes" and feature.parameters.get("layout") == "four_corners":
            diameter = float(feature.parameters["diameter_mm"])
            offset = float(feature.parameters["edge_offset_mm"])
            hole_radius = diameter / 2.0
            safety_margin = 0.25
            corner_fillet_limit = (
                fillet_radius
                + (fillet_radius + hole_radius + safety_margin) / (2.0 ** 0.5)
            )
            straight_edge_limit = chamfer_distance + hole_radius + safety_margin
            required_offset = max(
                hole_radius + safety_margin,
                corner_fillet_limit,
                straight_edge_limit,
            )
            if offset <= required_offset:
                raise ParseError(
                    f"Khoang cach tam lo den mep phai lon hon {required_offset:g} mm "
                    "de tranh giao voi lo, canh vat va cung Fillet o goc."
                )
            if (
                dimensions["length"] - 2.0 * offset <= diameter
                or dimensions["width"] - 2.0 * offset <= diameter
            ):
                raise ParseError(
                    "4 lo khong vua voi mat tren. Hay giam duong kinh/khoang cach mep "
                    "hoac tang kich thuoc hop."
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
