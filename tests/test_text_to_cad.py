import unittest
from src.text_to_cad import ParseError, parse_description

class TextToCADTests(unittest.TestCase):
    def test_labelled_dimensions_and_features(self):
        plan = parse_description(
            "Tao hop dai 100 mm, rong 60 mm, cao 30 mm, "
            "bo goc R5, khoet 4 lo duong kinh 3 mm"
        )
        self.assertEqual(plan.dimensions_mm, {"length": 100.0, "width": 60.0, "height": 30.0})
        self.assertEqual([item.kind for item in plan.features], ["fillet", "holes"])
        self.assertEqual(plan.features[0].parameters["radius_mm"], 5.0)
        self.assertEqual(plan.features[1].parameters["count"], 4)
        self.assertEqual(plan.features[1].parameters["diameter_mm"], 3.0)

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

if __name__ == "__main__":
    unittest.main()
