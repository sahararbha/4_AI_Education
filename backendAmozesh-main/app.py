
# import os
# from flask import Flask, request, jsonify, send_from_directory
# from flask_cors import CORS
# from dotenv import load_dotenv
# import time
# import mimetypes
# import struct

# # کتابخانه اول: برای تولید صدا (TTS)
# import google.generativeai as genai
# from google.oauth2 import service_account

# # کتابخانه دوم: برای چت (Chat)
# from google.cloud import aiplatform
# import vertexai
# from vertexai.generative_models import GenerativeModel

# # این خط متغیرهای محیطی از فایل .env را بارگذاری می‌کند
# load_dotenv()

# # --- یک چک نهایی برای اطمینان ---
# print(f"--- Running with google-generativeai version: {genai.__version__} ---")

# # --- مسیرهای ذخیره‌سازی فایل صوتی ---
# TTS_STORAGE_PATH = r"E:\8888\AI_Education\FrontAmozesh-master\my-app\src\assets\tts_audio"
# TTS_PUBLIC_URL_BASE = "/assets/tts_audio"
# PLACEHOLDER_FILE_NAME = "placeholder-tts.mp3"

# # --- کلید API (فقط برای مدل چت استفاده می‌شود) ---
# GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
# if not GEMINI_API_KEY:
#     raise ValueError("GEMINI_API_KEY is not set in .env file.")

# # اطمینان از وجود پوشه ذخیره‌سازی
# os.makedirs(TTS_STORAGE_PATH, exist_ok=True)
# print(f"INFO: TTS storage path verified: {TTS_STORAGE_PATH}")

# app = Flask(__name__)
# CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# # --- نام مدل‌ها ---
# MODEL_NAME_CHAT = "gemini-1.5-pro-001" # نام مدل برای Vertex AI کمی متفاوت است
# MODEL_NAME_TTS = "models/tts-1"


# # =========================================================================
# # ↓↓↓ توابع کمکی (بدون تغییر) ↓↓↓
# # =========================================================================
# def save_binary_file(file_name, data):
#     with open(file_name, "wb") as f:
#         f.write(data)
#     print(f"INFO: Successfully generated and SAVED TTS to: {file_name}")

# def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
#     parameters = parse_audio_mime_type(mime_type)
#     bits_per_sample = parameters["bits_per_sample"]
#     sample_rate = parameters["rate"]
#     num_channels = 1
#     data_size = len(audio_data)
#     bytes_per_sample = bits_per_sample // 8
#     block_align = num_channels * bytes_per_sample
#     byte_rate = sample_rate * block_align
#     chunk_size = 36 + data_size
#     header = struct.pack(
#         "<4sI4s4sIHHIIHH4sI",
#         b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
#         num_channels, sample_rate, byte_rate, block_align,
#         bits_per_sample, b"data", data_size
#     )
#     return header + audio_data

# def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
#     bits_per_sample = 16
#     rate = 24000
#     parts = mime_type.split(";")
#     for param in parts:
#         param = param.strip()
#         if param.lower().startswith("rate="):
#             try:
#                 rate = int(param.split("=", 1)[1])
#             except (ValueError, IndexError):
#                 pass
#         elif param.startswith("audio/L"):
#             try:
#                 bits_per_sample = int(param.split("L", 1)[1])
#             except (ValueError, IndexError):
#                 pass
#     return {"bits_per_sample": bits_per_sample, "rate": rate}
# # =========================================================================


# # =========================================================================
# # ↓↓↓ تابع اصلی تولید صدا (با کتابخانه genai) ↓↓↓
# # =========================================================================
# def generate_tts_audio(text_to_read: str) -> str:
#     try:
#         credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
#         if not credentials_path:
#             raise ValueError("GOOGLE_APPLICATION_CREDENTIALS path is not set in .env file.")
#         credentials = service_account.Credentials.from_service_account_file(credentials_path)

#         # کتابخانه را فقط برای این کار با فایل کلید پیکربندی می‌کنیم
#         genai.configure(credentials=credentials)
        
#         tts_model = genai.GenerativeModel(model_name=MODEL_NAME_TTS)

#         print(f"DEBUG: Sending text to Gemini TTS using configured credentials: '{text_to_read[:50]}...'")
        
#         response = tts_model.generate_content(
#             f"Read this text aloud in Persian: {text_to_read}",
#             stream=True
#         )

#         audio_buffer = b""
#         for chunk in response:
#             if chunk.audio_content:
#                 audio_buffer += chunk.audio_content

#         if not audio_buffer:
#             raise ValueError("No audio data received from Gemini. The response was empty.")

#         timestamp = int(time.time() * 1000)
#         filename = f"response_{timestamp}.wav"
#         full_save_path = os.path.join(TTS_STORAGE_PATH, filename)
        
#         wav_data = convert_to_wav(audio_buffer, "audio/L16;rate=24000")
#         save_binary_file(full_save_path, wav_data)
        
#         tts_public_url = f"{TTS_PUBLIC_URL_BASE}/{filename}"
#         return tts_public_url

#     except Exception as e:
#         print(f"FATAL ERROR: Gemini TTS failed. Error: {e}")
#         return f"{TTS_PUBLIC_URL_BASE}/{PLACEHOLDER_FILE_NAME}"

# # --- روت‌های Flask ---
# @app.route('/api/gemini-tts-start', methods=['POST'])
# def gemini_tts_start():
#     text_to_read = request.json.get('text_to_read')
#     if not text_to_read: return jsonify({'error': 'No text provided'}), 400
#     tts_url = generate_tts_audio(text_to_read)
#     return jsonify({'tts_url': tts_url})

# @app.route('/api/gemini-query', methods=['POST'])
# def gemini_query():
#     data = request.json
#     user_prompt = data.get('prompt')
#     if not user_prompt: return jsonify({'response': 'لطفاً سؤال خود را وارد کنید.'}), 400
    
#     try:
#         # با استفاده از کتابخانه Vertex AI، چت را انجام می‌دهیم
#         # این کتابخانه به صورت خودکار از فایل کلید شما استفاده می‌کند و نیازی به API Key نیست
#         project_id = "round-tome-472917-e4" # project_id از فایل gcp-tts-key.json
#         location = "us-central1" # یک منطقه استاندارد برای مدل‌های Gemini
#         vertexai.init(project=project_id, location=location)
        
#         model_chat = GenerativeModel(MODEL_NAME_CHAT)
        
#         response = model_chat.generate_content(user_prompt)
#         ai_response = response.text
        
#         # تولید صدا برای پاسخ چت (این تابع از کتابخانه دیگر استفاده می‌کند)
#         tts_url = generate_tts_audio(ai_response)
#         return jsonify({'response': ai_response, 'tts_url': tts_url})
#     except Exception as e:
#         print(f"ERROR: API Error: {e}")
#         return jsonify({'response': 'خطای سرویس AI: لطفاً دوباره تلاش کنید.'}), 500

# @app.route(f'{TTS_PUBLIC_URL_BASE}/<filename>')
# def serve_tts_audio(filename):
#     return send_from_directory(TTS_STORAGE_PATH, filename)

# @app.route('/api/whisper-stt', methods=['POST'])
# def whisper_stt():
#     print("WARNING: STT service is disabled.")
#     return jsonify({'error': 'سرویس تبدیل صدا به متن در حال حاضر غیرفعال است.'}), 503

# if __name__ == '__main__':
#     print("----------------------------------------------------------------")
#     print("Flask Server running at http://127.0.0.1:5000")
#     print(">> AI Chat & Audio (TTS) powered by Google Gemini (Correct Libraries).")
#     print("----------------------------------------------------------------")
#     app.run(debug=True, port=5000)





import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import time
import struct

# کتابخانه‌های مورد نیاز گوگل
import google.generativeai as genai

# این خط متغیرهای محیطی از فایل .env را بارگذاری می‌کند
load_dotenv()

# --- یک چک نهایی برای اطمینان ---
print(f"--- Running with google-generativeai version: {genai.__version__} ---")

# --- مسیرهای ذخیره‌سازی فایل صوتی ---
TTS_STORAGE_PATH = r"E:\8888\AI_Education\FrontAmozesh-master\my-app\src\assets\tts_audio"
TTS_PUBLIC_URL_BASE = "/assets/tts_audio"
PLACEHOLDER_FILE_NAME = "placeholder-tts.mp3"

# --- کلید API ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env file.")

# پیکربندی سراسری کتابخانه با کلید API
genai.configure(api_key=GEMINI_API_KEY)

# اطمینان از وجود پوشه ذخیره‌سازی
os.makedirs(TTS_STORAGE_PATH, exist_ok=True)
print(f"INFO: TTS storage path verified: {TTS_STORAGE_PATH}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# --- نام مدل‌ها ---
MODEL_NAME_CHAT = "gemini-2.5-pro-preview-tts"
# =======================> شروع تغییر نهایی <=======================
# از جدیدترین مدل که قابلیت تولید صدای داخلی دارد، استفاده می‌کنیم
MODEL_NAME_TTS = "gemini-2.5-pro-preview-tts"
# =======================> پایان تغییر نهایی <=======================


# =========================================================================
# ↓↓↓ توابع کمکی برای تبدیل صدای خام به فایل WAV ↓↓↓
# =========================================================================
def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"INFO: Successfully generated and SAVED TTS to: {file_name}")

def convert_to_wav(audio_data: bytes, sample_rate: int = 24000) -> bytes:
    bits_per_sample = 16
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
        num_channels, sample_rate, byte_rate, block_align,
        bits_per_sample, b"data", data_size
    )
    return header + audio_data
# =========================================================================


# =========================================================================
# ↓↓↓ تابع اصلی تولید صدا (با مدل صحیح) ↓↓↓
# =========================================================================
def generate_tts_audio(text_to_read: str) -> str:
    try:
        # 1. مدل صحیح را مقداردهی کن
        tts_model = genai.GenerativeModel(MODEL_NAME_TTS)

        print(f"DEBUG: Sending text to the correct model ({MODEL_NAME_TTS}): '{text_to_read[:50]}...'")
        
        # 2. درخواست تولید محتوا را ارسال کن.
        # مدل به صورت هوشمند تشخیص می‌دهد که خروجی باید صوتی باشد.
        response = tts_model.generate_content(
            f"Read this text aloud in Persian: {text_to_read}",
            stream=True
        )

        # 3. جمع‌آوری داده‌های صوتی خام (PCM) از استریم
        audio_buffer = b""
        for chunk in response:
            if chunk.audio_content:
                audio_buffer += chunk.audio_content

        if not audio_buffer:
            raise ValueError("No audio data received from Gemini. The response was empty.")

        # 4. داده‌های صوتی خام را به یک فایل WAV قابل پخش تبدیل و ذخیره کن
        timestamp = int(time.time() * 1000)
        filename = f"response_{timestamp}.wav"
        full_save_path = os.path.join(TTS_STORAGE_PATH, filename)
        
        wav_data = convert_to_wav(audio_buffer)
        save_binary_file(full_save_path, wav_data)
        
        tts_public_url = f"{TTS_PUBLIC_URL_BASE}/{filename}"
        return tts_public_url

    except Exception as e:
        print(f"FATAL ERROR: Gemini TTS failed. Error: {e}")
        return f"{TTS_PUBLIC_URL_BASE}/{PLACEHOLDER_FILE_NAME}"

# --- روت‌های Flask (بدون تغییر) ---
@app.route('/api/gemini-tts-start', methods=['POST'])
def gemini_tts_start():
    text_to_read = request.json.get('text_to_read')
    if not text_to_read: return jsonify({'error': 'No text provided'}), 400
    tts_url = generate_tts_audio(text_to_read)
    return jsonify({'tts_url': tts_url})

@app.route('/api/gemini-query', methods=['POST'])
def gemini_query():
    data = request.json
    user_prompt = data.get('prompt')
    if not user_prompt: return jsonify({'response': 'لطفاً سؤال خود را وارد کنید.'}), 400
    
    try:
        model_chat = genai.GenerativeModel(MODEL_NAME_CHAT)
        response = model_chat.generate_content(user_prompt)
        ai_response = response.text
        
        tts_url = generate_tts_audio(ai_response)
        return jsonify({'response': ai_response, 'tts_url': tts_url})
    except Exception as e:
        print(f"ERROR: API Error: {e}")
        return jsonify({'response': 'خطای سرویس AI: لطفاً دوباره تلاش کنید.'}), 500

@app.route(f'{TTS_PUBLIC_URL_BASE}/<filename>')
def serve_tts_audio(filename):
    return send_from_directory(TTS_STORAGE_PATH, filename)

if __name__ == '__main__':
    print("----------------------------------------------------------------")
    print("Flask Server running at http://127.0.0.1:5000")
    print(">> AI Chat & Audio (TTS) powered by Google Gemini (Final Correct Model).")
    print("----------------------------------------------------------------")
    app.run(debug=True, port=5000)

