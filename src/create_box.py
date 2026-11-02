"""
Create a rectangular solid in SOLIDWORKS 2026 using the SOLIDWORKS COM API.
Tested baseline: Python 3.14 64-bit, pywin32, SOLIDWORKS 2026.
"""
import os
import traceback
import pythoncom
import win32com.client

LENGTH = 100.0
WIDTH = 60.0
HEIGHT = 30.0

def mm_to_m(value: float) -> float:
    """Convert millimetres to metres for SOLIDWORKS API calls."""
    return float(value) / 1000.0

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
PART_PATH = os.path.join(OUTPUT_DIR, "My_First_Part.SLDPRT")

try:
    from src.solidworks_features import (
        apply_vertical_edge_fillet,
        apply_top_perimeter_chamfer,
        apply_four_corner_through_holes,
        apply_iso_metric_tapped_holes,
    )
except ModuleNotFoundError:
    from solidworks_features import (
        apply_vertical_edge_fillet,
        apply_top_perimeter_chamfer,
        apply_four_corner_through_holes,
        apply_iso_metric_tapped_holes,
    )


def create_box(
    length: float = LENGTH,
    width: float = WIDTH,
    height: float = HEIGHT,
    output_path: str = PART_PATH,
    fillet_radius_mm: float | None = None,
    chamfer_distance_mm: float | None = None,
    hole_count: int = 0,
    hole_diameter_mm: float | None = None,
    hole_edge_offset_mm: float | None = None,
    hole_centers_mm: list[tuple[float, float]] | None = None,
    tapped_hole_size: str | None = None,
) -> str:
    """Create and save a rectangular prism; dimensions are in millimetres."""
    dimensions = {"length": float(length), "width": float(width), "height": float(height)}
    for name, value in dimensions.items():
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero; received {value}.")
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path) or os.getcwd(), exist_ok=True)

    pythoncom.CoInitialize()
    try:
        print("Connecting to SOLIDWORKS...")
        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = True

        print("Getting default Part template...")
        default_template = sw.GetDocumentTemplate(1, "", 0, 0.0, 0.0)
        if not default_template:
            raise RuntimeError("Could not find the default Part template.")
        if not os.path.isfile(default_template):
            raise FileNotFoundError(f"Part template does not exist: {default_template}")

        model = sw.NewDocument(default_template, 0, 0.0, 0.0)
        if model is None:
            raise RuntimeError("NewDocument returned None.")

        # Clear any template/default selection before selecting the sketch plane.
        model.ClearSelection2(True)
        plane = model.FeatureByName("Front Plane")
        if plane is None:
            raise RuntimeError(
                "Front Plane was not found by its default English name. "
                "Check the Part template and SOLIDWORKS display language."
            )

        # Some SOLIDWORKS templates expose the plane Feature object but reject
        # IFeature.Select2. Try alternate selection methods before failing.
        selected_plane = False
        selection_errors = []
        try:
            selected_plane = bool(plane.Select2(False, 0))
        except Exception as exc:
            selection_errors.append(f"Feature.Select2: {exc}")

        if not selected_plane:
            model.ClearSelection2(True)
            try:
                selected_plane = bool(plane.Select(False))
            except Exception as exc:
                selection_errors.append(f"Feature.Select: {exc}")

        if not selected_plane:
            model.ClearSelection2(True)
            try:
                plane_name = str(plane.Name)
                null_callout = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
                selected_plane = bool(
                    model.Extension.SelectByID2(
                        plane_name, "PLANE", 0.0, 0.0, 0.0,
                        False, 0, null_callout, 0,
                    )
                )
            except Exception as exc:
                selection_errors.append(f"Extension.SelectByID2: {exc}")

        if not selected_plane:
            try:
                plane_name = str(plane.Name)
            except Exception:
                plane_name = "<unavailable>"
            try:
                plane_type = str(plane.GetTypeName2())
            except Exception:
                plane_type = "<unavailable>"
            raise RuntimeError(
                "Could not select the sketch plane. "
                f"Feature name={plane_name!r}, type={plane_type!r}. "
                "Check that the default Part template has an unsuppressed Front Plane. "
                + " | ".join(selection_errors)
            )

        model.SketchManager.InsertSketch(True)
        sketch_segment = model.SketchManager.CreateCornerRectangle(
            0.0, 0.0, 0.0,
            mm_to_m(dimensions["length"]),
            mm_to_m(dimensions["width"]),
            0.0,
        )
        if sketch_segment is None:
            raise RuntimeError("CreateCornerRectangle returned None.")

        model.SketchManager.InsertSketch(True)
        model.ClearSelection2(True)

        sketch = model.FeatureByName("Sketch1")
        if sketch is None:
            raise RuntimeError("Sketch1 was not found.")
        if not sketch.Select2(False, 0):
            raise RuntimeError("Could not select Sketch1.")

        depth = mm_to_m(dimensions["height"])
        feature = model.FeatureManager.FeatureExtrusion2(
            True, False, False, 0, 0, depth, depth,
            False, False, False, False, 0.0, 0.0,
            False, False, False, False, True, False, True, 0, 0.0, False,
        )
        if feature is None:
            raise RuntimeError("FeatureExtrusion2 returned None.")

        # Apply top-edge Chamfer first. This preserves four shortened vertical
        # corner edges for the subsequent Fillet operation.
        if chamfer_distance_mm is not None:
            max_chamfer = min(
                dimensions["length"], dimensions["width"], dimensions["height"]
            )
            if float(chamfer_distance_mm) <= 0 or float(chamfer_distance_mm) >= max_chamfer / 2.0:
                raise ValueError(
                    f"Chamfer distance must be > 0 and < {max_chamfer / 2.0:g} mm."
                )
            apply_top_perimeter_chamfer(
                model,
                distance_mm=float(chamfer_distance_mm),
                extrusion_height_mm=dimensions["height"],
            )

        if fillet_radius_mm is not None:
            max_radius = min(dimensions["length"], dimensions["width"]) / 2.0
            if float(fillet_radius_mm) <= 0 or float(fillet_radius_mm) >= max_radius:
                raise ValueError(
                    f"Fillet radius must be > 0 and < {max_radius:g} mm for this box."
                )
            apply_vertical_edge_fillet(
                model,
                radius_mm=float(fillet_radius_mm),
                extrusion_depth_mm=dimensions["height"],
            )

        if hole_count:
            if hole_centers_mm is None or len(hole_centers_mm) != int(hole_count):
                raise ValueError(
                    "Hole creation requires one validated XY center coordinate per hole."
                )
            if tapped_hole_size is not None:
                apply_iso_metric_tapped_holes(
                    model,
                    centers_mm=hole_centers_mm,
                    height_mm=dimensions["height"],
                    size=tapped_hole_size,
                )
            else:
                if hole_diameter_mm is None:
                    raise ValueError("A diameter is required for ordinary through-holes.")
                apply_four_corner_through_holes(
                    model,
                    length_mm=dimensions["length"],
                    width_mm=dimensions["width"],
                    height_mm=dimensions["height"],
                    diameter_mm=float(hole_diameter_mm),
                    edge_offset_mm=hole_edge_offset_mm,
                    fillet_radius_mm=float(fillet_radius_mm or 0.0),
                    chamfer_distance_mm=float(chamfer_distance_mm or 0.0),
                    centers_mm=hole_centers_mm,
                )

        model.ClearSelection2(True)
        model.ShowNamedView2("*Trimetric", 8)
        model.ViewZoomtofit2()

        rebuild_result = model.ForceRebuild3(False)
        if rebuild_result is False:
            raise RuntimeError("SOLIDWORKS reported that model rebuild failed.")

        # SaveAs3 belongs to IModelDocExtension, not IModelDoc2.
        # The final two arguments are COM [out] LONG values.
        errors = win32com.client.VARIANT(
            pythoncom.VT_BYREF | pythoncom.VT_I4, 0
        )
        warnings = win32com.client.VARIANT(
            pythoncom.VT_BYREF | pythoncom.VT_I4, 0
        )
        # These are optional COM interface parameters. Under pywin32
        # late binding, Python None is not always marshalled as VBA Nothing.
        # Use an explicit VT_DISPATCH null pointer for both object arguments.
        null_export_data = win32com.client.VARIANT(
            pythoncom.VT_DISPATCH, None
        )
        null_advanced_options = win32com.client.VARIANT(
            pythoncom.VT_DISPATCH, None
        )

        extension = model.Extension
        save_result = extension.SaveAs3(
            output_path,
            0,                      # swSaveAsCurrentVersion
            1,                      # swSaveAsOptions_Silent
            null_export_data,       # ExportData: COM Nothing
            null_advanced_options,  # AdvancedSaveAsOptions: COM Nothing
            errors,
            warnings,
        )
        print("SaveAs3 result:", save_result)
        print("Save error bitmask:", errors.value)
        print("Save warning bitmask:", warnings.value)
        if not save_result:
            raise RuntimeError(
                "SOLIDWORKS failed to save. "
                f"Error bitmask={errors.value}; warning bitmask={warnings.value}"
            )
        if not os.path.isfile(output_path):
            raise FileNotFoundError(
                "SaveAs3 reported success, but the output file was not found."
            )

        print("\nPART CREATED SUCCESSFULLY")
        print(f"Length: {dimensions['length']} mm")
        print(f"Width:  {dimensions['width']} mm")
        print(f"Height: {dimensions['height']} mm")
        print("Saved:", output_path)
        return output_path

    except Exception:
        print("\nDETAILED ERROR:")
        traceback.print_exc()
        raise
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    create_box()
