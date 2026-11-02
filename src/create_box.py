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

def create_box(
    length: float = LENGTH,
    width: float = WIDTH,
    height: float = HEIGHT,
    output_path: str = PART_PATH,
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

        plane = model.FeatureByName("Front Plane")
        if plane is None:
            raise RuntimeError(
                "Front Plane was not found. Check the template plane name "
                "or SOLIDWORKS display language."
            )
        if not plane.Select2(False, 0):
            raise RuntimeError("Could not select Front Plane.")

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

        model.ClearSelection2(True)
        model.ShowNamedView2("*Trimetric", 8)
        model.ViewZoomtofit2()

        rebuild_result = model.ForceRebuild3(False)
        if rebuild_result is False:
            raise RuntimeError("SOLIDWORKS reported that model rebuild failed.")

        save_result = model.SaveAs3(output_path, 0, 1)
        if not save_result:
            try:
                error_code = model.GetSaveError()
                warning_code = model.GetSaveWarning()
            except Exception:
                error_code, warning_code = "unavailable", "unavailable"
            raise RuntimeError(
                f"SOLIDWORKS failed to save. Error={error_code}; warning={warning_code}"
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
