from pathlib import Path

import streamlit as st

from navamatn.app import run_app_pipeline

st.set_page_config(page_title="navamatn", layout="wide")
st.title("navamatn")
st.caption("Upload one audio file, get transcript and summary.")

uploaded_file = st.file_uploader("Audio file", type=["wav", "mp3", "m4a", "flac"])
language_hint = st.text_input("Language hint (optional)", value="")

if st.button("Run pipeline"):
    if uploaded_file is None:
        st.error("Upload a file first.")
    else:
        temp_path = Path(".tmp_uploaded_audio")
        temp_path.write_bytes(uploaded_file.getvalue())

        try:
            result = run_app_pipeline(str(temp_path), language_hint=language_hint or None)
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
        else:
            st.subheader("Transcript")
            st.write(result.transcript.text)
            st.subheader("Short summary")
            st.write(result.summary.short_summary)
            if result.summary.bullet_points:
                st.subheader("Bullet points")
                for point in result.summary.bullet_points:
                    st.write(f"- {point}")
            if result.enrichment.keywords:
                st.subheader("Keywords")
                st.write(", ".join(result.enrichment.keywords))
            if result.enrichment.action_items:
                st.subheader("Action items")
                for item in result.enrichment.action_items:
                    st.write(f"- {item}")
        finally:
            if temp_path.exists():
                temp_path.unlink()
