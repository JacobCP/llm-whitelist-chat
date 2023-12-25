import os
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

import common
import utils

st.title("Text to Speech Converter")
st.session_state.audio_data = st.session_state.get("audio_data", {})

common.manage_openai_credentials()
FORMATS = ["flac", "opus", "aac", "mp3"]

with st.sidebar:
    model = st.selectbox("model", ["tts-1", "tts-1-hd"])
    voice = st.selectbox("voice", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
    format = st.selectbox("output format", ["mp3", "flac", "opus", "aac", "wav"])
    format_to_use = format if format in FORMATS else "flac"

if st.session_state.get("zip_uploader", None) is None:
    st.file_uploader("Choose a text file", type="txt", key="file_uploader")
if st.session_state.get("file_uploader", None) is None:
    st.file_uploader(
        "Or upload a zip file of text files", type="zip", key="zip_uploader"
    )

if (
    st.session_state.get("file_uploader", None) is not None
    or st.session_state.get("zip_uploader", None) is not None
):
    convert = st.button(f"Convert to {format}")
    if convert:
        if not st.session_state.get("OPENAI_API_KEY", ""):
            st.error("please provide api key")
        else:

            def text_to_audio(
                text,
                model=model,
                voice=voice,
                format_to_use=format_to_use,
                format=format,
            ):
                audio_data = utils.text_to_speech(
                    text,
                    model=model,
                    voice=voice,
                    response_format=format_to_use,
                )
                if format != format_to_use:
                    audio_data = utils.convert_audio(
                        BytesIO(audio_data),
                        format_to_use,
                        format,
                    )

                return audio_data

            st.session_state.audio_data = {}
            if st.session_state.get("file_uploader", None) is not None:
                text = st.session_state.file_uploader.getvalue().decode("utf-8")
                file_name = os.path.splitext(st.session_state.file_uploader.name)[0]
                audio_file_name = f"{file_name}_{model}_{voice}.{format}"
                audio_data = text_to_audio(text)
                st.session_state["download_file_name"] = audio_file_name
                st.session_state["download_data"] = audio_data
                st.session_state["download_mime"] = f"audio/{format}"
                st.session_state.audio_data[audio_file_name] = audio_data
            elif st.session_state.get("zip_uploader", None) is not None:
                new_zip_io = BytesIO()
                with ZipFile(st.session_state.zip_uploader, "r") as zip_file:
                    with ZipFile(new_zip_io, "w", ZIP_DEFLATED) as new_zip:
                        for info in zip_file.infolist():
                            with zip_file.open(info) as text_file:
                                text = text_file.read().decode("utf-8")
                                audio_file_name = (
                                    f"{os.path.splitext(info.filename)[0]}.{format}"
                                )
                                audio_data = text_to_audio(text)
                                new_zip.writestr(audio_file_name, audio_data)
                                st.session_state.audio_data[
                                    audio_file_name
                                ] = audio_data
                zip_name = os.path.splitext(st.session_state.zip_uploader.name)[0]
                new_zip_name = f"{zip_name}_{model}_{voice}.zip"
                st.session_state["download_file_name"] = new_zip_name
                st.session_state["download_data"] = new_zip_io.getvalue()
                st.session_state["download_mime"] = "application/zip"


if st.session_state.audio_data:
    for audio_file_name in st.session_state.audio_data:
        st.audio(
            st.session_state.audio_data[audio_file_name],
            format=f"audio/{format}",
            start_time=0,
        )
    st.download_button(
        label=f"Download {st.session_state.download_mime}",
        data=st.session_state.download_data,
        file_name=st.session_state.download_file_name,
        mime=st.session_state.download_mime,
    )
