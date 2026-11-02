# Troubleshooting – SOLIDWORKS COM

The baseline environment is Windows + SOLIDWORKS 2026 (Type Library 22.0) + Python 3.14 64-bit + pywin32.

## 1. MakePy / COM wrapper

Run:

    python -m win32com.client.makepy

Select SOLIDWORKS 2026 Type Library (22.0). The Fillet implementation reads enum values from win32com.client.constants, so this type library must be generated/registered.

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

SOLIDWORKS API Help confirms IEdge.GetStartVertex and IEdge.GetEndVertex are
valid IEdge members. This particular error was caused by the additional
zero-argument invocation in the Python helper, not by a missing API function.

## 4. Entity selection

For stable plane/sketch selection, use feature objects:

    plane = model.FeatureByName("Front Plane")
    plane.Select2(False, 0)

For edge selection, IEntity.Select4 requires a real ISelectData object. Do not pass Python None:

    selection_data = model.SelectionManager.CreateSelectData
    selection_data.Mark = 1
    edge.Select4(False, selection_data)

Selection mark 1 is used for edge selections defining a simple Fillet.

## 5. Creating a constant-radius Fillet

Use:

    fillet_data = model.FeatureManager.CreateDefinition(constants.swFmFillet)
    fillet_data.Initialize(constants.swConstRadiusFillet)
    fillet_data.DefaultRadius = radius_mm / 1000.0
    fillet_data.ConicTypeForCrossSectionProfile = constants.swFeatureFilletCircular
    fillet_feature = model.FeatureManager.CreateFeature(fillet_data)

For current API guidance, see the SOLIDWORKS ISimpleFilletFeatureData2 and IFeatureManager::CreateFeature documentation. FeatureFillet3 is obsolete for constant-radius fillets.

## 6. SaveAs3

SaveAs3 belongs to model.Extension and takes seven arguments. The optional COM interface arguments are passed as explicit null VT_DISPATCH variants in this project to avoid the pywin32 late-binding type mismatch previously observed. The last two by-reference integer variants receive error and warning bitmasks.

## 7. Rebuild and diagnostics

    rebuild_result = model.ForceRebuild3(False)

After a feature is created, check the returned feature is not None, rebuild the model, then save and verify the output file exists.

## 8. General rule

Change one operation at a time, preserve the last working commit, print the full traceback, and record SOLIDWORKS/Python/pywin32 versions for any COM error.
