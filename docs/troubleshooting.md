# Troubleshooting – SOLIDWORKS COM

Baseline environment: Windows + SOLIDWORKS 2026 + Python 3.14 64-bit + pywin32.

## MakePy / COM wrapper

    python -m win32com.client.makepy

Select SOLIDWORKS 2026 Type Library (22.0). The Fillet/Chamfer/Hole Wizard enum values used by this project are defined locally to avoid depending on the global constants cache.

## Zero-argument COM members and Member not found

Do not add parentheses to a late-bound COM member that has already been invoked on attribute access. The helper _call_member avoids using callable() for COM dispatch objects.

## Chamfer and Fillet

Chamfer selects four top-perimeter edges and is applied before vertical-corner Fillet. Fillet selects the four vertical outer edges. The constant-radius simple Fillet has been confirmed on the user's SOLIDWORKS session; new Chamfer variants still need to be exercised on each target template.

## Ordinary through-holes

The top face is selected by a model-space point. One sketch contains all circles at the requested XY centers, then FeatureCut4 is called with swEndCondThroughAll = 1. User-facing dimensions are mm and are converted to metres.

The XY origin is the lower-left corner of the top face in the base sketch coordinate system. For two-hole pitch layouts, centers are symmetric around the face center; X is the default pattern direction, Y is selected with wording such as "theo chieu rong".

## ISO M3/M4 tapped Hole Wizard

The project uses the feature-data workflow, not IFeatureManager.HoleWizard5:

    hole_data = model.FeatureManager.CreateDefinition(SW_FM_HOLE_WIZARD)
    hole_data.InitializeHole(
        SW_WZD_TAP, SW_STANDARD_ISO, SW_STANDARD_ISO_TAPPED_HOLE,
        "M3", SW_END_COND_THROUGH_ALL
    )
    hole_data.ThreadDepth = height_mm / 1000.0
    hole_data.ThreadEndCondition = SW_END_THREAD_TYPE_THROUGH_ALL
    hole_data.CosmeticThreadType = SW_COSMETIC_THREAD_WITH_CALLOUT
    model.Extension.SelectByRay(...)
    feature = model.FeatureManager.CreateFeature(hole_data)

Enum values used:
- swFmHoleWzd = 25
- swWzdTap = 4
- swStandardISO = 8
- swStandardISOTappedHole = 147
- swEndCondThroughAll = 1
- swEndThreadTypeTHROUGH_ALL = 1
- swCosmeticThreadWithCallout = 1

M3/M4 coarse thread sizes are supplied as "M3" / "M4" to the ISO Hole Wizard database. The tap-drill diameter is read from the SOLIDWORKS standard table. Cosmetic thread annotation is not a true helical solid thread.

If Hole Wizard returns None, inspect the selected-face ray and confirm the installed SOLIDWORKS ISO Hole Wizard database contains the requested size. Capture the full traceback and the feature-data property values.

## SaveAs3

SaveAs3 belongs to model.Extension. Optional COM interface arguments are passed as explicit null VT_DISPATCH variants; the last two by-reference integer variants receive error and warning bitmasks.

## General diagnostics

After each feature, check the returned feature is not None, rebuild the model, and verify the output file exists. Preserve the last working commit and change one operation at a time. Chamfer, coordinate hole patterns and tapped Hole Wizard calls require real SOLIDWORKS 2026 verification.
