import unittest
from src.text_to_cad import ParseError, parse_description
from src.solidworks_features import (
    _call_member,
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

    def test_fillet_accented_phrase_and_decimal_comma(self):
        plan = parse_description(
            "Tạo hộp dài 100 mm rộng 60 mm cao 30 mm, bo tròn góc bán kính 2,5 mm"
        )
        self.assertEqual(plan.features[0].kind, "fillet")
        self.assertEqual(plan.features[0].parameters["radius_mm"], 2.5)

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

    def test_vertical_edge_classifier(self):
        self.assertTrue(
            is_vertical_extrusion_edge((0.0, 0.0, 0.0), (0.0, 0.0, 0.03), 30)
        )
        self.assertTrue(
            is_vertical_extrusion_edge((0.1, 0.2, 0.03), (0.1, 0.2, 0.0), 30)
        )
        self.assertFalse(
            is_vertical_extrusion_edge((0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 30)
        )
        self.assertFalse(
            is_vertical_extrusion_edge((0.0, 0.0, 0.0), (0.0, 0.0, 0.02), 30)
        )

    def test_get_exactly_four_vertical_box_edges(self):
        edges = [
            DummyEdge((0.0, 0.0, 0.0), (0.0, 0.0, 0.03)),
            DummyEdge((0.1, 0.0, 0.0), (0.1, 0.0, 0.03)),
            DummyEdge((0.0, 0.06, 0.0), (0.0, 0.06, 0.03)),
            DummyEdge((0.1, 0.06, 0.03), (0.1, 0.06, 0.0)),
            DummyEdge((0.0, 0.0, 0.0), (0.1, 0.0, 0.0)),
        ]
        model = DummyModel([DummyBody(edges)])
        result = get_box_vertical_edges(model, 30)
        self.assertEqual(len(result), 4)

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

if __name__ == "__main__":
    unittest.main()
