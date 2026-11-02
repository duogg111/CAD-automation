# Troubleshooting – SOLIDWORKS COM

Baseline environment: Windows + SOLIDWORKS 2026 + Python 3.14 64-bit + pywin32.

## MakePy / COM wrapper

    python -m win32com.client.makepy

Select SOLIDWORKS 2026 Type Library (22.0). The three Fillet/Chamfer enum values used by this project are defined locally so the code does not depend on the global constants cache.

## Zero-argument COM members and Member not found

Do not add parentheses to a late-bound COM member that has already been invoked on attribute access. The helper _call_member avoids using callable() for COM dispatch objects.

## Chamfer

The symmetric offset-face Chamfer uses the simple fillet/chamfer feature-data interface:
- CreateDefinition with swFmFillet = 1
- Initialize with swConstRadiusFillet = 0
- ConicTypeForCrossSectionProfile = swFeatureFilletConicRhoZeroChamfer = 3
- DefaultRadius is the symmetric offset distance in metres
- OverflowType = swFilletOverFlowType_Default = 0

The project selects the four top-perimeter edges with selection mark 1 and applies Chamfer before Fillet.

## Fillet

The project selects the four vertical outer edges with mark 1, initializes a constant-radius simple Fillet, sets the radius in metres and the circular profile, then creates the feature. This operation has been verified on the user's SOLIDWORKS 2026 session.

## Four-hole Cut-Extrude

The implementation selects the top planar face by a model-space point at the footprint center and top height, then starts one sketch on that face. Four circles are created using local sketch coordinates and radius in metres. FeatureCut4 uses swEndCondThroughAll = 1.

The default hole-center offset is 10 mm from each adjacent footprint edge. The planner checks clearance from the hole radius, the top chamfer and the rounded outer corner. If the default offset is too small, specify a larger value with wording such as "cach mep 12 mm".

If face selection fails, verify the default Part template and the model dimensions/orientation. If the Cut-Extrude fails, capture the full traceback and check whether the sketch is on the upper planar face and the circle centers lie inside the top face with enough clearance.

## SaveAs3

SaveAs3 belongs to model.Extension. Optional COM interface arguments are passed as explicit null VT_DISPATCH variants; the last two by-reference integer variants receive error and warning bitmasks.

## General diagnostics

After each feature, check the returned feature is not None, rebuild the model, and verify the output file exists. Preserve the last working commit and change one operation at a time.

The parser, edge-selection and hole-layout planning functions have unit tests. The Chamfer and hole COM calls remain pending verification in the user's SOLIDWORKS session.
