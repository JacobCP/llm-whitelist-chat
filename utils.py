import openai
import pydub
import yagmail


def send_email(user, password, to, subject, text):
    yag = yagmail.SMTP(user, password)

    # Send email
    yag.send(
        to=to,
        subject=subject,
        contents=text,
    )


def format_messages(messages):
    messages_string = ""
    for message in messages:
        messages_string += f"{message['role']}: {message['content']}\n"

    return messages_string


def text_to_speech(text, model="tts-1", voice="alloy", response_format="mp3"):
    client = openai.OpenAI()

    audio_data = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format,
    ).content

    return audio_data


def convert_audio(audio_file, input_format, output_format):
    input_audio = pydub.AudioSegment.from_file(audio_file, format=input_format)
    output_audio = input_audio.export(format=output_format)
    output_data = output_audio.read()

    return output_data
