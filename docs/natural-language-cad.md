# Natural-language CAD

## Pipeline

1. User enters a Vietnamese description.
2. The parser validates the rectangular-prism dimensions and feature parameters.
3. The program displays the planned feature targets, hole centers, defaults and warnings.
4. The user confirms.
5. SOLIDWORKS creates the base solid, optional top Chamfer, vertical Fillet, and requested ordinary/tapped holes.
6. The model is rebuilt and saved as SLDPRT.

## Supported descriptions

Base box:

    Tao hop dai 100 mm rong 60 mm cao 30 mm

Vertical corner Fillet:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5

Top perimeter Chamfer:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, vat canh 2 mm

Four through-holes, default edge offset 10 mm:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3

Single hole at explicit XY coordinates:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 1 lo D5 tai X=20 mm va Y=15 mm

Two holes centered 40 mm apart along X, symmetric about the face center:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 cach nhau 40 mm

Two holes along Y:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 cach nhau 30 mm theo chieu rong

Explicit multiple coordinates:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 tai (20, 15) va (80, 15)

ISO tapped holes:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, tao 2 lo ren M3 cach nhau 40 mm

    Tao hop dai 100 mm rong 60 mm cao 30 mm, tao 1 lo ren M4 tai (20, 20)

## Hole placement rules

### Coordinate system

- XY coordinates are measured in millimetres from the lower-left origin of the top face.
- X follows the length dimension; Y follows the width dimension.
- Coordinates are shown in the plan and validated before calling SOLIDWORKS.

### Automatic layouts

- Four corners: for four holes, the parser uses the specified edge offset or proposes 10 mm and displays a warning.
- Center-to-center X: for two holes, places them symmetrically about the face center, separated along X.
- Center-to-center Y: same but along Y when the description includes "theo chieu rong".
- Single center: one hole without coordinates is proposed at the center of the top face; this default is explicitly disclosed.
- Explicit points: one coordinate pair per hole, e.g. (20, 15) and (80, 15); coordinate notation X=20 mm va Y=15 mm is also accepted.
- Other counts/layouts remain preview-only until a deterministic placement rule is provided.

### Ordinary through-holes

Ordinary round holes are drawn together in one sketch on the top face and cut with FeatureCut4 using the Through All end condition. The planner checks hole diameter, edge clearance, Chamfer clearance, rounded-corner Fillet clearance and minimum center-to-center separation.

### ISO M3/M4 tapped holes

- The supported tap sizes are ISO metric coarse M3 and M4.
- M3: nominal thread diameter 3 mm, coarse pitch 0.5 mm, standard tap drill 2.5 mm.
- M4: nominal thread diameter 4 mm, coarse pitch 0.7 mm, standard tap drill 3.3 mm.
- The implementation creates a Hole Wizard feature data object with CreateDefinition(swFmHoleWzd), initializes it as a straight tap (swWzdTap) using the ISO standard and swStandardISOTappedHole, selects the top-face placement point with SelectByRay, then calls CreateFeature.
- An explicitly specified non-coarse pitch is rejected; only ISO coarse M3 and M4 are included in this milestone.
- Thread depth and thread end condition are set to the part's Through All depth. Cosmetic thread display with callout is requested.
- This is a Hole Wizard tapped-hole/cosmetic-thread feature, not a modeled helical solid thread. For true 3D thread geometry, a separate Thread feature workflow would be required.

## SOLIDWORKS API workflow

- Base: SketchManager.CreateCornerRectangle and FeatureExtrusion2.
- Chamfer: select top perimeter edges, create simple fillet/chamfer feature data, then CreateFeature.
- Fillet: select the four vertical edges and create a constant-radius simple fillet feature.
- Ordinary holes: select the top face, create circles in one sketch, then FeatureCut4 with swEndCondThroughAll.
- Tapped holes: IFeatureManager.CreateDefinition(swFmHoleWzd) → IWizardHoleFeatureData2.InitializeHole → set thread depth/end condition/cosmetic thread properties → select placement point with IModelDocExtension.SelectByRay → IFeatureManager.CreateFeature.

## Run and test

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D5 cach nhau 40 mm"

    python -m src.run_text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm, tao 2 lo ren M3 cach nhau 40 mm"

Run parser and geometry-plan tests without SOLIDWORKS:

    python -m unittest discover -s tests -v

GitHub Actions runs the unit tests on the feature branch. These tests do not start SOLIDWORKS.

## Verification boundary

The parser, XY placement calculations and existing Fillet workflow have test coverage and prior user-session confirmation where noted. The new coordinate/pitch Cut-Extrude variants and the ISO M3/M4 Hole Wizard COM workflow still require verification on the user's SOLIDWORKS 2026 installation.
