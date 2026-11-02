"""End-to-end text-to-CAD entry point for rectangular-prism requests."""
from __future__ import annotations
import argparse
import os
from src.text_to_cad import ParseError, parse_description
from src.create_box import create_box, OUTPUT_DIR

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse a Vietnamese part description and create a SOLIDWORKS part."
    )
    parser.add_argument("description", nargs="?", help="Natural-language part description")
    parser.add_argument(
        "--output",
        default=os.path.join(OUTPUT_DIR, "Generated_From_Text.SLDPRT"),
        help="Output SLDPRT path (default: output/Generated_From_Text.SLDPRT)",
    )
    args = parser.parse_args()
    description = args.description or input("Mo ta chi tiet can ve: ")

    try:
        plan = parse_description(description)
    except ParseError as exc:
        parser.error(str(exc))

    print("\nCAD PLAN")
    print(f"Shape: {plan.shape}")
    print(f"Length: {plan.dimensions_mm['length']} mm")
    print(f"Width:  {plan.dimensions_mm['width']} mm")
    print(f"Height: {plan.dimensions_mm['height']} mm")
    for warning in plan.warnings:
        print("WARNING:", warning)

    if plan.features:
        print("\nAdditional features are preview-only and will NOT be applied.")
    confirm = input("\nCreate the rectangular base solid in SOLIDWORKS? [y/N]: ")
    if confirm.strip().lower() not in {"y", "yes"}:
        print("Cancelled. No SOLIDWORKS model was created.")
        return

    saved_path = create_box(
        length=plan.dimensions_mm["length"],
        width=plan.dimensions_mm["width"],
        height=plan.dimensions_mm["height"],
        output_path=args.output,
    )
    print("\nCompleted:", saved_path)

if __name__ == "__main__":
    main()
