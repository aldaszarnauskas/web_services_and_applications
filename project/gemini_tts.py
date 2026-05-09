from google import genai
from google.genai import types

client = genai.Client()

def tts(transcript, language_code):

    response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=f"Read this aloud naturally in {language_code}: {transcript}",
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                types.SpeakerVoiceConfig(
                    speaker='Dr. Anya',
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Kore',
                        )
                    )
                ),
                ]
            )
        )
    )
    )