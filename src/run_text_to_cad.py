"""End-to-end text-to-CAD entry point for rectangular-prism requests."""
from __future__ import annotations
import argparse
import os
from src.text_to_cad import ParseError, parse_description
from src.create_box import create_box, OUTPUT_DIR
from src.solidworks_features import compute_hole_centers_mm


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
    hole_features = [
        item for item in plan.features if item.kind in {"holes", "tapped_holes"}
    ]

    fillet_radius = None
    chamfer_distance = None
    hole_diameter = None
    hole_count = 0
    hole_offset = None
    hole_centers = None
    tapped_hole_size = None

    if chamfer_features:
        chamfer_distance = float(chamfer_features[0].parameters["distance_mm"])
        print(f"Chamfer: {chamfer_distance:g} mm on the four edges around the top face.")
    if fillet_features:
        fillet_radius = float(fillet_features[0].parameters["radius_mm"])
        print(f"Fillet: R{fillet_radius:g} mm on the four vertical outer corner edges.")

    if hole_features:
        hole = hole_features[0]
        params = hole.parameters
        hole_count = int(params["count"])
        layout = str(params["layout"])
        axis = str(params.get("axis", "x"))
        if hole.kind == "tapped_holes":
            tapped_hole_size = str(params["size"])
            hole_diameter = float(params["tap_drill_diameter_mm"])
            print(
                f"Tapped holes: {hole_count} x ISO {tapped_hole_size} coarse thread, "
                f"tap drill {hole_diameter:g} mm, pitch {float(params['pitch_mm']):g} mm."
            )
            print("Thread representation: Hole Wizard tapped-hole/cosmetic thread, not helical solid geometry.")
        else:
            hole_diameter = float(params["diameter_mm"])
            print(f"Through-holes: {hole_count} x diameter {hole_diameter:g} mm.")

        if layout == "unspecified":
            print("PREVIEW ONLY: this hole count/layout has no automatic placement rule yet.")
            hole_count = 0
        else:
            try:
                hole_centers = compute_hole_centers_mm(
                    length_mm=plan.dimensions_mm["length"],
                    width_mm=plan.dimensions_mm["width"],
                    count=hole_count,
                    layout=layout,
                    edge_offset_mm=params.get("edge_offset_mm"),
                    center_distance_mm=params.get("center_distance_mm"),
                    axis=axis,
                    explicit_points=params.get("centers_mm"),
                    diameter_mm=hole_diameter,
                    fillet_radius_mm=fillet_radius or 0.0,
                    chamfer_distance_mm=chamfer_distance or 0.0,
                )
            except ValueError as exc:
                parser.error(str(exc))
            print(f"Layout: {layout}")
            print("Hole centers (X, Y) in mm:", hole_centers)
            if layout == "four_corners" and params.get("offset_was_defaulted"):
                print("NOTE: the four-corner layout uses the stated program default: 10 mm from each adjacent edge.")
            elif layout == "center_to_center_x":
                print(f"Center-to-center distance along X: {float(params['center_distance_mm']):g} mm.")
            elif layout == "center_to_center_y":
                print(f"Center-to-center distance along Y: {float(params['center_distance_mm']):g} mm.")

    for warning in plan.warnings:
        print("WARNING:", warning)

    requested = []
    if chamfer_distance is not None:
        requested.append(f"Chamfer {chamfer_distance:g} mm on top perimeter")
    if fillet_radius is not None:
        requested.append(f"Fillet R{fillet_radius:g} mm on vertical corners")
    if hole_centers is not None and hole_centers:
        if tapped_hole_size:
            requested.append(f"{hole_count} ISO {tapped_hole_size} tapped holes")
        else:
            requested.append(f"{hole_count} Through All holes D{hole_diameter:g} mm")

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
        hole_count=len(hole_centers) if hole_centers else 0,
        hole_diameter_mm=hole_diameter if tapped_hole_size is None else None,
        hole_edge_offset_mm=hole_offset,
        hole_centers_mm=hole_centers,
        tapped_hole_size=tapped_hole_size,
    )
    print("\nCompleted:", saved_path)


if __name__ == "__main__":
    main()
