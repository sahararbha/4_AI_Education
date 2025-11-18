# import os
# import psycopg2
# from dotenv import load_dotenv

# # --- بارگذاری متغیرهای محیطی فقط برای اطلاعات دیتابیس ---
# load_dotenv()

# # --- اطلاعات اتصال به پایگاه داده ---
# DB_NAME = os.getenv("POSTGRES_DB")
# DB_USER = os.getenv("POSTGRES_USER")
# DB_PASS = os.getenv("POSTGRES_PASSWORD")
# DB_HOST = "localhost"
# DB_PORT = "5432"

# # --- تابع درج اطلاعات در پایگاه داده (دقیقاً همان تابع قبلی) ---
# def insert_user_into_db(user_info):
#     conn = None
#     try:
#         print("ربات تست: در حال اتصال به پایگاه داده...")
#         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
#         cur = conn.cursor()
#         print("ربات تست: اتصال به پایگاه داده موفق بود.")
        
#         username = user_info['email'].split('@')[0]
#         password_hash = "test_password_hash"
        
#         insert_query = "INSERT INTO Users (username, password_hash, email, first_name, last_name) VALUES (%s, %s, %s, %s, %s)"
#         cur.execute(insert_query, (username, password_hash, user_info['email'], user_info['first_name'], user_info['last_name']))
        
#         conn.commit()
#         cur.close()
#         print(f"ربات تست: کاربر '{user_info['first_name']}' با موفقیت در پایگاه داده ثبت شد.")
#         return True
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(f"خطا در عملیات پایگاه داده: {error}")
#         return False
#     finally:
#         if conn is not None:
#             conn.close()

# # --- اجرای اصلی برنامه تست ---
# def main_test():
#     print("--- شروع تست درج اطلاعات در دیتابیس ---")
    
#     # 1. ساخت اطلاعات یک کاربر فرضی (اینجا نقش هوش مصنوعی را شبیه‌سازی می‌کنیم)
#     fake_user_data = {
#         "first_name": "آزمایش",
#         "last_name": "تستی",
#         "email": "test.user@example.com"
#     }
#     print(f"اطلاعات فرضی ساخته شد: {fake_user_data}")

#     # 2. فراخوانی تابع برای درج این اطلاعات در دیتابیس
#     insert_user_into_db(fake_user_data)
    
#     print("--- پایان تست ---")

# if __name__ == "__main__":
#     main_test()









import os
import psycopg2
import json
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from dotenv import load_dotenv
from openai import OpenAI
import pygame
import time
import uuid
from collections import deque
import re

# --- بخش 1: تنظیمات اولیه ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT = os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_USER"), os.getenv("POSTGRES_PASSWORD"), "localhost", "5432"

# --- بخش 2: کلاس VADAudioHandler با قابلیت کالیبراسیون ---

class VADAudioHandler:
    def __init__(self, silence_threshold=40, silence_duration=1.2):
        self.SILENCE_THRESHOLD = silence_threshold
        self.SILENCE_DURATION = silence_duration
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = int(self.SAMPLE_RATE / 10)
        self.audio_queue = deque()
        self.is_speaking = False
        self.silent_chunks = 0
        self.required_silent_chunks = int(self.SILENCE_DURATION * 10)
        self.stream = None
        self.calibrated_energy_threshold = 100

    def calibrate(self, duration=2):
        speak("برای تنظیم حساسیت میکروفون، لطفاً برای چند لحظه سکوت کنید...")
        print("--- شروع کالیبراسیون ---")
        energies = []
        def calibration_callback(indata, frames, time, status):
            energies.append(np.linalg.norm(indata) * 10)
        stream = sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1, dtype='int16', blocksize=self.CHUNK_SIZE, callback=calibration_callback)
        with stream:
            time.sleep(duration)
        if energies:
            average_noise = np.mean(energies)
            self.calibrated_energy_threshold = average_noise * 1.8 + 30
        print(f"--- کالیبراسیون تمام شد. آستانه انرژی جدید: {self.calibrated_energy_threshold:.2f} ---")
        speak("متشکرم. تنظیمات انجام شد.")

    def _reset_state(self):
        self.audio_queue.clear()
        self.is_speaking = False
        self.silent_chunks = 0

    def _audio_callback(self, indata, frames, time, status):
        energy = np.linalg.norm(indata) * 10
        if self.is_speaking:
            self.audio_queue.append(indata.copy())
            self.silent_chunks = self.silent_chunks + 1 if energy < self.SILENCE_THRESHOLD else 0
            if self.silent_chunks > self.required_silent_chunks:
                self.is_speaking = False
        elif energy > self.calibrated_energy_threshold:
            print("\n--- کاربر شروع به صحبت کرد! ---")
            self.is_speaking = True
            self.silent_chunks = 0
            self.audio_queue.clear()
            self.audio_queue.append(indata.copy())

    def listen_for_interruption(self):
        # این تابع دیگر به صورت مستقیم استفاده نمی‌شود، منطق آن در speak ادغام شده
        pass

    def listen_and_transcribe(self, context_prompt="", timeout=7.0):
        self._reset_state()
        print("ربات: در حال گوش دادن...")
        self.stream = sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1, dtype='int16', blocksize=self.CHUNK_SIZE, callback=self._audio_callback)
        with self.stream:
            start_time = time.time()
            while not self.is_speaking and time.time() - start_time < timeout: time.sleep(0.1)
            if self.is_speaking:
                while self.is_speaking and time.time() - start_time < timeout: time.sleep(0.1)
        print("\n--- گوش دادن متوقف شد. ---")
        if not self.audio_queue: return None
        recording = np.concatenate(list(self.audio_queue))
        temp_audio_file = f"temp_vad_audio_{uuid.uuid4()}.wav"
        write(temp_audio_file, self.SAMPLE_RATE, recording)
        try:
            with open(temp_audio_file, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="fa", prompt=context_prompt)
            return transcription.text.strip()
        finally:
            os.remove(temp_audio_file)

# --- بخش 3: تمام توابع کمکی برنامه ---

def speak(text, audio_handler=None, interruptible=False):
    user_interrupted_text = None
    sentences = re.split(r'(?<=[.!?])\s+', text)
    pygame.init()
    pygame.mixer.init()

    # --- تغییر کلیدی: استریم میکروفون فقط یک بار برای کل صحبت باز می‌شود ---
    if interruptible and audio_handler:
        audio_handler._reset_state()
        stream = sd.InputStream(samplerate=audio_handler.SAMPLE_RATE, channels=1, dtype='int16', blocksize=audio_handler.CHUNK_SIZE, callback=audio_handler._audio_callback)
        stream.start()

    for sentence in sentences:
        if not sentence: continue
        speech_file = f"temp_speech_{uuid.uuid4()}.mp3"
        try:
            print(f"ربات (در حال صحبت): {sentence}")
            response = client.audio.speech.create(model="tts-1", voice="nova", input=sentence)
            response.stream_to_file(speech_file)
            pygame.mixer.music.load(speech_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                # --- حلقه بسیار سریع برای حداکثر حساسیت ---
                if interruptible and audio_handler and audio_handler.is_speaking:
                    pygame.mixer.music.stop()
                    print("\n--- صحبت ربات قطع شد! ---")
                    # حالا منتظر بمان تا صحبت کاربر تمام شود
                    start_wait = time.time()
                    while audio_handler.is_speaking and time.time() - start_wait < 7.0:
                        time.sleep(0.1)
                    user_interrupted_text = "INTERRUPTED" # یک سیگنال که قطع شده
                    break
                time.sleep(0.01) # <-- زمان انتظار بسیار کوتاه
        finally:
            if pygame.mixer.get_init():
                while pygame.mixer.music.get_busy(): time.sleep(0.1)
            if os.path.exists(speech_file):
                try: os.remove(speech_file)
                except Exception: pass
        if user_interrupted_text: break
    
    # --- استریم میکروفون در انتها بسته می‌شود ---
    if interruptible and audio_handler and 'stream' in locals() and stream.active:
        stream.stop()
        stream.close()

    pygame.quit()

    # اگر قطع شده بود، حالا صدای ضبط شده را پردازش کن
    if user_interrupted_text == "INTERRUPTED":
        print("\n--- پردازش صدای ضبط شده کاربر ---")
        if not audio_handler.audio_queue: return None
        recording = np.concatenate(list(audio_handler.audio_queue))
        temp_audio_file = f"temp_interrupt_audio_{uuid.uuid4()}.wav"
        write(temp_audio_file, audio_handler.SAMPLE_RATE, recording)
        try:
            with open(temp_audio_file, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="fa", prompt="توضیح بده. سوال دارم.")
            return transcription.text.strip()
        finally:
            os.remove(temp_audio_file)
            
    return None

def find_user_by_fuzzy_name(transcribed_text):
    """کاربر را در دیتابیس پیدا می‌کند."""
    conn = None
    try:
        replacements = {'ي': 'ی', 'ك': 'ک'}
        normalized_text = transcribed_text
        for char, replacement in replacements.items():
            normalized_text = normalized_text.replace(char, replacement)
        
        ignore_words = ['اسم', 'من', 'هست', 'هستم', 'است', 'نام', 'نامم']
        clean_text = ''.join(c for c in normalized_text if c not in '''!()-[]{};:'"\,<>./?@#$%^&*_~.''')
        words = clean_text.strip().split()
        name_keywords = [word for word in words if word.lower() not in ignore_words and word.strip()]
        if not name_keywords: return None
        
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        base_query = "SELECT user_id, first_name FROM Users WHERE "
        conditions = " OR ".join(["LOWER(CONCAT(first_name, ' ', last_name)) LIKE %s" for _ in name_keywords])
        search_patterns = [f'%{keyword.lower()}%' for keyword in name_keywords]
        cur.execute(f"({base_query} {conditions}) LIMIT 1;", search_patterns)
        result = cur.fetchone()
        cur.close()
        if result:
            return {'user_id': result[0], 'first_name': result[1]}
        return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"خطا در جستجوی کاربر: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()

def get_enrolled_course_info(user_id):
    """اطلاعات درس کاربر را برمی‌گرداند."""
    conn = None
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        query = "SELECT C.title, C.pdf_file_path FROM Enrollments E JOIN Courses C ON E.course_id = C.course_id WHERE E.user_id = %s LIMIT 1;"
        cur.execute(query, (user_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            return {'title': result[0], 'pdf_path': result[1]}
        return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"خطا در یافتن درس کاربر: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()

def load_lesson_from_json(pdf_path):
    """درس را از فایل JSON بارگذاری می‌کند."""
    try:
        file_name = os.path.basename(pdf_path).replace('.pdf', '.json')
        json_path = os.path.join('lessons', file_name)
        with open(json_path, 'r', encoding='utf-8') as f:
            lesson_content = json.load(f)
        print(f"ربات: درس '{lesson_content['course_title']}' با موفقیت بارگذاری شد.")
        return lesson_content
    except Exception as e:
        speak(f"خطا در بارگذاری فایل درس: {e}", VADAudioHandler())
        return None

def is_confirmation(text):
    """تشخیص می‌دهد آیا پاسخ کاربر مثبت است یا خیر."""
    text = text.lower().strip().replace('.', '')
    replacements = {'ي': 'ی', 'ك': 'ک', '\u200c': ' '}
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    positive_keywords = ["بله", "آره", "آری", "حتما", "موافقم", "شروع کن", "آماده ام", "آمادم", "باشه", "باید"]
    negative_keywords = ["نه", "نخیر", "فعلا نه", "آماده نیستم", "مخالفم"]
    if any(keyword in text for keyword in negative_keywords):
        return False
    if any(keyword in text for keyword in positive_keywords):
        return True
    return False

def recognize_command(text):
    """قصد کاربر را از متن تشخیص می‌دهد."""
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in ["تکرار کن", "دوباره بگو", "متوجه نشدم"]):
        return "REPEAT_CHUNK"
    if any(keyword in text_lower for keyword in ["ادامه بده", "بعدی", "برو", "سوالی ندارم"]):
        return "CONTINUE_LESSON"
    return "USER_QUESTION"

def handle_user_question(question, lesson_content, current_chunk_index, audio_handler):
    """به سوال کاربر با تشخیص موضوعات آینده پاسخ می‌دهد."""
    try:
        future_chunks = [chunk for chunk in lesson_content['chunks'] if chunk['chunk_id'] > current_chunk_index + 1]
        if future_chunks:
            future_keywords = [kw for chunk in future_chunks for kw in chunk.get('keywords', [])]
            prompt_check_future = f"سوال کاربر: '{question}'. لیست کلمات کلیدی آینده: {json.dumps(future_keywords, ensure_ascii=False)}. آیا سوال به این موضوعات آینده مرتبط است؟ پاسخ فقط JSON: {{\"is_future_topic\": true}} یا {{\"is_future_topic\": false}}"
            response = client.chat.completions.create(model="gpt-4o", response_format={"type": "json_object"}, messages=[{"role": "user", "content": prompt_check_future}])
            analysis = json.loads(response.choices[0].message.content)
            if analysis.get("is_future_topic", False):
                speak("سوال خوبی پرسیدی! هنوز به این مبحث نرسیدیم. لطفاً تامل بفرمایید.", audio_handler)
                return

        known_context = " ".join([f"موضوع: {chunk['title']}. محتوا: {chunk['content']}" for chunk in lesson_content['chunks'] if chunk['chunk_id'] <= current_chunk_index + 1])
        prompt_answer = f"شما یک مدرس هستید. با توجه به این اطلاعات: '{known_context}'. به این سوال پاسخ بده: '{question}'."
        answer_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_answer}])
        answer = answer_response.choices[0].message.content
        speak(answer, audio_handler, interruptible=True)
    except Exception as e:
        print(f"خطا در پردازش سوال کاربر: {e}")
        speak("متاسفانه در پردازش سوال شما خطایی رخ داد.", audio_handler)
# --- بخش 4: تابع اصلی برنامه ---

def main():
    audio_handler = VADAudioHandler()
    audio_handler.calibrate()
    
    # (کد کامل و واقعی شناسایی کاربر و بارگذاری درس از پاسخ قبلی)
    # ...
    
    # مرحله 3: شروع حلقه تدریس
    session_state = {'current_chunk_index': 0}
    speak(f"عالیه! پس درس «{lesson['course_title']}» را شروع می‌کنیم. هر زمان سوالی داشتی، می‌توانی صحبت من را قطع کنی.", audio_handler)

    while session_state['current_chunk_index'] < len(lesson['chunks']):
        current_chunk = lesson['chunks'][session_state['current_chunk_index']]
        
        prompt = f"موضوع زیر را به زبان ساده توضیح بده: {current_chunk['title']} - {current_chunk['content']}"
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        teaching_text = response.choices[0].message.content
        
        user_input = speak(teaching_text, audio_handler, interruptible=True)
        
        if user_input:
            handle_user_question(user_input, lesson, session_state['current_chunk_index'], audio_handler)
            speak("بسیار خب، برگردیم به درسی که در حال توضیح آن بودم.", audio_handler)
            continue
        
        # (کد حلقه پرسش و پاسخ انتهای بخش از پاسخ قبلی)
        # ...
        
        session_state['current_chunk_index'] += 1

    speak("این درس به پایان رسید. موفق باشی.", audio_handler)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nبرنامه در حال بسته شدن...")
    except Exception as e:
        print(f"\nیک خطای بحرانی رخ داد: {e}")