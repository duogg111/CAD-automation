import unittest
from src.text_to_cad import ParseError, parse_description
from src.solidworks_features import (
    SW_FM_FILLET,
    SW_CONST_RADIUS_FILLET,
    SW_FEATURE_FILLET_CIRCULAR,
    SW_FEATURE_FILLET_CONIC_RHO_ZERO_CHAMFER,
    SW_FILLET_OVERFLOW_DEFAULT,
    SW_END_COND_THROUGH_ALL,
    _call_member,
    compute_four_corner_hole_centers_mm,
    get_box_top_perimeter_edges,
    get_box_vertical_edges,
    is_vertical_extrusion_edge,
)

class DummyVertex:
    def __init__(self, point):
        self.point = point
    def GetPoint(self):
        return self.point

class DummyEdge:
    def __init__(self, start, end):
        self.start = DummyVertex(start)
        self.end = DummyVertex(end)
    def GetStartVertex(self):
        return self.start
    def GetEndVertex(self):
        return self.end

class DummyBody:
    def __init__(self, edges):
        self.edges = edges
    def GetEdges(self):
        return self.edges

class DummyModel:
    def __init__(self, bodies):
        self.bodies = bodies
    def GetBodies2(self, body_type, visible_only):
        return self.bodies

class TextToCADTests(unittest.TestCase):
    def test_enum_constants(self):
        self.assertEqual(SW_FM_FILLET, 1)
        self.assertEqual(SW_CONST_RADIUS_FILLET, 0)
        self.assertEqual(SW_FEATURE_FILLET_CIRCULAR, 0)
        self.assertEqual(SW_FEATURE_FILLET_CONIC_RHO_ZERO_CHAMFER, 3)
        self.assertEqual(SW_FILLET_OVERFLOW_DEFAULT, 0)
        self.assertEqual(SW_END_COND_THROUGH_ALL, 1)

    def test_labelled_dimensions_and_features(self):
        plan = parse_description(
            "Tao hop dai 100 mm, rong 60 mm, cao 30 mm, "
            "bo goc R5, khoet 4 lo duong kinh 3 mm"
        )
        self.assertEqual(plan.dimensions_mm, {"length": 100.0, "width": 60.0, "height": 30.0})
        self.assertEqual([item.kind for item in plan.features], ["fillet", "holes"])
        self.assertEqual(plan.features[0].parameters["radius_mm"], 5.0)
        self.assertEqual(plan.features[0].parameters["target"], "four_vertical_outer_edges")
        self.assertEqual(plan.features[1].parameters["count"], 4)
        self.assertEqual(plan.features[1].parameters["diameter_mm"], 3.0)
        self.assertEqual(plan.features[1].parameters["edge_offset_mm"], 10.0)

    def test_chamfer_and_explicit_hole_offset(self):
        plan = parse_description(
            "Tao hop dai 100 mm rong 60 mm cao 30 mm, "
            "vat canh 2 mm, khoet 4 lo phi 3 mm cach mep 8 mm"
        )
        self.assertEqual([f.kind for f in plan.features], ["chamfer", "holes"])
        self.assertEqual(plan.features[0].parameters["distance_mm"], 2.0)
        self.assertEqual(plan.features[0].parameters["target"], "four_top_perimeter_edges")
        self.assertEqual(plan.features[1].parameters["edge_offset_mm"], 8.0)
        self.assertFalse(plan.features[1].parameters["offset_was_defaulted"])

    def test_chamfer_accented_phrase(self):
        plan = parse_description("Tạo hộp dài 100 mm rộng 60 mm cao 30 mm, vát mép trên 2,5 mm")
        self.assertEqual(plan.features[0].kind, "chamfer")
        self.assertEqual(plan.features[0].parameters["distance_mm"], 2.5)

    def test_fillet_accented_phrase_and_decimal_comma(self):
        plan = parse_description(
            "Tạo hộp dài 100 mm rộng 60 mm cao 30 mm, bo tròn góc bán kính 2,5 mm"
        )
        self.assertEqual(plan.features[0].kind, "fillet")
        self.assertEqual(plan.features[0].parameters["radius_mm"], 2.5)

    def test_default_hole_offset_warns_user(self):
        plan = parse_description("Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 4 lo D3")
        self.assertTrue(plan.features[0].parameters["offset_was_defaulted"])
        self.assertTrue(any("10 mm" in warning for warning in plan.warnings))

    def test_non_four_hole_count_is_preview_only(self):
        plan = parse_description("Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D3")
        self.assertEqual(plan.features[0].parameters["layout"], "unspecified")
        self.assertTrue(any("so lo khac" in warning for warning in plan.warnings))

    def test_dimension_tuple(self):
        plan = parse_description("Tao mot cai hop 100 x 60 x 30 mm")
        self.assertEqual(plan.dimensions_mm["length"], 100.0)
        self.assertEqual(plan.dimensions_mm["width"], 60.0)
        self.assertEqual(plan.dimensions_mm["height"], 30.0)

    def test_decimal_comma(self):
        plan = parse_description("Tao hop dai 10,5 mm rong 8 mm cao 2 mm")
        self.assertEqual(plan.dimensions_mm["length"], 10.5)

    def test_missing_dimension_is_rejected(self):
        with self.assertRaises(ParseError):
            parse_description("Tao hop dai 100 mm rong 60 mm")

    def test_non_positive_dimension_is_rejected(self):
        with self.assertRaises(ParseError):
            parse_description("Tao hop dai 0 mm rong 60 mm cao 30 mm")

    def test_unsupported_shape_is_rejected(self):
        with self.assertRaises(ParseError):
            parse_description("Tao mot truc dai 100 mm rong 10 mm cao 10 mm")

    def test_fillet_radius_must_fit_footprint(self):
        with self.assertRaises(ParseError):
            parse_description("Tao hop dai 100 mm rong 60 mm cao 30 mm bo goc R30")

    def test_holes_must_clear_chamfer_and_fillet(self):
        with self.assertRaises(ParseError):
            parse_description(
                "Tao hop dai 100 mm rong 60 mm cao 30 mm, "
                "bo goc R5, khoet 4 lo D3 cach mep 5 mm"
            )

    def test_vertical_edge_classifier_accepts_shortened_vertical_edge(self):
        self.assertTrue(
            is_vertical_extrusion_edge((0.0, 0.0, 0.002), (0.0, 0.0, 0.028), 30)
        )
        self.assertFalse(
            is_vertical_extrusion_edge((0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 30)
        )

    def test_get_exactly_four_vertical_box_edges(self):
        edges = [
            DummyEdge((0.0, 0.0, 0.002), (0.0, 0.0, 0.028)),
            DummyEdge((0.1, 0.0, 0.002), (0.1, 0.0, 0.028)),
            DummyEdge((0.0, 0.06, 0.002), (0.0, 0.06, 0.028)),
            DummyEdge((0.1, 0.06, 0.028), (0.1, 0.06, 0.002)),
            DummyEdge((0.0, 0.0, 0.0), (0.1, 0.0, 0.0)),
        ]
        model = DummyModel([DummyBody(edges)])
        self.assertEqual(len(get_box_vertical_edges(model, 30)), 4)

    def test_get_four_top_perimeter_edges(self):
        edges = [
            DummyEdge((0.0, 0.0, 0.03), (0.1, 0.0, 0.03)),
            DummyEdge((0.1, 0.0, 0.03), (0.1, 0.06, 0.03)),
            DummyEdge((0.1, 0.06, 0.03), (0.0, 0.06, 0.03)),
            DummyEdge((0.0, 0.06, 0.03), (0.0, 0.0, 0.03)),
            DummyEdge((0.0, 0.0, 0.0), (0.1, 0.0, 0.0)),
        ]
        model = DummyModel([DummyBody(edges)])
        self.assertEqual(len(get_box_top_perimeter_edges(model, 30)), 4)

    def test_four_corner_hole_centers(self):
        self.assertEqual(
            compute_four_corner_hole_centers_mm(100, 60, 3, 10, fillet_radius_mm=5),
            [(10, 10), (90, 10), (90, 50), (10, 50)],
        )

    def test_hole_layout_rejects_overlap_or_edge_collision(self):
        with self.assertRaises(ValueError):
            compute_four_corner_hole_centers_mm(100, 60, 10, 4, fillet_radius_mm=0)
        with self.assertRaises(ValueError):
            compute_four_corner_hole_centers_mm(30, 20, 4, 10, fillet_radius_mm=0)

    def test_zero_argument_com_member_wrapper(self):
        class Fake:
            def function_member(self):
                return "called"
            @property
            def property_member(self):
                return "value"
        fake = Fake()
        self.assertEqual(_call_member(fake, "function_member"), "called")
        self.assertEqual(_call_member(fake, "property_member"), "value")

    def test_callable_dispatch_value_is_not_invoked(self):
        class FakeDispatchValue:
            def __call__(self):
                raise AssertionError("A COM dispatch value must not be invoked.")
        class FakeComObject:
            def __init__(self):
                self.dispatch_value = FakeDispatchValue()
            @property
            def GetStartVertex(self):
                return self.dispatch_value
        obj = FakeComObject()
        self.assertIs(_call_member(obj, "GetStartVertex"), obj.dispatch_value)


    def test_rounded_corner_requires_extra_hole_offset(self):
        with self.assertRaises(ValueError):
            compute_four_corner_hole_centers_mm(
                100, 60, 3, 9.5, fillet_radius_mm=5
            )


    def test_execution_status_marks_non_four_holes_preview_only(self):
        plan = parse_description(
            "Tao hop dai 100 mm rong 60 mm cao 30 mm, khoet 2 lo D3"
        )
        status = plan.to_dict()["execution_status"]
        self.assertEqual(status["holes"], "preview_only")
        self.assertEqual(status["fillet"], "not_requested")
        self.assertEqual(status["chamfer"], "not_requested")

    def test_execution_status_marks_requested_features(self):
        plan = parse_description(
            "Tao hop dai 100 mm rong 60 mm cao 30 mm, "
            "vat canh 2 mm, bo goc R5, khoet 4 lo D3"
        )
        status = plan.to_dict()["execution_status"]
        self.assertEqual(status["chamfer"], "implemented_pending_SOLIDWORKS_verification")
        self.assertEqual(status["fillet"], "verified_on_user_SOLIDWORKS")
        self.assertEqual(status["holes"], "implemented_pending_SOLIDWORKS_verification")

if __name__ == "__main__":
    unittest.main()
