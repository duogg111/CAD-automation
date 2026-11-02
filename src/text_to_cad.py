"""Parse Vietnamese rectangular-prism descriptions into a validated CAD plan."""
from __future__ import annotations
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

NUMBER = r"(\d+(?:[.,]\d+)?)"
TAP_SPECS = {
    "M3": {"thread_diameter_mm": 3.0, "tap_drill_diameter_mm": 2.5, "pitch_mm": 0.5},
    "M4": {"thread_diameter_mm": 4.0, "tap_drill_diameter_mm": 3.3, "pitch_mm": 0.7},
}

class ParseError(ValueError):
    """Raised when a description lacks enough unambiguous data."""

@dataclass
class Feature:
    kind: str
    parameters: dict[str, Any]

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
        hole_feature = requested.get("holes") or requested.get("tapped_holes")
        hole_is_supported = (
            hole_feature is not None
            and hole_feature.parameters.get("layout") in {
                "four_corners", "center_to_center_x", "center_to_center_y",
                "explicit_points", "single_center",
            }
        )
        data["execution_status"] = {
            "base_solid": "supported",
            "fillet": "verified_on_user_SOLIDWORKS" if "fillet" in requested else "not_requested",
            "chamfer": (
                "implemented_pending_SOLIDWORKS_verification"
                if "chamfer" in requested else "not_requested"
            ),
            "holes": (
                "implemented_pending_SOLIDWORKS_verification"
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

def _parse_xy_points(text: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for match in re.finditer(
        rf"\(\s*{NUMBER}\s*[,;]\s*{NUMBER}\s*\)",
        text,
    ):
        points.append((_number(match.group(1)), _number(match.group(2))))
    if points:
        return points

    xy_match = re.search(
        rf"\bx\s*[:=]?\s*{NUMBER}\s*(?:,|;|\s+)\s*y\s*[:=]?\s*{NUMBER}\b",
        text,
    )
    if xy_match:
        points.append((_number(xy_match.group(1)), _number(xy_match.group(2))))
    return points

def _parse_hole_layout(
    text: str,
    count: int,
    warnings: list[str],
) -> dict[str, Any]:
    points = _parse_xy_points(text)
    if points:
        if len(points) != count:
            raise ParseError(
                f"Mo ta co {len(points)} cap toa do nhung yeu cau {count} lo. "
                "Hay cung cap dung mot toa do (X,Y) cho moi lo."
            )
        return {"layout": "explicit_points", "centers_mm": points}

    pitch_match = re.search(
        rf"(?:tam\s*[- ]?\s*tam|khoang cach tam(?:\s*[- ]?\s*tam)?|cach nhau)\s*{NUMBER}\s*(?:mm)?",
        text,
    )
    if pitch_match:
        if count != 2:
            raise ParseError("Bo cuc theo khoang cach tam-tam hien ho tro dung 2 lo.")
        axis = "y" if re.search(r"theo\s+(?:chieu\s+)?rong|doc\s+chieu\s+rong", text) else "x"
        return {
            "layout": "center_to_center_" + axis,
            "center_distance_mm": _number(pitch_match.group(1)),
            "axis": axis,
        }

    offset_match = re.search(
        rf"\bcach\s+(?:mep|canh)\s*{NUMBER}\s*(?:mm)?\b",
        text,
    )
    if count == 4:
        offset_explicit = offset_match is not None
        edge_offset = _number(offset_match.group(1)) if offset_match else 10.0
        if not offset_explicit:
            warnings.append(
                "Chua ghi khoang cach lo den mep: tam 4 lo duoc de xuat cach moi mep 10 mm."
            )
        return {
            "layout": "four_corners",
            "edge_offset_mm": edge_offset,
            "offset_was_defaulted": not offset_explicit,
        }

    if count == 1:
        return {"layout": "single_center"}

    return {"layout": "unspecified"}

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

    # ISO coarse metric tapped holes, M3 and M4 only in this milestone.
    tap_match = re.search(
        r"(?:(\d+)\s*lo\s*)?(?:(?:lo\s*)?ren\s*|(?:ta\s*ro|taro)\s*)?m\s*([34])(?:\s*x\s*[\d,.]+)?\b",
        text,
    )
    has_tap_context = bool(re.search(r"\b(lo|ren|ta\s*ro|taro)\b", text))
    if tap_match and has_tap_context:
        count = int(tap_match.group(1) or 1)
        size = "M" + tap_match.group(2)
        if count <= 0:
            raise ParseError("So luong lo ren phai lon hon 0.")
        layout = _parse_hole_layout(text, count, warnings)
        spec = TAP_SPECS[size]
        features.append(
            Feature(
                "tapped_holes",
                {
                    "count": count,
                    "size": size,
                    "standard": "ISO metric coarse",
                    **spec,
                    **layout,
                },
            )
        )
        if size == "M3":
            warnings.append("Lo ren M3 mac dinh dung buoc ren ISO coarse 0,5 mm va mui khoan taro 2,5 mm.")
        else:
            warnings.append("Lo ren M4 mac dinh dung buoc ren ISO coarse 0,7 mm va mui khoan taro 3,3 mm.")
        warnings.append(
            "Lo ren duoc tao bang Hole Wizard (tap hole) voi chi tiet ren/cosmetic thread; "
            "khong phai ren xoan 3D duoc mo hinh hoa."
        )
    else:
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
            layout = _parse_hole_layout(text, count, warnings)
            features.append(
                Feature("holes", {"count": count, "diameter_mm": diameter, **layout})
            )
            if layout["layout"] == "unspecified":
                warnings.append(
                    "Bo tri nay chua duoc ho tro tu dong; lo chi duoc phan tich, khong tu dat vi tri."
                )

    if "chamfer" in {feature.kind for feature in features}:
        warnings.append("Chamfer se duoc dat tren 4 canh bao quanh mat tren cua hop.")
    if "fillet" in {feature.kind for feature in features}:
        warnings.append("Fillet se duoc dat tren 4 canh dung ngoai cua hop.")
    if "holes" in {feature.kind for feature in features}:
        warnings.append("Lo khoan thong thuong duoc tao bang Cut-Extrude Through All.")
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
        (float(f.parameters["radius_mm"]) for f in features if f.kind == "fillet"), 0.0
    )
    chamfer_distance = next(
        (float(f.parameters["distance_mm"]) for f in features if f.kind == "chamfer"), 0.0
    )

    if fillet_radius >= min(dimensions["length"], dimensions["width"]) / 2.0:
        raise ParseError(f"Fillet R{fillet_radius:g} mm qua lon so voi mat day cua hop.")
    if chamfer_distance and chamfer_distance >= min(
        dimensions["length"], dimensions["width"], dimensions["height"]
    ) / 2.0:
        raise ParseError("Chamfer qua lon so voi kich thuoc hop.")

    for feature in features:
        if feature.kind == "holes":
            diameter = float(feature.parameters["diameter_mm"])
            drill_diameter = diameter
        elif feature.kind == "tapped_holes":
            drill_diameter = float(feature.parameters["tap_drill_diameter_mm"])
            diameter = drill_diameter
        else:
            continue

        layout = feature.parameters.get("layout")
        if layout == "four_corners":
            offset = float(feature.parameters["edge_offset_mm"])
            radius = diameter / 2.0
            required_offset = max(
                chamfer_distance + radius + 0.25,
                fillet_radius + (fillet_radius + radius + 0.25) / (2.0 ** 0.5),
            )
            if offset <= required_offset:
                raise ParseError(
                    f"Khoang cach tam lo den mep phai lon hon {required_offset:g} mm "
                    "de tranh giao voi cac feature canh."
                )
        elif layout == "center_to_center_x":
            pitch = float(feature.parameters["center_distance_mm"])
            if pitch <= diameter:
                raise ParseError("Khoang cach tam-tam phai lon hon duong kinh lo.")
            if pitch / 2.0 + diameter / 2.0 >= dimensions["length"] / 2.0:
                raise ParseError("Cap lo theo chieu dai khong vua tren mat hop.")
        elif layout == "center_to_center_y":
            pitch = float(feature.parameters["center_distance_mm"])
            if pitch <= diameter:
                raise ParseError("Khoang cach tam-tam phai lon hon duong kinh lo.")
            if pitch / 2.0 + diameter / 2.0 >= dimensions["width"] / 2.0:
                raise ParseError("Cap lo theo chieu rong khong vua tren mat hop.")
        elif layout == "explicit_points":
            points = feature.parameters["centers_mm"]
            for x, y in points:
                if not (0.0 < x < dimensions["length"] and 0.0 < y < dimensions["width"]):
                    raise ParseError(f"Toa do lo ({x:g}, {y:g}) nam ngoai mat tren.")
                edge_clearance = min(x, dimensions["length"] - x, y, dimensions["width"] - y)
                required_edge = chamfer_distance + diameter / 2.0 + 0.25
                if edge_clearance <= required_edge:
                    raise ParseError(
                        f"Toa do lo ({x:g}, {y:g}) qua sat mep/vat canh; "
                        f"can cach moi mep hon {required_edge:g} mm."
                    )
                if fillet_radius:
                    corner_centers = [
                        (fillet_radius, fillet_radius),
                        (dimensions["length"] - fillet_radius, fillet_radius),
                        (dimensions["length"] - fillet_radius, dimensions["width"] - fillet_radius),
                        (fillet_radius, dimensions["width"] - fillet_radius),
                    ]
                    min_corner_distance = min(
                        ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                        for cx, cy in corner_centers
                    )
                    if min_corner_distance <= fillet_radius + diameter / 2.0 + 0.25:
                        raise ParseError(
                            f"Toa do lo ({x:g}, {y:g}) qua gan cung Fillet goc."
                        )
        elif layout == "single_center":
            if min(dimensions["length"], dimensions["width"]) <= diameter + 2 * chamfer_distance:
                raise ParseError("Lo tam khong du khoang cach voi mep hop.")

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
