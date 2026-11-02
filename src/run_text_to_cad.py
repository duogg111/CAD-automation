"""End-to-end text-to-CAD entry point for rectangular-prism requests."""
from __future__ import annotations
import argparse
import os
from src.text_to_cad import ParseError, parse_description
from src.create_box import create_box, OUTPUT_DIR
from src.solidworks_features import compute_four_corner_hole_centers_mm

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

    fillet_features = [item for item in plan.features if item.kind == "fillet"]
    chamfer_features = [item for item in plan.features if item.kind == "chamfer"]
    hole_features = [item for item in plan.features if item.kind == "holes"]

    fillet_radius = None
    chamfer_distance = None
    hole_diameter = None
    hole_count = 0
    hole_offset = None

    if chamfer_features:
        chamfer_distance = float(chamfer_features[0].parameters["distance_mm"])
        print(
            f"Chamfer: {chamfer_distance:g} mm on the four edges around the top face."
        )
    if fillet_features:
        fillet_radius = float(fillet_features[0].parameters["radius_mm"])
        print(f"Fillet: R{fillet_radius:g} mm on the four vertical outer corner edges.")
    if hole_features:
        hole = hole_features[0]
        hole_count = int(hole.parameters["count"])
        hole_diameter = float(hole.parameters["diameter_mm"])
        if hole.parameters.get("layout") == "four_corners":
            hole_offset = float(hole.parameters["edge_offset_mm"])
            centers = compute_four_corner_hole_centers_mm(
                plan.dimensions_mm["length"],
                plan.dimensions_mm["width"],
                hole_diameter,
                hole_offset,
                fillet_radius_mm=fillet_radius or 0.0,
                chamfer_distance_mm=chamfer_distance or 0.0,
            )
            print(
                f"Holes: 4 through-holes, diameter {hole_diameter:g} mm, "
                f"four-corner layout, edge offset {hole_offset:g} mm."
            )
            print("Hole centers (X, Y) in mm:", centers)
        else:
            print(
                f"PREVIEW ONLY: {hole_count} holes, diameter {hole_diameter:g} mm; "
                "automatic layout is not supported yet."
            )

    for warning in plan.warnings:
        print("WARNING:", warning)

    requested = []
    if chamfer_distance is not None:
        requested.append(f"Chamfer {chamfer_distance:g} mm on top perimeter")
    if fillet_radius is not None:
        requested.append(f"Fillet R{fillet_radius:g} mm on vertical corners")
    if hole_offset is not None and hole_diameter is not None:
        requested.append(f"4 Through All holes D{hole_diameter:g} mm")

    prompt = (
        "\nCreate the box with: " + ", ".join(requested) + "? [y/N]: "
        if requested
        else "\nCreate the rectangular base solid in SOLIDWORKS? [y/N]: "
    )
    confirm = input(prompt)
    if confirm.strip().lower() not in {"y", "yes"}:
        print("Cancelled. No SOLIDWORKS model was created.")
        return

    saved_path = create_box(
        length=plan.dimensions_mm["length"],
        width=plan.dimensions_mm["width"],
        height=plan.dimensions_mm["height"],
        output_path=args.output,
        fillet_radius_mm=fillet_radius,
        chamfer_distance_mm=chamfer_distance,
        hole_count=hole_count if hole_offset is not None else 0,
        hole_diameter_mm=hole_diameter if hole_offset is not None else None,
        hole_edge_offset_mm=hole_offset,
    )
    print("\nCompleted:", saved_path)

if __name__ == "__main__":
    main()
