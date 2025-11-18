from google.cloud import texttospeech
import os

# تنظیم کلید
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-tts-key.json"

client = texttospeech.TextToSpeechClient()

input_text = texttospeech.SynthesisInput(text="سلام، این یک تست صوتی است.")
voice = texttospeech.VoiceSelectionParams(
    language_code="fa-IR",
    name="fa-IR-Standard-A"
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)

try:
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    with open("test_output.mp3", "wb") as f:
        f.write(response.audio_content)
    print("فایل صوتی با موفقیت ساخته شد: test_output.mp3")
except Exception as e:
    print("خطا در TTS:", e)