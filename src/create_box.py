"""
Create a 100 x 60 x 30 mm rectangular solid in SOLIDWORKS 2026
using the SOLIDWORKS COM API.

Tested workflow:
- Python 3.14 64-bit
- pywin32
- SOLIDWORKS 2026 (Type Library 22.0)
"""

import os
import traceback

import pythoncom
import win32com.client


# ======================================
# 1. DESIGN PARAMETERS (mm)
# ======================================

LENGTH = 100.0
WIDTH = 60.0
HEIGHT = 30.0


def mm_to_m(value: float) -> float:
    """Convert millimetres to metres for SOLIDWORKS API calls."""
    return float(value) / 1000.0


# ======================================
# 2. OUTPUT LOCATION
# ======================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PART_PATH = os.path.join(OUTPUT_DIR, "My_First_Part.SLDPRT")


# ======================================
# 3. CREATE THE PART
# ======================================

def create_box() -> None:
    pythoncom.CoInitialize()

    try:
        # 4. Connect to SOLIDWORKS
        print("Connecting to SOLIDWORKS...")

        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = True

        print("Connected to SOLIDWORKS.")

        # 5. Get the default Part template and create a new Part
        print("Getting default Part template...")

        # 1 = swDocPART
        default_template = sw.GetDocumentTemplate(
            1, "", 0, 0.0, 0.0
        )

        print("Default template:", default_template)

        if not default_template:
            raise RuntimeError("Could not find the default Part template.")

        if not os.path.isfile(default_template):
            raise FileNotFoundError(
                f"Part template does not exist: {default_template}"
            )

        print("Creating Part...")
        model = sw.NewDocument(default_template, 0, 0.0, 0.0)

        if model is None:
            raise RuntimeError("NewDocument returned None.")

        print("Part created.")

        # 6. Select Front Plane
        print("Selecting Front Plane...")

        plane = model.FeatureByName("Front Plane")
        if plane is None:
            raise RuntimeError(
                "Front Plane was not found. Check the template's plane name "
                "or the SOLIDWORKS display language."
            )

        if not plane.Select2(False, 0):
            raise RuntimeError("Could not select Front Plane.")

        print("Front Plane selected.")

        # 7. Start a sketch
        print("Starting sketch...")
        model.SketchManager.InsertSketch(True)

        # 8. Draw the rectangle
        print("Drawing rectangle...")

        model.SketchManager.CreateCornerRectangle(
            0.0,
            0.0,
            0.0,
            mm_to_m(LENGTH),
            mm_to_m(WIDTH),
            0.0,
        )

        print("Rectangle sketch created.")

        # Exit sketch mode and clear selection
        model.SketchManager.InsertSketch(True)
        model.ClearSelection2(True)

        # 9. Select Sketch1
        print("Selecting Sketch1...")

        sketch = model.FeatureByName("Sketch1")
        if sketch is None:
            raise RuntimeError("Sketch1 was not found.")

        if not sketch.Select2(False, 0):
            raise RuntimeError("Could not select Sketch1.")

        print("Sketch1 selected.")

        # 10. Extrude
        print("Extruding...")

        depth = mm_to_m(HEIGHT)

        feature = model.FeatureManager.FeatureExtrusion2(
            True,       # Sd: single direction
            False,      # Flip
            False,      # Dir
            0,          # T1: Blind
            0,          # T2
            depth,      # D1: depth 1 (m)
            depth,      # D2: depth 2 (m)
            False,      # Dchk1
            False,      # Dchk2
            False,      # Ddir1
            False,      # Ddir2
            0.0,        # Dang1
            0.0,        # Dang2
            False,      # OffsetReverse1
            False,      # OffsetReverse2
            False,      # TranslateSurface1
            False,      # TranslateSurface2
            True,       # Merge
            False,      # UseFeatScope
            True,       # UseAutoSelect
            0,          # T0: start condition
            0.0,        # StartOffset
            False,      # FlipStartOffset
        )

        if feature is None:
            raise RuntimeError("FeatureExtrusion2 returned None.")

        print("Extrude successful.")

        # 11. Display the model
        model.ClearSelection2(True)
        model.ShowNamedView2("*Trimetric", 8)
        model.ViewZoomtofit2()

        # 12. Rebuild and save
        print("Rebuilding model...")

        rebuild_result = model.ForceRebuild3(False)
        print("Rebuild result:", rebuild_result)

        print("Saving file...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        save_result = model.SaveAs3(PART_PATH, 0, 1)
        print("Save result:", save_result)
        print("File path:", PART_PATH)

        if not save_result:
            try:
                print("Save error code:", model.GetSaveError())
                print("Save warning code:", model.GetSaveWarning())
            except Exception as error:
                print("Could not retrieve save diagnostics:", repr(error))

            raise RuntimeError("SOLIDWORKS failed to save the Part.")

        if not os.path.isfile(PART_PATH):
            raise FileNotFoundError(
                "SaveAs3 reported success, but the output file was not found."
            )

        # 13. Completion summary
        print("\n================================")
        print("PART CREATED SUCCESSFULLY")
        print(f"Length: {LENGTH} mm")
        print(f"Width:  {WIDTH} mm")
        print(f"Height: {HEIGHT} mm")
        print("Saved:", PART_PATH)
        print("================================")

    except Exception:
        print("\nDETAILED ERROR:")
        traceback.print_exc()

    finally:
        pythoncom.CoUninitialize()


# ======================================
# 14. RUN
# ======================================

if __name__ == "__main__":
    create_box()
