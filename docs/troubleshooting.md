# Troubleshooting – SOLIDWORKS COM

Baseline environment: Windows + SOLIDWORKS 2026 + Python 3.14 64-bit + pywin32.

## MakePy / COM wrapper

    python -m win32com.client.makepy

Select SOLIDWORKS 2026 Type Library (22.0). Generated interface wrappers are important for writable feature-data properties; the project early-binds IWizardHoleFeatureData2 rather than relying on a dynamic <unknown> dispatch object.

## Hole Wizard: Property can not be set (ThreadDepth, ThreadEndCondition)

FeatureManager.CreateDefinition(swFmHoleWzd) may return a late-bound pywin32 CDispatch whose displayed name is <unknown>. Its dynamic wrapper may not have property-put metadata, so code such as:

    hole_data.ThreadDepth = height_m

can fail in Python with:

    AttributeError: Property '<unknown>.ThreadDepth' can not be set.

This does not mean that ThreadDepth is absent from the SOLIDWORKS API. SOLIDWORKS documents it as a read/write property on IWizardHoleFeatureData2.

The project fix is to bind the raw dispatch to the generated MakePy interface before calling InitializeHole or setting its properties:

    hole_data = feature_manager.CreateDefinition(SW_FM_HOLE_WIZARD)
    hole_data = _early_bind_solidworks_interface(
        hole_data,
        "IWizardHoleFeatureData2",
    )
    hole_data.InitializeHole(...)
    hole_data.ThreadDepth = height_m
    hole_data.ThreadEndCondition = SW_WZD_THREAD_END_THROUGH_ALL

The helper does not call GetTypeInfo() on IFeatureManager or on the Hole Wizard definition. Some SOLIDWORKS proxies return DISP_E_BADINDEX for that call. Instead, it enumerates registered type libraries with pywin32 selecttlb.EnumTlbs(), filters the stable sldworks.tlb LIBID {83A33D31-27C5-11CE-BFD4-00400513BB57}, resolves the actual version from the registered TLB file, loads the MakePy module with gencache.EnsureModule(), resolves IWizardHoleFeatureData2 through NamesToIIDMap, then instantiates the generated interface class with the raw IDispatch. The generated wrapper performs QueryInterface and exposes the interface property setters.

The CosmeticThreadType property is not set by this code. Although some language-specific signatures show a setter, SOLIDWORKS API Help explicitly states that Set is not implemented for this property in the referenced API versions. Its display behaviour follows the installed Hole Wizard/template defaults. Do not add a Python assignment to this property.

If early binding fails:
1. Confirm that the installed SOLIDWORKS 2026 type library is registered in Windows.
2. Run python -m win32com.client.makepy and select SOLIDWORKS 2026 Type Library.
3. Confirm that MakePy completes without an error.
4. Pull the latest feature/natural-language-cad branch and retry.

The code reads the actual major/minor version from the registered sldworks.tlb file; do not hardcode the UI's displayed version string as a Python integer.

Do not work around this exception by deleting all thread settings: ThreadDepth and ThreadEndCondition still need to be configured for a Through All tapped hole.

## Zero-argument COM members and Member not found

Do not add parentheses to a late-bound COM member that has already been invoked on attribute access. The helper _call_member avoids using callable() for COM dispatch objects.

## Chamfer and Fillet

Chamfer selects four top-perimeter edges and is applied before vertical-corner Fillet. Fillet selects the four vertical outer edges. The constant-radius simple Fillet has been confirmed on the user's SOLIDWORKS session; new Chamfer variants still need to be exercised on each target template.

## Ordinary through-holes

The top face is selected by a model-space point. One sketch contains all circles at the requested XY centers, then FeatureCut4 is called with swEndCondThroughAll = 1. User-facing dimensions are mm and are converted to metres.

The XY origin is the lower-left corner of the top face in the base sketch coordinate system. For two-hole pitch layouts, centers are symmetric around the face center; X is the default pattern direction, Y is selected with wording such as "theo chieu rong".

## ISO M3/M4 tapped Hole Wizard

The implementation uses the feature-data workflow:
- CreateDefinition(swFmHoleWzd)
- Early-bind to IWizardHoleFeatureData2
- InitializeHole(swWzdTap, swStandardISO, swStandardISOTappedHole, "M3"/"M4", swEndCondThroughAll)
- Set ThreadDepth and ThreadEndCondition
- Select the top-face placement point with SelectByRay
- Call CreateFeature

The ISO M3/M4 coarse sizes use the SOLIDWORKS Hole Wizard table. The tap-drill diameter is selected from that standard. Cosmetic-thread callout display follows the Hole Wizard/template default; the automation does not attempt to assign the read-only CosmeticThreadType property.

If Hole Wizard returns None after this binding fix, inspect the selected-face ray and confirm the installed SOLIDWORKS ISO Hole Wizard database contains the requested size. Capture the full traceback and the feature-data property values.

## SaveAs3

SaveAs3 belongs to model.Extension. Optional COM interface arguments are passed as explicit null VT_DISPATCH variants; the last two by-reference integer variants receive error and warning bitmasks.

## General diagnostics

After each feature, check the returned feature is not None, rebuild the model, and verify the output file exists. Preserve the last working commit and change one operation at a time. Chamfer, coordinate hole patterns and tapped Hole Wizard calls require real SOLIDWORKS 2026 verification.
