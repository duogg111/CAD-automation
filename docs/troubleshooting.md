# Troubleshooting – SOLIDWORKS COM

The baseline environment is Windows + SOLIDWORKS 2026 + Python 3.14 64-bit + pywin32.

## 1. MakePy / COM wrapper

Run this if pywin32 needs generated interface wrappers:

    python -m win32com.client.makepy

Select the SOLIDWORKS 2026 Type Library (22.0). MakePy can improve type information and interface casting. However, the Fillet helper does not require the global win32com.client.constants cache for its three enum values.

## 2. Part template

    template = sw.GetDocumentTemplate(1, "", 0, 0.0, 0.0)
    model = sw.NewDocument(template, 0, 0.0, 0.0)

In this workflow, 1 is swDocPART.

## 3. Zero-argument COM members and Member not found

SOLIDWORKS methods such as IBody2.GetEdges, IEdge.GetStartVertex,
IEdge.GetEndVertex, and IVertex.GetPoint take no arguments. With pywin32
late-bound IDispatch, these members can be invoked while retrieving the
attribute. Do not then call the returned value with parentheses.

Incorrect:

    start_vertex = edge.GetStartVertex()

Correct for late-bound COM:

    start_vertex = edge.GetStartVertex
    point = start_vertex.GetPoint

The helper _call_member therefore calls a member only when arguments are
provided, or when the object is an ordinary Python bound method. It does not
use callable() to identify COM methods because a pywin32 dispatch object can
report callable even when it is the returned COM object/value.

## 4. Entity selection

For stable plane/sketch selection, use feature objects:

    plane = model.FeatureByName("Front Plane")
    plane.Select2(False, 0)

For edge selection, IEntity.Select4 requires a real ISelectData object:

    selection_data = model.SelectionManager.CreateSelectData
    selection_data.Mark = 1
    edge.Select4(False, selection_data)

Selection mark 1 is used for edge selections defining a simple Fillet.

## 5. Creating a constant-radius Fillet

The feature-data workflow is:

    fillet_data = model.FeatureManager.CreateDefinition(SW_FM_FILLET)
    fillet_data.Initialize(SW_CONST_RADIUS_FILLET)
    fillet_data.DefaultRadius = radius_mm / 1000.0
    fillet_data.ConicTypeForCrossSectionProfile = SW_FEATURE_FILLET_CIRCULAR
    fillet_feature = model.FeatureManager.CreateFeature(fillet_data)

The project defines these documented SwConst enum values locally to avoid relying
on win32com.client.constants, which may not have imported the separate SwConst
type library into its global constants cache:

- SW_FM_FILLET = 1 (swFeatureNameID_e.swFmFillet)
- SW_CONST_RADIUS_FILLET = 0 (swSimpleFilletType_e.swConstRadiusFillet)
- SW_FEATURE_FILLET_CIRCULAR = 0 (swFeatureFilletProfileType_e.swFeatureFilletCircular)

The latter two values are listed in the SOLIDWORKS enum reference. The feature name
ID values are defined by the SwConst type library; in that enum, swFmChamfer = 0
and swFmFillet = 1.

## 6. SaveAs3

SaveAs3 belongs to model.Extension and takes seven arguments. The optional COM
interface arguments are passed as explicit null VT_DISPATCH variants to avoid
the pywin32 late-binding type mismatch previously observed. The last two
by-reference integer variants receive error and warning bitmasks.

## 7. Rebuild and diagnostics

    rebuild_result = model.ForceRebuild3(False)

After a feature is created, check the returned feature is not None, rebuild the
model, then save and verify the output file exists.

## 8. General rule

Change one operation at a time, preserve the last working commit, print the full
traceback, and record SOLIDWORKS/Python/pywin32 versions for any COM error.
