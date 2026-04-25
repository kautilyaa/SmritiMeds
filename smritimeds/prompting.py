"""Prompt builders for the SmritiMeds medication reminder application."""

from __future__ import annotations

from textwrap import dedent


SYSTEM_PROMPT = dedent(
    """
    You are SmritiMeds, a medication adherence assistant.

    Your job is limited to:
    1. reading medication labels or blister-pack text from images,
    2. extracting visible medication instructions,
    3. turning those instructions into a reminder schedule,
    4. optionally comparing a pill photo against the visible label details.

    Safety rules:
    - Do not invent facts not visible in the image.
    - Do not provide new dosage advice or treatment recommendations.
    - Only restate or normalize what is visible on the packaging/label.
    - If instructions are unclear, ambiguous, partially occluded, or unreadable, set needs_manual_review to true.
    - If pill identity cannot be verified confidently from the supplied images, say so clearly.
    - Output valid JSON only. No markdown fences. No extra prose.
    """
).strip()


def build_user_prompt(include_verification_image: bool) -> str:
    verification_instructions = (
        "A second image is included with a loose pill or blister pack. Compare it against the label when possible."
        if include_verification_image
        else "No second pill-verification image is included. Leave verification focused on what can be inferred from the label image only."
    )
    return dedent(
        f"""
        Analyze the provided medication image(s) and return exactly one JSON object with this shape:

        {{
          "medication_name": "string or null",
          "strength": "string or null",
          "instructions_raw": "string or null",
          "times_per_day": 0,
          "schedule": [
            {{
              "time_of_day": "Morning|Noon|Evening|Bedtime|Custom",
              "label": "short reminder label",
              "dose": "string or null",
              "items": ["list of medication names or pill descriptors"],
              "notes": "string or null"
            }}
          ],
          "pill_appearance": {{
            "color": "string or null",
            "shape": "string or null",
            "imprint": "string or null",
            "notes": "string or null"
          }},
          "verification_summary": "string",
          "confidence_notes": ["short strings"],
          "needs_manual_review": true
        }}

        Rules for filling the JSON:
        - Use null when a field cannot be read confidently.
        - Prefer the exact visible medication name.
        - instructions_raw should preserve the visible label instruction as closely as possible.
        - times_per_day should be an integer estimate only when clearly supported by the visible text; otherwise use 0.
        - schedule should be empty if a reliable schedule cannot be extracted.
        - If the label says things like "twice daily", normalize into schedule entries such as Morning and Evening.
        - If the timing is custom or vague (for example "every 6 hours"), use a Custom entry with notes.
        - verification_summary must clearly state whether the pill appears consistent, uncertain, or not verifiable.
        - confidence_notes should list the reasons for uncertainty, such as glare, blur, curved label text, hidden imprint, or cropped image.

        {verification_instructions}
        """
    ).strip()


def build_text_analysis_prompt(raw_text: str, document_kind: str) -> str:
    return dedent(
        f"""
        The following text was extracted from a {document_kind.replace('_', ' ')}.
        Use only this OCR text and do not invent any medication facts beyond it.

        OCR TEXT:
        {raw_text}

        Return exactly one JSON object with this shape:

        {{
          "medication_name": "string or null",
          "strength": "string or null",
          "instructions_raw": "string or null",
          "times_per_day": 0,
          "schedule": [
            {{
              "time_of_day": "Morning|Noon|Evening|Bedtime|Custom",
              "label": "short reminder label",
              "dose": "string or null",
              "items": ["list of medication names or pill descriptors"],
              "notes": "string or null"
            }}
          ],
          "pill_appearance": {{
            "color": "string or null",
            "shape": "string or null",
            "imprint": "string or null",
            "notes": "string or null"
          }},
          "verification_summary": "string",
          "confidence_notes": ["short strings"],
          "needs_manual_review": true
        }}

        Rules:
        - Base the answer only on the OCR text shown above.
        - If the OCR text is uncertain or incomplete, set needs_manual_review to true.
        - If timing is explicit, convert it into a reminder schedule.
        - If timing is vague, use a Custom entry or leave schedule empty.
        - Do not provide independent dosage advice.
        - verification_summary should mention that the result came from OCR text, not visual pill verification.
        - Output valid JSON only.
        """
    ).strip()
