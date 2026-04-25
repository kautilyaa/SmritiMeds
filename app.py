"""Streamlit prototype for SmritiMeds medication reminders."""

from __future__ import annotations

import io
from typing import Any

import streamlit as st

from anthropic_client import SmritiMedsAPIError, analyze_medication_images, debug_request_summary
from config import load_config, load_env_file
from local_pill_pipeline import analyze_local_pills
from pill_detector import DetectorUnavailableError
from pill_identifier_model import LocalVisionUnavailableError, local_model_status


def _uploaded_file_to_payload(uploaded_file: Any) -> tuple[bytes, str] | None:
    if uploaded_file is None:
        return None
    image_bytes = uploaded_file.getvalue()
    mime_type = getattr(uploaded_file, "type", None) or "image/jpeg"
    if not image_bytes:
        return None
    return image_bytes, mime_type


def _payload_to_image(payload: tuple[bytes, str] | None) -> Any:
    if payload is None:
        return None
    try:
        from PIL import Image
    except Exception:
        return None
    return Image.open(io.BytesIO(payload[0])).convert("RGB")


def _render_schedule(schedule: list[dict[str, Any]]) -> None:
    if not schedule:
        st.info("No reliable daily schedule could be extracted from the image.")
        return

    st.subheader("Daily reminder checklist")
    for index, entry in enumerate(schedule):
        key = f"reminder_{index}_{entry['time_of_day']}_{entry['label']}"
        label = f"**{entry['time_of_day']}** — {entry['label']}"
        details = ", ".join(entry["items"]) if entry["items"] else "Medication item not identified"
        if entry["dose"]:
            details = f"{details} · Dose: {entry['dose']}"
        if entry["notes"]:
            details = f"{details} · {entry['notes']}"
        st.checkbox(label, key=key, help=details)


def _render_pill_appearance(appearance: dict[str, Any]) -> None:
    values = [
        ("Color", appearance.get("color")),
        ("Shape", appearance.get("shape")),
        ("Imprint", appearance.get("imprint")),
        ("Notes", appearance.get("notes")),
    ]
    present = [(name, value) for name, value in values if value]
    if not present:
        st.caption("No pill appearance details were extracted confidently.")
        return

    for name, value in present:
        st.write(f"**{name}:** {value}")


def _render_local_vision(parsed: dict[str, Any], source_image: Any) -> None:
    st.subheader("Local pill vision beta")
    st.caption(
        "Uses a local YOLO detector plus Hugging Face pillIdentifierAI/pillIdentifier. "
        "This is a best-effort hackathon feature and should not be treated as authoritative."
    )
    st.json(local_model_status())

    if source_image is None:
        st.info("Add a pill image to run local detection and classification.")
        return

    try:
        local_result = analyze_local_pills(
            source_image,
            medication_name=parsed.get("medication_name"),
        )
    except (DetectorUnavailableError, LocalVisionUnavailableError) as exc:
        st.info(str(exc))
        return
    except Exception as exc:
        st.warning(f"Local vision failed: {exc}")
        return

    st.write(f"Detected **{local_result['count']}** pill region(s).")
    st.image(local_result["annotated_image"], caption="YOLO pill detections", use_container_width=True)

    for detection in local_result["detections"]:
        with st.expander(f"Pill region {detection['pill_index']}"):
            st.image(detection["crop"], caption=f"Pill crop {detection['pill_index']}", width=180)
            if detection["confidence"] is not None:
                st.write(f"**Detection confidence:** {detection['confidence']:.2f}")
            if detection["best_match"] is not None:
                st.write(
                    f"**Best text match vs extracted medication:** "
                    f"{detection['best_match']['label']} "
                    f"(match {detection['best_match']['match_score']:.2f})"
                )
            st.write("**Top local visual candidates**")
            for prediction in detection["predictions"]:
                st.write(f"- {prediction['label']} ({prediction['score']:.3f})")


def main() -> None:
    load_env_file()
    config = load_config()

    st.set_page_config(page_title="SmritiMeds", page_icon="💊", layout="centered")
    st.title("💊 SmritiMeds")
    st.caption(
        "Medication reminder and pill verification prototype powered by Claude Vision. "
        "Smriti = remembrance."
    )
    st.warning(
        "Prototype only: review extracted instructions manually before relying on reminders. "
        "This app does not provide medical advice."
    )

    with st.sidebar:
        st.subheader("Model configuration")
        st.json(debug_request_summary(config))
        st.markdown(
            "- Upload a prescription bottle, pharmacy label, or blister pack.\n"
            "- Optionally upload a second pill image for visual consistency checking.\n"
            "- The model will extract reminders, not new dosage guidance.\n"
            "- Optional local beta: YOLO pill detection + Hugging Face pill classification."
        )

    if not config.api_key:
        st.error("Missing ANTHROPIC_API_KEY. Add it to SmritiMeds/.env or your environment.")
        st.stop()

    st.subheader("1) Upload medication label")
    label_camera = st.camera_input("Take a photo of the medication label or blister pack")
    label_upload = st.file_uploader(
        "Or upload a label image",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
    )

    st.subheader("2) Optional pill verification image")
    verification_camera = st.camera_input("Take a photo of the loose pill or blister pack (optional)")
    verification_upload = st.file_uploader(
        "Or upload a pill verification image",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
        key="pill_verification_upload",
    )

    label_source = label_camera or label_upload
    verification_source = verification_camera or verification_upload
    run_local_vision = st.checkbox(
        "Also run local YOLO + Hugging Face pill identification beta",
        value=verification_source is not None,
    )

    analyze_clicked = st.button("Analyze medication", type="primary", use_container_width=True)
    if not analyze_clicked:
        return

    label_payload = _uploaded_file_to_payload(label_source)
    verification_payload = _uploaded_file_to_payload(verification_source)

    if not label_payload:
        st.error("Upload or capture a medication label image first.")
        return

    with st.spinner("Reading label, extracting reminders, and checking confidence..."):
        try:
            parsed, raw_json = analyze_medication_images(
                config,
                label_image_bytes=label_payload[0],
                label_mime_type=label_payload[1],
                verification_image_bytes=verification_payload[0] if verification_payload else None,
                verification_mime_type=verification_payload[1] if verification_payload else None,
            )
        except SmritiMedsAPIError as exc:
            st.error(str(exc))
            return

    cols = st.columns(3)
    cols[0].metric("Medication", parsed["medication_name"] or "Unknown")
    cols[1].metric("Strength", parsed["strength"] or "Unknown")
    cols[2].metric("Times/day", parsed["times_per_day"])

    if parsed["needs_manual_review"]:
        st.warning("Manual review recommended before using this reminder schedule.")
    else:
        st.success("Model found enough signal to generate a reminder schedule.")

    if parsed["instructions_raw"]:
        st.subheader("Extracted label instructions")
        st.write(parsed["instructions_raw"])

    _render_schedule(parsed["schedule"])

    st.subheader("Verification summary")
    st.write(parsed["verification_summary"])

    st.subheader("Pill appearance notes")
    _render_pill_appearance(parsed["pill_appearance"])

    if parsed["confidence_notes"]:
        st.subheader("Confidence notes")
        for note in parsed["confidence_notes"]:
            st.write(f"- {note}")

    with st.expander("Raw JSON payload"):
        st.code(raw_json, language="json")

    if run_local_vision:
        local_source = _payload_to_image(verification_payload or label_payload)
        _render_local_vision(parsed, local_source)


if __name__ == "__main__":
    main()
