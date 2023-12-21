import os

import openai
import streamlit as st

import common
import utils

st.title("Text to Speech Converter")

common.manage_openai_credentials()

with st.sidebar:
    st.selectbox("model", ["tts-1", "tts-1-hd"], key="model")
    st.selectbox(
        "voice", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], key="voice"
    )

st.file_uploader("Choose a text file", type="txt", key="file_uploader")
if st.session_state.file_uploader is not None:
    st.button("Convert to MP3", key="convert_to_mp3")
    if st.session_state.convert_to_mp3:
        text = st.session_state.file_uploader.getvalue().decode("utf-8")
        st.session_state.audio_data = utils.text_to_speech(
            text, model=st.session_state.model, voice=st.session_state.voice
        )
        st.session_state.file_name, _ = os.path.splitext(
            st.session_state.file_uploader.name
        )
        st.session_state.audio_file_name = f"{st.session_state.file_name}_{st.session_state.model}_{st.session_state.voice}.mp3"

    if st.session_state.get("audio_data", None) is not None:
        st.audio(
            st.session_state.audio_data,
            format="audio/mp3",
            start_time=0,
        )
        st.download_button(
            label="Download MP3",
            data=st.session_state.audio_data,
            file_name=st.session_state.audio_file_name,
            mime="audio/mp3",
        )
