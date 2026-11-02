# Natural-language CAD

## Pipeline

1. User enters a part description in Vietnamese.
2. Text is normalised and parsed into a validated CAD plan.
3. The user reviews the dimensions and requested features.
4. The program creates a rectangular base solid in SOLIDWORKS.
5. Requested vertical-corner Fillet is created as a separate feature.
6. The model is rebuilt and saved as SLDPRT.

## Supported descriptions

Base box:

    Tao hop dai 100 mm, rong 60 mm, cao 30 mm

Four outside vertical corners, constant radius:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5

Dimensions may also use a tuple:

    Tao hop 100 x 60 x 30 mm, bo goc R5

## Fillet behaviour

- bo goc R5 means a constant-radius R5 fillet on the four vertical outer edges of the rectangular prism.
- It does not mean all 12 box edges.
- The starter creates the rectangle on Front Plane and extrudes along global Z. Edge discovery checks endpoint coordinates and extrusion depth; it expects exactly four matching vertical edges.
- The radius must be positive and strictly less than half the smaller footprint dimension.
- Chamfer and holes are still preview-only.

## SOLIDWORKS API approach

The implementation uses the current simple fillet feature-data workflow:

1. Obtain the solid body's edges with IPartDoc::GetBodies2 and IBody2::GetEdges.
2. Identify the four vertical edges with IEdge::GetStartVertex, IEdge::GetEndVertex, and IVertex::GetPoint.
3. Select those edges using IEntity::Select4 and ISelectionMgr::CreateSelectData, with selection mark 1.
4. Create the definition using IFeatureManager::CreateDefinition(swFmFillet).
5. Initialize with swConstRadiusFillet, set the radius and circular profile, then call IFeatureManager::CreateFeature.
6. Rebuild and save the part.

FeatureFillet3 is not used because SOLIDWORKS documents it as obsolete for constant-radius fillets.

## Run

From the repository root:

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5"

Run tests without starting SOLIDWORKS:

    python -m unittest discover -s tests -v

## Current execution boundary

- Rectangular base solid: supported by the COM starter.
- Four-edge constant-radius Fillet: implemented; must be verified on the user's SOLIDWORKS installation.
- Chamfer and holes: parsed into the plan, preview-only.
- Missing, non-positive, or oversized dimensions/radii are rejected instead of guessed.
