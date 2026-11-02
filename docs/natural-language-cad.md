# Natural-language CAD – Milestone 1

## Pipeline

1. User enters a part description.
2. Text is normalised (case, accents and whitespace).
3. The parser extracts a rectangular-prism shape and dimensions.
4. Optional feature requests are extracted into a structured plan.
5. The plan is printed as JSON for review.
6. No SOLIDWORKS geometry is changed by this parser.

## Supported input examples

Labelled dimensions:

    Tao hop dai 100 mm, rong 60 mm, cao 30 mm

Dimension tuple:

    Tao mot cai hop 100 x 60 x 30 mm

Optional feature extraction:

    Tao hop dai 100 mm rong 60 mm cao 30 mm, bo goc R5, khoet 4 lo duong kinh 3 mm

## Run

From the repository root:

    python -m src.text_to_cad "Tao hop dai 100 mm rong 60 mm cao 30 mm"

Or run interactively:

    python -m src.text_to_cad

## Current execution boundary

- Rectangular base solid: supported by the existing SOLIDWORKS COM starter script.
- Fillet, chamfer and holes: parsed into the plan, preview only.
- The parser does not call SOLIDWORKS and cannot alter an open document.
- Missing or non-positive dimensions are rejected instead of guessed.

## Next milestone

Connect a validated rectangular-prism plan to the existing create_box.py workflow.
Then implement optional features as separate, tested COM operations. Do not enable
automatic feature execution until selection strategy and geometry validation are
tested against the user's SOLIDWORKS 2026 installation.
