"""SOLIDWORKS feature helpers for the rectangular-prism starter."""
from __future__ import annotations
from typing import Any

def _call_member(obj: Any, name: str, *args: Any) -> Any:
    """Call a pywin32 method whether exposed callable or auto-invoked (zero args)."""
    member = getattr(obj, name)
    if callable(member):
        return member(*args)
    if args:
        raise TypeError(f"COM member {name} is not callable but arguments were supplied.")
    return member

def _as_items(value: Any) -> list[Any]:
    """Convert a COM SAFEARRAY result to a Python list."""
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
    """Match a global-Z edge whose length equals the starter extrusion depth."""
    expected_depth_m = float(extrusion_depth_mm) / 1000.0
    dx = abs(end_point[0] - start_point[0])
    dy = abs(end_point[1] - start_point[1])
    dz = abs(end_point[2] - start_point[2])
    tol = max(float(tolerance_m), expected_depth_m * 1e-6)
    return dx <= tol and dy <= tol and abs(dz - expected_depth_m) <= tol

def _get_solid_bodies(model: Any) -> list[Any]:
    """Get solid bodies, explicitly casting to IPartDoc if needed by COM dispatch."""
    try:
        result = _call_member(model, "GetBodies2", 0, False)  # swSolidBody = 0
        return _as_items(result)
    except Exception as direct_error:
        import win32com.client
        last_error: Exception = direct_error
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

def get_box_vertical_edges(model: Any, extrusion_depth_mm: float) -> list[Any]:
    """Find the four vertical corner edges of the starter's single solid body."""
    bodies = _get_solid_bodies(model)
    if len(bodies) != 1:
        raise RuntimeError(
            "Expected exactly one solid body before Fillet, "
            f"but SOLIDWORKS returned {len(bodies)}."
        )
    body_edges = _as_items(_call_member(bodies[0], "GetEdges"))
    vertical_edges: list[Any] = []
    for edge in body_edges:
        start_vertex = _call_member(edge, "GetStartVertex")
        end_vertex = _call_member(edge, "GetEndVertex")
        if start_vertex is None or end_vertex is None:
            continue
        if is_vertical_extrusion_edge(
            _vertex_point(start_vertex),
            _vertex_point(end_vertex),
            extrusion_depth_mm,
        ):
            vertical_edges.append(edge)
    if len(vertical_edges) != 4:
        raise RuntimeError(
            "Could not identify the four vertical box edges for Fillet. "
            f"Expected 4, found {len(vertical_edges)}. "
            "Check the Part template plane/orientation and extrusion direction."
        )
    return vertical_edges

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
    model.ClearSelection2(True)
    selection_manager = model.SelectionManager
    selection_data = _call_member(selection_manager, "CreateSelectData")
    selection_data.Mark = 1

    for index, edge in enumerate(edges):
        selected = edge.Select4(index > 0, selection_data)
        if not selected:
            model.ClearSelection2(True)
            raise RuntimeError(
                f"SOLIDWORKS could not select vertical edge {index + 1}/4 for Fillet."
            )

    # These enum values are loaded by the SOLIDWORKS Type Library MakePy wrapper.
    import win32com.client
    constants = win32com.client.constants
    try:
        fillet_definition_id = int(constants.swFmFillet)
        constant_radius_type = int(constants.swConstRadiusFillet)
        circular_profile_type = int(constants.swFeatureFilletCircular)
    except Exception as exc:
        model.ClearSelection2(True)
        raise RuntimeError(
            "SOLIDWORKS API constants are unavailable. Run "
            "'python -m win32com.client.makepy' and select "
            "'SOLIDWORKS 2026 Type Library (22.0)'."
        ) from exc

    feature_manager = model.FeatureManager
    fillet_data = feature_manager.CreateDefinition(fillet_definition_id)
    if fillet_data is None:
        model.ClearSelection2(True)
        raise RuntimeError("FeatureManager.CreateDefinition(swFmFillet) returned None.")

    fillet_data.Initialize(constant_radius_type)
    fillet_data.DefaultRadius = radius_mm / 1000.0
    fillet_data.ConicTypeForCrossSectionProfile = circular_profile_type
    fillet_data.PropagateToTangentFaces = False

    fillet_feature = feature_manager.CreateFeature(fillet_data)
    model.ClearSelection2(True)
    if fillet_feature is None:
        raise RuntimeError(
            f"SOLIDWORKS failed to create the constant-radius Fillet R{radius_mm:g}."
        )
    rebuild_result = model.ForceRebuild3(False)
    if rebuild_result is False:
        raise RuntimeError("SOLIDWORKS failed to rebuild the Fillet feature.")

    print(
        f"Fillet created: R{radius_mm:g} mm on "
        f"{len(edges)} vertical outer edges."
    )
    return fillet_feature
