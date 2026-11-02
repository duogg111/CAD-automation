# Natural-language CAD

## Pipeline

1. User enters a Vietnamese description.
2. The parser validates the rectangular-prism dimensions and feature parameters.
3. The program displays the planned feature targets and any placement defaults.
4. The user confirms.
5. SOLIDWORKS creates the base solid, optional top Chamfer, vertical Fillet, and optional four-hole Cut-Extrude.
6. The model is rebuilt and saved as SLDPRT.

## Example descriptions

Base box:

    Tao hop dai 100 mm rong 60 mm cao 30 mm

Vertical corner Fillet:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5

Top perimeter Chamfer:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm

Four through-holes, default edge offset 10 mm:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3

Four through-holes with explicit edge offset:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3 cach mep 8 mm

Combined example:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm, bo goc R5, khoet 4 lo D3 cach mep 10 mm

## Feature definitions

### Chamfer

- The phrase "vat canh 2 mm" is defined in this starter as a symmetric 2 mm chamfer on the four edges surrounding the top planar face.
- The Chamfer is created before vertical-corner Fillet.
- The code uses the SOLIDWORKS simple fillet/chamfer feature data object. For an offset-face chamfer, SOLIDWORKS documents swConstRadiusFillet initialization, swFeatureFilletConicRhoZeroChamfer profile, DefaultRadius as the symmetric offset distance, and OverflowType.
- Chamfer distance must be less than half the smallest of length, width, and height.

### Fillet

- "bo goc R5" means a constant-radius R5 fillet on the four vertical outside corner edges.
- It does not mean all twelve edges.
- Edge discovery accepts shortened vertical edges so that it still works after the top perimeter Chamfer.
- Radius must be positive and less than half the smaller footprint dimension.

### Four through-holes

- Automatic hole creation currently supports exactly four holes.
- The holes are placed symmetrically at (offset, offset), (length-offset, offset), (length-offset, width-offset), and (offset, width-offset) in the top sketch plane.
- Each hole is a Through All cut.
- If no edge offset is stated, the planner proposes 10 mm and displays a warning. The requested diameter, Chamfer and round-corner Fillet are checked against this offset. If 10 mm is insufficient, the planner rejects the request and asks for a larger explicit offset, for example "cach mep 12 mm".
- The center offset must clear the hole radius and the larger of the requested Fillet radius or Chamfer distance.
- Other counts/layouts are parsed but stay preview-only until positioning rules are implemented.

## SOLIDWORKS API workflow

- Base: SketchManager.CreateCornerRectangle and FeatureExtrusion2.
- Chamfer: select the four top perimeter edges with mark 1; create the simple fillet/chamfer feature data using CreateDefinition(swFmFillet), Initialize(swConstRadiusFillet), set the zero-rho chamfer profile, offset distance and overflow type; then CreateFeature.
- Fillet: select the four vertical edges and create a constant-radius simple fillet feature.
- Holes: select the top planar face by a point at its center, create four circles in one sketch using CreateCircleByRadius, then use FeatureCut4 with swEndCondThroughAll.

## Run and test

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm, bo goc R5, khoet 4 lo D3 cach mep 10 mm"

Run parser and geometry-plan tests without SOLIDWORKS:

    python -m unittest discover -s tests -v

## Verification boundary

The parser, edge classifiers and hole-layout calculations have unit tests. Fillet was confirmed on the user’s SOLIDWORKS session. The newly added Chamfer, top-face selection and four-hole Cut-Extrude COM operations still require verification in the user’s SOLIDWORKS 2026 session; they have not been executed from this development environment.
