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
# IWizardHoleFeatureData2.ThreadEndCondition uses swWzdHoleThreadEndCondition_e.
SW_WZD_THREAD_END_THROUGH_ALL = 1
# swFeatureNameID_e.swFmHoleWzd
SW_FM_HOLE_WIZARD = 25
# swWzdGeneralHoleTypes_e.swWzdTap
SW_WZD_TAP = 4
# swWzdHoleStandards_e.swStandardISO
SW_STANDARD_ISO = 8
# swWzdHoleStandardFastenerTypes_e.swStandardISOTappedHole
SW_STANDARD_ISO_TAPPED_HOLE = 147


SOLIDWORKS_TYPELIB_GUID = "{83A33D31-27C5-11CE-BFD4-00400513BB57}"


def _wrap_generated_interface(
    obj: Any,
    interface_name: str,
    gencache_module: Any,
    selecttlb_module: Any,
    pythoncom_module: Any,
) -> Any:
    """Wrap a raw IDispatch using the registered SldWorks type library.

    Do not ask the returned Hole Wizard definition or IFeatureManager for
    IDispatch.GetTypeInfo(): some SOLIDWORKS COM proxies reject that call with
    DISP_E_BADINDEX. Instead enumerate registered type libraries by the
    stable sldworks.tlb LIBID, resolve the actual version from its file when
    possible, load its MakePy module, and instantiate the generated interface
    class with the raw IDispatch (which performs QueryInterface).
    """
    ole_object = getattr(obj, "_oleobj_", None)
    if ole_object is None:
        raise TypeError("Expected a live SOLIDWORKS COM dispatch object.")

    specs = [
        spec
        for spec in selecttlb_module.EnumTlbs()
        if str(spec.clsid).strip("{}").upper()
        == SOLIDWORKS_TYPELIB_GUID.strip("{}").upper()
    ]
    if not specs:
        raise LookupError(
            "The registered SldWorks type library was not found. "
            f"Expected LIBID {SOLIDWORKS_TYPELIB_GUID}."
        )

    # Prefer the highest registered SldWorks typelib version. Resolve() reads
    # the actual version from the .tlb file and avoids interpreting registry
    # version strings (which pywin32 documents as inconsistently decimal/hex).
    resolved_specs = []
    errors: list[str] = []
    for spec in specs:
        try:
            if getattr(spec, "dll", None):
                spec.Resolve()
            else:
                major_text = str(spec.major)
                minor_text = str(spec.minor)
                typelib = pythoncom_module.LoadRegTypeLib(
                    spec.clsid,
                    int(major_text, 16),
                    int(minor_text, 16),
                    int(spec.lcid),
                )
                spec.FromTypelib(typelib)
            resolved_specs.append(spec)
        except Exception as exc:
            errors.append(f"{getattr(spec, 'ver_desc', spec.clsid)}: {exc}")

    resolved_specs.sort(
        key=lambda item: (int(item.major), int(item.minor)),
        reverse=True,
    )

    for spec in resolved_specs:
        try:
            library_module = gencache_module.EnsureModule(
                spec.clsid,
                int(spec.lcid),
                int(spec.major),
                int(spec.minor),
            )
            interface_iid = library_module.NamesToIIDMap.get(interface_name)
            if interface_iid is None:
                continue

            interface_module = gencache_module.GetModuleForCLSID(interface_iid)
            interface_class = getattr(interface_module, interface_name, None)
            if interface_class is None:
                errors.append(
                    f"Generated module has IID for {interface_name} but no wrapper class."
                )
                continue

            return interface_class(ole_object)
        except Exception as exc:
            errors.append(
                f"{getattr(spec, 'ver_desc', spec.clsid)} "
                f"({spec.major}.{spec.minor}): {exc}"
            )

    detail = "; ".join(errors[-5:]) if errors else (
        f"{interface_name} was not found in any registered SldWorks typelib."
    )
    raise RuntimeError(
        f"Could not load the MakePy wrapper for {interface_name} from "
        f"{SOLIDWORKS_TYPELIB_GUID}. Details: {detail}"
    )


def _early_bind_solidworks_interface(
    obj: Any,
    interface_name: str,
) -> Any:
    """Bind a SOLIDWORKS dispatch to its generated MakePy interface wrapper."""
    from win32com.client import gencache, selecttlb
    import pythoncom

    try:
        return _wrap_generated_interface(
            obj,
            interface_name,
            gencache,
            selecttlb,
            pythoncom,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Could not early-bind {interface_name} from the registered "
            "SldWorks type library. Verify SOLIDWORKS 2026 is installed and "
            "registered, then run 'python -m win32com.client.makepy' and "
            "select the SOLIDWORKS 2026 Type Library."
        ) from exc



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
    fillet_radius_mm: float = 0.0,
    chamfer_distance_mm: float = 0.0,
) -> list[tuple[float, float]]:
    """Return four corner centers after checking hole, chamfer and round-corner clearance."""
    length = float(length_mm)
    width = float(width_mm)
    diameter = float(diameter_mm)
    offset = float(edge_offset_mm)
    fillet_radius = float(fillet_radius_mm)
    chamfer_distance = float(chamfer_distance_mm)
    if (
        min(length, width, diameter, offset) <= 0
        or fillet_radius < 0
        or chamfer_distance < 0
    ):
        raise ValueError("Hole dimensions and offset must be positive; feature clearances cannot be negative.")

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
        raise ValueError(
            f"Hole center offset must exceed {required_offset:g} mm "
            "to clear the hole, top Chamfer and rounded corner boundary."
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


def compute_hole_centers_mm(
    length_mm: float,
    width_mm: float,
    count: int,
    layout: str,
    edge_offset_mm: float | None = None,
    center_distance_mm: float | None = None,
    axis: str = "x",
    explicit_points: list[tuple[float, float]] | None = None,
    diameter_mm: float = 1.0,
    fillet_radius_mm: float = 0.0,
    chamfer_distance_mm: float = 0.0,
) -> list[tuple[float, float]]:
    """Resolve and validate hole center positions in the top-face XY coordinates."""
    length = float(length_mm)
    width = float(width_mm)
    diameter = float(diameter_mm)
    if min(length, width, diameter) <= 0 or int(count) <= 0:
        raise ValueError("Part dimensions, hole diameter and hole count must be positive.")

    if layout == "four_corners":
        if edge_offset_mm is None:
            raise ValueError("Four-corner layout requires an edge offset.")
        centers = compute_four_corner_hole_centers_mm(
            length, width, diameter, float(edge_offset_mm),
            fillet_radius_mm, chamfer_distance_mm,
        )
    elif layout == "center_to_center_x":
        if int(count) != 2 or center_distance_mm is None:
            raise ValueError("Center-to-center layout along X requires exactly two holes and a pitch.")
        pitch = float(center_distance_mm)
        if pitch <= diameter or pitch / 2.0 + diameter / 2.0 >= length / 2.0:
            raise ValueError("The X-axis hole pitch does not fit the part.")
        centers = [
            (length / 2.0 - pitch / 2.0, width / 2.0),
            (length / 2.0 + pitch / 2.0, width / 2.0),
        ]
    elif layout == "center_to_center_y":
        if int(count) != 2 or center_distance_mm is None:
            raise ValueError("Center-to-center layout along Y requires exactly two holes and a pitch.")
        pitch = float(center_distance_mm)
        if pitch <= diameter or pitch / 2.0 + diameter / 2.0 >= width / 2.0:
            raise ValueError("The Y-axis hole pitch does not fit the part.")
        centers = [
            (length / 2.0, width / 2.0 - pitch / 2.0),
            (length / 2.0, width / 2.0 + pitch / 2.0),
        ]
    elif layout == "explicit_points":
        if explicit_points is None or len(explicit_points) != int(count):
            raise ValueError("Explicit point layout requires one XY coordinate pair per hole.")
        centers = [(float(x), float(y)) for x, y in explicit_points]
    elif layout == "single_center":
        if int(count) != 1:
            raise ValueError("Single-center layout supports exactly one hole.")
        centers = [(length / 2.0, width / 2.0)]
    else:
        raise ValueError(f"Unsupported automatic hole layout: {layout}")

    hole_radius = diameter / 2.0
    safety_margin = 0.25
    minimum_center_spacing = diameter + safety_margin
    for index, (x, y) in enumerate(centers):
        for other_x, other_y in centers[index + 1:]:
            center_spacing = ((x - other_x) ** 2 + (y - other_y) ** 2) ** 0.5
            if center_spacing <= minimum_center_spacing:
                raise ValueError(
                    "Two holes overlap or are too close: center spacing "
                    f"{center_spacing:g} mm must exceed {minimum_center_spacing:g} mm."
                )

        if not (0.0 < x < length and 0.0 < y < width):
            raise ValueError(f"Hole center ({x:g}, {y:g}) is outside the top face.")
        edge_clearance = min(x, length - x, y, width - y)
        required_edge = float(chamfer_distance_mm) + hole_radius + safety_margin
        if edge_clearance <= required_edge:
            raise ValueError(
                f"Hole center ({x:g}, {y:g}) is too close to an edge/chamfer; "
                f"clearance must exceed {required_edge:g} mm."
            )
        fillet_radius = float(fillet_radius_mm)
        if fillet_radius:
            corner_centers = [
                (fillet_radius, fillet_radius),
                (length - fillet_radius, fillet_radius),
                (length - fillet_radius, width - fillet_radius),
                (fillet_radius, width - fillet_radius),
            ]
            min_corner_distance = min(
                ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                for cx, cy in corner_centers
            )
            if min_corner_distance <= fillet_radius + hole_radius + safety_margin:
                raise ValueError(
                    f"Hole center ({x:g}, {y:g}) is too close to a rounded Fillet corner."
                )

    return centers


def apply_iso_metric_tapped_holes(
    model: Any,
    centers_mm: list[tuple[float, float]],
    height_mm: float,
    size: str,
) -> list[Any]:
    """Create ISO M3/M4 tapped Hole Wizard features at explicitly selected points.

    The feature carries native Hole Wizard tapped-hole data. It does not
    create a true helical solid thread. CosmeticThreadType is read-only in
    this API, so its display follows the SOLIDWORKS standard/template default.
    """
    size = str(size).upper()
    if size not in {"M3", "M4"}:
        raise ValueError("Only ISO coarse metric M3 and M4 tapped holes are supported.")
    if not centers_mm:
        raise ValueError("At least one tapped-hole center is required.")
    height_mm = float(height_mm)
    if height_mm <= 0:
        raise ValueError("Part height must be positive.")

    feature_manager = model.FeatureManager
    created_features: list[Any] = []
    height_m = height_mm / 1000.0

    for index, (x_mm, y_mm) in enumerate(centers_mm, start=1):
        x_mm = float(x_mm)
        y_mm = float(y_mm)
        hole_data = feature_manager.CreateDefinition(SW_FM_HOLE_WIZARD)
        if hole_data is None:
            raise RuntimeError("FeatureManager.CreateDefinition(swFmHoleWzd) returned None.")

        # CreateDefinition can return a dynamic CDispatch (<unknown>).
        # Bind to the MakePy-generated IWizardHoleFeatureData2 wrapper before
        # using property setters; otherwise pywin32 cannot discover property puts.
        hole_data = _early_bind_solidworks_interface(
            hole_data,
            "IWizardHoleFeatureData2",
        )

        # ISO metric straight-tap Hole Wizard, M3/M4 coarse series, Through All.
        hole_data.InitializeHole(
            SW_WZD_TAP,
            SW_STANDARD_ISO,
            SW_STANDARD_ISO_TAPPED_HOLE,
            size,
            SW_END_COND_THROUGH_ALL,
        )
        # The tap-drill bore is Through All (InitializeHole above), and the
        # thread itself is also Through All. Do not assign ThreadDepth here:
        # SOLIDWORKS 2026 can raise RPC_E_SERVERFAULT for that redundant setter
        # when the thread end condition is Through All.
        hole_data.ThreadEndCondition = SW_WZD_THREAD_END_THROUGH_ALL
        # CosmeticThreadType is get-only in the installed SOLIDWORKS API;
        # assigning it is documented as not implemented. Leave display style
        # to the SOLIDWORKS Hole Wizard/template default.

        model.ClearSelection2(True)
        selected = model.Extension.SelectByRay(
            x_mm / 1000.0,
            y_mm / 1000.0,
            height_m + 0.005,
            0.0,
            0.0,
            -1.0,
            0.0005,
            2,
            False,
            0,
            0,
        )
        if not selected:
            model.ClearSelection2(True)
            raise RuntimeError(
                f"Could not select the top-face placement point for tapped hole "
                f"{index} at ({x_mm:g}, {y_mm:g}) mm."
            )

        feature = feature_manager.CreateFeature(hole_data)
        model.ClearSelection2(True)
        if feature is None:
            raise RuntimeError(
                f"SOLIDWORKS failed to create ISO {size} Hole Wizard feature "
                f"{index} at ({x_mm:g}, {y_mm:g}) mm."
            )
        if model.ForceRebuild3(False) is False:
            raise RuntimeError(f"SOLIDWORKS failed to rebuild tapped-hole feature {index}.")
        created_features.append(feature)

    print(
        f"ISO {size} tapped holes created: {len(created_features)}; "
        "thread end condition: Through All; tap-drill dimensions come from "
        "the SOLIDWORKS Hole Wizard standard."
    )
    print(
        "Cosmetic thread callout display follows SOLIDWORKS defaults; "
        "the API CosmeticThreadType setter is not implemented."
    )
    return created_features


def apply_four_corner_through_holes(
    model: Any,
    length_mm: float,
    width_mm: float,
    height_mm: float,
    diameter_mm: float,
    edge_offset_mm: float | None = None,
    fillet_radius_mm: float = 0.0,
    chamfer_distance_mm: float = 0.0,
    centers_mm: list[tuple[float, float]] | None = None,
) -> Any:
    """Cut positioned through-holes from the top face using one circular sketch."""
    diameter_mm = float(diameter_mm)
    height_mm = float(height_mm)
    if diameter_mm <= 0 or height_mm <= 0:
        raise ValueError("Hole diameter and part height must be greater than zero.")

    centers = centers_mm or compute_four_corner_hole_centers_mm(
        length_mm,
        width_mm,
        diameter_mm,
        float(edge_offset_mm) if edge_offset_mm is not None else 10.0,
        fillet_radius_mm,
        chamfer_distance_mm,
    )
    centers = [(float(x), float(y)) for x, y in centers]
    if not centers:
        raise ValueError("At least one hole center is required.")
    for x, y in centers:
        if not (0.0 < x < float(length_mm) and 0.0 < y < float(width_mm)):
            raise ValueError(f"Hole center ({x:g}, {y:g}) is outside the top face.")

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
        f"Through-holes created: {len(centers)} x diameter {diameter_mm:g} mm."
    )
    if edge_offset_mm is not None:
        print(f"Hole center edge offset: {float(edge_offset_mm):g} mm.")
    print("Hole centers (X, Y) in mm:", centers)
    return cut_feature
