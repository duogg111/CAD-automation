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

## 3. Entity selection

For stable plane/sketch selection, use feature objects:

    plane = model.FeatureByName("Front Plane")
    plane.Select2(False, 0)

For edge selection, IEntity.Select4 requires a real ISelectData object. Do not pass Python None:

    selection_data = model.SelectionManager.CreateSelectData()
    selection_data.Mark = 1
    edge.Select4(False, selection_data)

Selection mark 1 is used for edge selections defining a simple Fillet.

## 4. Creating a constant-radius Fillet

Use:

    fillet_data = model.FeatureManager.CreateDefinition(constants.swFmFillet)
    fillet_data.Initialize(constants.swConstRadiusFillet)
    fillet_data.DefaultRadius = radius_mm / 1000.0
    fillet_data.ConicTypeForCrossSectionProfile = constants.swFeatureFilletCircular
    fillet_feature = model.FeatureManager.CreateFeature(fillet_data)

For current API guidance, see the SOLIDWORKS ISimpleFilletFeatureData2 and IFeatureManager::CreateFeature documentation. FeatureFillet3 is obsolete for constant-radius fillets.

## 5. SaveAs3

SaveAs3 belongs to model.Extension and takes seven arguments. The optional COM interface arguments are passed as explicit null VT_DISPATCH variants in this project to avoid the pywin32 late-binding type mismatch previously observed. The last two by-reference integer variants receive error and warning bitmasks.

## 6. Rebuild and diagnostics

    rebuild_result = model.ForceRebuild3(False)

After a feature is created, check the returned feature is not None, rebuild the model, then save and verify the output file exists.

## 7. General rule

Change one operation at a time, preserve the last working commit, print the full traceback, and record SOLIDWORKS/Python/pywin32 versions for any COM error.
