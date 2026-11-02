"""SOLIDWORKS feature helpers for the rectangular-prism starter."""
from __future__ import annotations
import types
from typing import Any

# Documented SOLIDWORKS SwConst enum values used by this project.
SW_FM_FILLET = 1
SW_CONST_RADIUS_FILLET = 0
SW_FEATURE_FILLET_CIRCULAR = 0
SW_FEATURE_FILLET_CONIC_RHO_ZERO_CHAMFER = 3
SW_FILLET_OVERFLOW_DEFAULT = 0
SW_END_COND_THROUGH_ALL = 1


def _call_member(obj: Any, name: str, *args: Any) -> Any:
    """Read zero-argument COM members without invoking a returned dispatch value."""
    member = getattr(obj, name)
    if args:
        return member(*args)
    if isinstance(member, types.MethodType):
        return member()
    return member


def _as_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (tuple, list)):
        return list(value)
    try:
        return list(value)
    except TypeError:
        return [value]


def _vertex_point(vertex: Any) -> tuple[float, float, float]:
    if vertex is None:
        raise ValueError("An edge does not have two finite endpoint vertices.")
    point = _call_member(vertex, "GetPoint")
    if point is None or len(point) < 3:
        raise ValueError("SOLIDWORKS returned an invalid vertex point.")
    return (float(point[0]), float(point[1]), float(point[2]))


def is_vertical_extrusion_edge(
    start_point: tuple[float, float, float],
    end_point: tuple[float, float, float],
    extrusion_depth_mm: float,
    tolerance_m: float = 1e-7,
) -> bool:
    """Match a vertical edge segment, including one shortened by top chamfer."""
    expected_depth_m = float(extrusion_depth_mm) / 1000.0
    dx = abs(end_point[0] - start_point[0])
    dy = abs(end_point[1] - start_point[1])
    dz = abs(end_point[2] - start_point[2])
    tol = max(float(tolerance_m), expected_depth_m * 1e-6)
    return (
        dx <= tol
        and dy <= tol
        and dz > tol
        and dz <= expected_depth_m + tol
    )


def _get_solid_bodies(model: Any) -> list[Any]:
    try:
        result = _call_member(model, "GetBodies2", 0, False)  # swSolidBody = 0
        return _as_items(result)
    except Exception:
        import win32com.client
        last_error: Exception | None = None
        for interface_name in ("PartDoc", "IPartDoc"):
            try:
                part_doc = win32com.client.CastTo(model, interface_name)
                result = _call_member(part_doc, "GetBodies2", 0, False)
                return _as_items(result)
            except Exception as cast_error:
                last_error = cast_error
        raise RuntimeError(
            "Could not access IPartDoc.GetBodies2 through the current COM wrapper. "
            "Check that the SOLIDWORKS Type Library MakePy wrapper is generated."
        ) from last_error


def _edge_endpoints(edge: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    start_vertex = _call_member(edge, "GetStartVertex")
    end_vertex = _call_member(edge, "GetEndVertex")
    if start_vertex is None or end_vertex is None:
        raise ValueError("Edge has no start/end vertex.")
    return _vertex_point(start_vertex), _vertex_point(end_vertex)


def get_box_vertical_edges(model: Any, extrusion_depth_mm: float) -> list[Any]:
    """Find the four vertical corner edges, even after top-edge chamfer."""
    bodies = _get_solid_bodies(model)
    if len(bodies) != 1:
        raise RuntimeError(
            "Expected exactly one solid body before vertical-edge operation, "
            f"but SOLIDWORKS returned {len(bodies)}."
        )
    body_edges = _as_items(_call_member(bodies[0], "GetEdges"))
    vertical_edges: list[Any] = []
    for edge in body_edges:
        try:
            start_point, end_point = _edge_endpoints(edge)
        except (ValueError, TypeError):
            continue
        if is_vertical_extrusion_edge(start_point, end_point, extrusion_depth_mm):
            vertical_edges.append(edge)
    if len(vertical_edges) != 4:
        raise RuntimeError(
            "Could not identify the four vertical box edges. "
            f"Expected 4, found {len(vertical_edges)}. "
            "Check the Part template plane/orientation and extrusion direction."
        )
    return vertical_edges


def get_box_top_perimeter_edges(model: Any, height_mm: float) -> list[Any]:
    """Find the four top perimeter edges before the vertical-corner Fillet."""
    bodies = _get_solid_bodies(model)
    if len(bodies) != 1:
        raise RuntimeError(
            "Expected exactly one solid body before top Chamfer, "
            f"but SOLIDWORKS returned {len(bodies)}."
        )
    top_z = float(height_mm) / 1000.0
    tolerance = max(1e-7, top_z * 1e-6)
    body_edges = _as_items(_call_member(bodies[0], "GetEdges"))
    top_edges: list[Any] = []
    for edge in body_edges:
        try:
            start_point, end_point = _edge_endpoints(edge)
        except (ValueError, TypeError):
            continue
        both_on_top = (
            abs(start_point[2] - top_z) <= tolerance
            and abs(end_point[2] - top_z) <= tolerance
        )
        edge_length_xy = (
            (end_point[0] - start_point[0]) ** 2
            + (end_point[1] - start_point[1]) ** 2
        ) ** 0.5
        if both_on_top and edge_length_xy > tolerance:
            top_edges.append(edge)
    if len(top_edges) != 4:
        raise RuntimeError(
            "Could not identify the four top perimeter edges for Chamfer. "
            f"Expected 4, found {len(top_edges)}. "
            "Chamfer is applied before the corner Fillet in this workflow."
        )
    return top_edges


def _select_edges(model: Any, edges: list[Any], label: str) -> None:
    model.ClearSelection2(True)
    selection_data = _call_member(model.SelectionManager, "CreateSelectData")
    selection_data.Mark = 1
    for index, edge in enumerate(edges):
        if not edge.Select4(index > 0, selection_data):
            model.ClearSelection2(True)
            raise RuntimeError(
                f"SOLIDWORKS could not select edge {index + 1}/{len(edges)} for {label}."
            )


def apply_top_perimeter_chamfer(
    model: Any,
    distance_mm: float,
    extrusion_height_mm: float,
) -> Any:
    """Create a symmetric offset-face chamfer on the four top perimeter edges."""
    distance_mm = float(distance_mm)
    extrusion_height_mm = float(extrusion_height_mm)
    if distance_mm <= 0:
        raise ValueError("Chamfer distance must be greater than zero.")
    if extrusion_height_mm <= 0:
        raise ValueError("Extrusion height must be greater than zero.")

    edges = get_box_top_perimeter_edges(model, extrusion_height_mm)
    _select_edges(model, edges, "top perimeter Chamfer")

    feature_manager = model.FeatureManager
    chamfer_data = feature_manager.CreateDefinition(SW_FM_FILLET)
    if chamfer_data is None:
        model.ClearSelection2(True)
        raise RuntimeError("FeatureManager.CreateDefinition(swFmFillet) returned None.")

    initialized = chamfer_data.Initialize(SW_CONST_RADIUS_FILLET)
    if not initialized:
        model.ClearSelection2(True)
        raise RuntimeError("Simple Chamfer initialization returned False.")

    chamfer_data.DefaultRadius = distance_mm / 1000.0
    chamfer_data.ConicTypeForCrossSectionProfile = SW_FEATURE_FILLET_CONIC_RHO_ZERO_CHAMFER
    chamfer_data.OverflowType = SW_FILLET_OVERFLOW_DEFAULT

    chamfer_feature = feature_manager.CreateFeature(chamfer_data)
    model.ClearSelection2(True)
    if chamfer_feature is None:
        raise RuntimeError(
            f"SOLIDWORKS failed to create top perimeter Chamfer {distance_mm:g} mm."
        )
    if model.ForceRebuild3(False) is False:
        raise RuntimeError("SOLIDWORKS failed to rebuild the Chamfer feature.")

    print(
        f"Chamfer created: {distance_mm:g} mm on "
        f"{len(edges)} top perimeter edges."
    )
    return chamfer_feature


def apply_vertical_edge_fillet(
    model: Any,
    radius_mm: float,
    extrusion_depth_mm: float,
) -> Any:
    """Apply a constant-radius fillet to the four vertical outer box edges."""
    radius_mm = float(radius_mm)
    extrusion_depth_mm = float(extrusion_depth_mm)
    if radius_mm <= 0:
        raise ValueError("Fillet radius must be greater than zero.")
    if extrusion_depth_mm <= 0:
        raise ValueError("Extrusion depth must be greater than zero.")

    edges = get_box_vertical_edges(model, extrusion_depth_mm)
    _select_edges(model, edges, "vertical-corner Fillet")

    feature_manager = model.FeatureManager
    fillet_data = feature_manager.CreateDefinition(SW_FM_FILLET)
    if fillet_data is None:
        model.ClearSelection2(True)
        raise RuntimeError("FeatureManager.CreateDefinition(swFmFillet) returned None.")

    initialized = fillet_data.Initialize(SW_CONST_RADIUS_FILLET)
    if not initialized:
        model.ClearSelection2(True)
        raise RuntimeError("ISimpleFilletFeatureData2.Initialize returned False.")

    fillet_data.DefaultRadius = radius_mm / 1000.0
    fillet_data.ConicTypeForCrossSectionProfile = SW_FEATURE_FILLET_CIRCULAR

    fillet_feature = feature_manager.CreateFeature(fillet_data)
    model.ClearSelection2(True)
    if fillet_feature is None:
        raise RuntimeError(
            f"SOLIDWORKS failed to create the constant-radius Fillet R{radius_mm:g}."
        )
    if model.ForceRebuild3(False) is False:
        raise RuntimeError("SOLIDWORKS failed to rebuild the Fillet feature.")

    print(
        f"Fillet created: R{radius_mm:g} mm on "
        f"{len(edges)} vertical outer edges."
    )
    return fillet_feature


def compute_four_corner_hole_centers_mm(
    length_mm: float,
    width_mm: float,
    diameter_mm: float,
    edge_offset_mm: float,
    edge_clearance_mm: float = 0.0,
) -> list[tuple[float, float]]:
    """Return four hole centers measured from the two adjacent footprint edges."""
    length = float(length_mm)
    width = float(width_mm)
    diameter = float(diameter_mm)
    offset = float(edge_offset_mm)
    clearance = float(edge_clearance_mm)
    if min(length, width, diameter, offset) <= 0 or clearance < 0:
        raise ValueError("Hole dimensions and offset must be positive.")
    required_offset = diameter / 2.0 + clearance
    if offset <= required_offset:
        raise ValueError(
            f"Hole center offset must exceed {required_offset:g} mm "
            "to clear the hole radius and nearby edge features."
        )
    if length - 2.0 * offset <= diameter or width - 2.0 * offset <= diameter:
        raise ValueError(
            "Four corner holes do not fit: increase the part footprint "
            "or reduce the edge offset/hole diameter."
        )
    return [
        (offset, offset),
        (length - offset, offset),
        (length - offset, width - offset),
        (offset, width - offset),
    ]


def apply_four_corner_through_holes(
    model: Any,
    length_mm: float,
    width_mm: float,
    height_mm: float,
    diameter_mm: float,
    edge_offset_mm: float,
    edge_clearance_mm: float = 0.0,
) -> Any:
    """Cut four through-holes from the top face using one circular sketch."""
    diameter_mm = float(diameter_mm)
    height_mm = float(height_mm)
    if diameter_mm <= 0 or height_mm <= 0:
        raise ValueError("Hole diameter and part height must be greater than zero.")

    centers = compute_four_corner_hole_centers_mm(
        length_mm, width_mm, diameter_mm, edge_offset_mm, edge_clearance_mm
    )

    import pythoncom
    import win32com.client

    model.ClearSelection2(True)
    null_callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    selected_face = model.Extension.SelectByID2(
        "",
        "FACE",
        float(length_mm) / 2000.0,
        float(width_mm) / 2000.0,
        height_mm / 1000.0,
        False,
        0,
        null_callout,
        0,
    )
    if not selected_face:
        model.ClearSelection2(True)
        raise RuntimeError(
            "Could not select the top planar face at the center of the box for the hole sketch."
        )

    model.SketchManager.InsertSketch(True)
    circle_segments = []
    radius_m = diameter_mm / 2000.0
    for x_mm, y_mm in centers:
        segment = model.SketchManager.CreateCircleByRadius(
            x_mm / 1000.0,
            y_mm / 1000.0,
            0.0,
            radius_m,
        )
        if segment is None:
            model.SketchManager.InsertSketch(True)
            model.ClearSelection2(True)
            raise RuntimeError("SOLIDWORKS failed to create one of the hole circles.")
        circle_segments.append(segment)

    model.SketchManager.InsertSketch(True)
    model.ClearSelection2(True)

    hole_sketch = model.FeatureByName("Sketch2")
    if hole_sketch is None:
        raise RuntimeError("Hole sketch Sketch2 was not found in the FeatureManager tree.")
    if not hole_sketch.Select2(False, 0):
        raise RuntimeError("Could not select the hole sketch for Cut-Extrude.")

    cut_feature = model.FeatureManager.FeatureCut4(
        True,                       # Sd: single-ended cut
        False,                      # Flip
        False,                      # Dir: default direction, into the solid from top face
        SW_END_COND_THROUGH_ALL,    # T1: Through All
        0,                          # T2: unused for single-ended cut
        0.0,                        # D1: unused for Through All
        0.0,                        # D2
        False, False,               # Dchk1, Dchk2
        False, False,               # Ddir1, Ddir2
        0.0, 0.0,                   # Dang1, Dang2
        False, False,               # OffsetReverse1, OffsetReverse2
        False, False,               # TranslateSurface1, TranslateSurface2
        False,                      # NormalCut
        False,                      # UseFeatScope
        True,                       # UseAutoSelect
        False, False, False,        # AssemblyFeatureScope, AutoSelectComponents, PropagateFeatureToParts
        0,                          # T0: start condition
        0.0,                        # StartOffset
        False,                      # FlipStartOffset
        False,                      # OptimizeGeometry
    )
    model.ClearSelection2(True)
    if cut_feature is None:
        raise RuntimeError(
            "SOLIDWORKS failed to create the Through All Cut-Extrude for the four holes."
        )
    if model.ForceRebuild3(False) is False:
        raise RuntimeError("SOLIDWORKS failed to rebuild the hole Cut-Extrude feature.")

    print(
        f"Through-holes created: {len(centers)} x diameter {diameter_mm:g} mm, "
        f"edge offset {edge_offset_mm:g} mm."
    )
    return cut_feature
