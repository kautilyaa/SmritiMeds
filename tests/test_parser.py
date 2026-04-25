import unittest

from smritimeds.parser import ParseError, parse_model_output


class ParserTests(unittest.TestCase):
    def test_parses_markdown_wrapped_json(self) -> None:
        payload = """```json
        {
          "medication_name": "Amoxicillin",
          "strength": "500 mg",
          "instructions_raw": "Take 1 capsule by mouth twice daily",
          "times_per_day": "2",
          "schedule": [
            {
              "time_of_day": "Evening",
              "label": "Take capsule",
              "dose": "1 capsule",
              "items": ["Amoxicillin"],
              "notes": "After dinner"
            },
            {
              "time_of_day": "Morning",
              "label": "Take capsule",
              "dose": "1 capsule",
              "items": ["Amoxicillin"],
              "notes": null
            }
          ],
          "pill_appearance": {
            "color": "pink",
            "shape": "capsule",
            "imprint": null,
            "notes": "label image only"
          },
          "verification_summary": "Appears plausible but not fully verifiable.",
          "confidence_notes": ["curved text", "no imprint visible"],
          "needs_manual_review": "true"
        }
        ```"""

        parsed = parse_model_output(payload)
        self.assertEqual(parsed["medication_name"], "Amoxicillin")
        self.assertEqual(parsed["times_per_day"], 2)
        self.assertEqual(parsed["schedule"][0]["time_of_day"], "Morning")
        self.assertTrue(parsed["needs_manual_review"])

    def test_defaults_when_schedule_missing(self) -> None:
        parsed = parse_model_output(
            """
            {
              "medication_name": "Ibuprofen",
              "strength": null,
              "instructions_raw": null,
              "times_per_day": null,
              "schedule": "unclear",
              "pill_appearance": null,
              "verification_summary": "",
              "confidence_notes": "blurry",
              "needs_manual_review": false
            }
            """
        )

        self.assertEqual(parsed["times_per_day"], 0)
        self.assertEqual(parsed["schedule"], [])
        self.assertEqual(parsed["verification_summary"], "Verification result unavailable.")
        self.assertFalse(parsed["needs_manual_review"])

    def test_raises_for_missing_json(self) -> None:
        with self.assertRaises(ParseError):
            parse_model_output("No structured output here")


if __name__ == "__main__":
    unittest.main()
