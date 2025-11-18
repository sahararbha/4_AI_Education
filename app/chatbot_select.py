# import os
# import psycopg2
# import json
# import sounddevice as sd
# import numpy as np
# from scipy.io.wavfile import write
# from dotenv import load_dotenv
# from openai import OpenAI
# import pygame
# import time
# import uuid
# from collections import deque
# import re

# # --- بخش 1: تنظیمات اولیه ---
# # متغیرهای محیطی در ابتدای برنامه بارگذاری می‌شوند
# load_dotenv()
# DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT = os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_USER"), os.getenv("POSTGRES_PASSWORD"), "localhost", "5432"

# # --- بخش 2: کلاس VADAudioHandler با معماری تزریق وابستگی ---

# class VADAudioHandler:
#     def __init__(self, client, silence_energy_threshold=50, silence_duration=1.2):
#         # client به عنوان وابستگی به کلاس تزریق می‌شود
#         self.client = client
#         self.SILENCE_ENERGY_THRESHOLD = silence_energy_threshold
#         self.SILENCE_DURATION = silence_duration
#         self.SAMPLE_RATE = 16000
#         self.CHUNK_SIZE = int(self.SAMPLE_RATE / 10)
#         self.audio_queue = deque()
#         self.is_speaking = False
#         self.silent_chunks = 0
#         self.required_silent_chunks = int(self.SILENCE_DURATION * (self.SAMPLE_RATE / self.CHUNK_SIZE))
#         self.stream = None
#         self.speech_start_energy_threshold = 500
#         self.energy_buffer = deque(maxlen=3)
#         self.MIN_SPEECH_CHUNKS = 2

#     def calibrate(self, duration=2):
#         print("ربات (کالیبراسیون): برای تنظیم حساسیت میکروفون، لطفاً برای چند لحظه سکوت کنید...")
#         print("--- شروع کالیبراسیون ---")
        
#         energies = []
#         print("در حال ضبط نویز محیط...")
#         calibration_recording = sd.rec(int(duration * self.SAMPLE_RATE), samplerate=self.SAMPLE_RATE, channels=1, dtype='int16')
#         sd.wait()
        
#         num_chunks = len(calibration_recording) // self.CHUNK_SIZE
#         for i in range(num_chunks):
#             chunk = calibration_recording[i*self.CHUNK_SIZE:(i+1)*self.CHUNK_SIZE]
#             energies.append(np.linalg.norm(chunk))

#         if energies:
#             average_noise = np.mean(energies)
#             print(f"میانگین انرژی نویز محیط محاسبه شد: {average_noise:.2f}")
#             self.speech_start_energy_threshold = (average_noise * 5.0) + 300
#         else:
#             self.speech_start_energy_threshold = 500

#         print(f"--- کالیبراسیون تمام شد. آستانه انرژی برای شروع صحبت: {self.speech_start_energy_threshold:.2f} ---")
#         print("ربات (کالیبراسیون): متشکرم. تنظیمات انجام شد.")

#     def _reset_state(self):
#         self.audio_queue.clear()
#         self.is_speaking = False
#         self.silent_chunks = 0
#         self.energy_buffer.clear()

#     def _audio_callback(self, indata, frames, time, status):
#         if status:
#             print(f"خطای استریم صدا: {status}")
#             return
#         energy = np.linalg.norm(indata)
#         if not self.is_speaking:
#             self.energy_buffer.append(indata.copy()) # کپی کردن داده برای صف
#             energetic_chunks_count = sum(1 for e in self.energy_buffer if np.linalg.norm(e) > self.speech_start_energy_threshold)
#             if energetic_chunks_count >= self.MIN_SPEECH_CHUNKS:
#                 print(f"\n--- الگوی صحبت پایدار شناسایی شد! (انرژی: {np.linalg.norm(self.energy_buffer[-1]):.2f}) ---")
#                 self.is_speaking = True
#                 self.silent_chunks = 0
#                 self.audio_queue.clear()
#                 self.audio_queue.extend(self.energy_buffer)
#             return
#         if self.is_speaking:
#             self.audio_queue.append(indata.copy())
#             if energy < self.SILENCE_ENERGY_THRESHOLD:
#                 self.silent_chunks += 1
#                 if self.silent_chunks > self.required_silent_chunks:
#                     self.is_speaking = False
#             else:
#                 self.silent_chunks = 0
    
#     def listen_and_transcribe(self, context_prompt="", timeout=7.0):
#         self._reset_state()
#         print("ربات: در حال گوش دادن به دستور/سوال شما...")
#         self.stream = sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1, dtype='int16', blocksize=self.CHUNK_SIZE, callback=self._audio_callback)
#         with self.stream:
#             start_time = time.time()
#             while not self.is_speaking and time.time() - start_time < timeout:
#                 time.sleep(0.1)
#             if self.is_speaking:
#                 while self.is_speaking and time.time() - start_time < timeout:
#                     time.sleep(0.1)
#         print("\n--- گوش دادن متوقف شد. ---")
#         if not self.audio_queue:
#             print("ربات: صدایی شناسایی نشد.")
#             return None
#         recording = np.concatenate(list(self.audio_queue))
#         temp_audio_file = f"temp_vad_audio_{uuid.uuid4()}.wav"
#         write(temp_audio_file, self.SAMPLE_RATE, recording)
#         try:
#             with open(temp_audio_file, "rb") as audio_file:
#                 transcription = self.client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="fa", prompt=context_prompt)
#             transcribed_text = transcription.text.strip()
#             if transcribed_text:
#                 print(f"ربات: متن شناسایی شده: '{transcribed_text}'")
#                 return transcribed_text
#             else:
#                 print("ربات: متنی شناسایی نشد.")
#                 return ""
#         except Exception as e:
#             print(f"خطا در تبدیل صدا: {e}")
#             return None
#         finally:
#             if os.path.exists(temp_audio_file):
#                 os.remove(temp_audio_file)

# # --- بخش 3: تمام توابع کمکی برنامه ---

# def speak(text, client, audio_handler=None, interruptible=False):
#     user_interrupted_text = None
#     sentences = re.split(r'(?<=[.!?])\s+', text)
#     pygame.init()
#     pygame.mixer.init()
#     stream = None
#     for sentence in sentences:
#         if not sentence.strip(): continue
#         if user_interrupted_text: break
#         speech_file = f"temp_speech_{uuid.uuid4()}.mp3"
#         try:
#             print(f"ربات (در حال صحبت): {sentence}")
#             response = client.audio.speech.create(model="tts-1", voice="nova", input=sentence)
#             response.stream_to_file(speech_file)
#             pygame.mixer.music.load(speech_file)
#             if interruptible and audio_handler:
#                 audio_handler._reset_state()
#                 stream = sd.InputStream(samplerate=audio_handler.SAMPLE_RATE, channels=1, dtype='int16', blocksize=audio_handler.CHUNK_SIZE, callback=audio_handler._audio_callback)
#                 stream.start()
#                 print("--- حالت وقفه فعال شد. در حال گوش دادن به کاربر... ---")
#             pygame.mixer.music.play()
#             while pygame.mixer.music.get_busy():
#                 if interruptible and audio_handler and audio_handler.is_speaking:
#                     pygame.mixer.music.stop()
#                     print("\n--- صحبت ربات توسط کاربر قطع شد! ---")
#                     start_wait = time.time()
#                     while audio_handler.is_speaking and time.time() - start_wait < 7.0:
#                         time.sleep(0.1)
#                     user_interrupted_text = "INTERRUPTED"
#                     break
#                 time.sleep(0.01)
#         finally:
#             if stream and stream.active:
#                 stream.stop(); stream.close(); stream = None
#                 print("--- حالت وقفه غیرفعال شد. ---")
#             if pygame.mixer.get_init():
#                 pygame.mixer.music.unload()
#             if os.path.exists(speech_file):
#                 try: os.remove(speech_file)
#                 except Exception as e: print(f"خطا در حذف فایل موقت صوتی: {e}")
#         if user_interrupted_text: break
#     if user_interrupted_text == "INTERRUPTED":
#         print("\n--- پردازش صدای ضبط شده کاربر پس از وقفه ---")
#         if not audio_handler or not audio_handler.audio_queue:
#             pygame.quit(); return None
#         recording = np.concatenate(list(audio_handler.audio_queue))
#         temp_audio_file = f"temp_interrupt_audio_{uuid.uuid4()}.wav"
#         write(temp_audio_file, audio_handler.SAMPLE_RATE, recording)
#         transcribed_text = None
#         try:
#             with open(temp_audio_file, "rb") as audio_file:
#                 transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="fa", prompt="توضیح بده. سوال دارم.")
#             transcribed_text = transcription.text.strip()
#             print(f"ربات: متن شناسایی شده از وقفه: '{transcribed_text}'")
#         except Exception as e: print(f"خطا در تبدیل صدای وقفه: {e}")
#         finally:
#             if os.path.exists(temp_audio_file): os.remove(temp_audio_file)
#         pygame.quit()
#         return transcribed_text
#     pygame.quit()
#     return None

# def find_user_by_fuzzy_name(transcribed_text):
#     # این تابع به client نیازی ندارد
#     conn = None
#     try:
#         # ... (کد داخلی این تابع بدون تغییر باقی می‌ماند)
#         replacements = {'ي': 'ی', 'ك': 'ک'}
#         normalized_text = transcribed_text
#         for char, replacement in replacements.items():
#             normalized_text = normalized_text.replace(char, replacement)
#         ignore_words = ['اسم', 'من', 'هست', 'هستم', 'است', 'نام', 'نامم']
#         clean_text = ''.join(c for c in normalized_text if c not in '''!()-[]{};:'"\,<>./?@#$%^&*_~.''')
#         words = clean_text.strip().split()
#         name_keywords = [word for word in words if word.lower() not in ignore_words and word.strip()]
#         if not name_keywords: return None
#         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
#         cur = conn.cursor()
#         base_query = "SELECT user_id, first_name FROM Users WHERE "
#         conditions = " OR ".join(["LOWER(CONCAT(first_name, ' ', last_name)) LIKE %s" for _ in name_keywords])
#         search_patterns = [f'%{keyword.lower()}%' for keyword in name_keywords]
#         cur.execute(f"({base_query} {conditions}) LIMIT 1;", search_patterns)
#         result = cur.fetchone()
#         cur.close()
#         if result: return {'user_id': result[0], 'first_name': result[1]}
#         return None
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(f"خطا در جستجوی کاربر: {error}")
#         return None
#     finally:
#         if conn is not None: conn.close()

# def get_enrolled_course_info(user_id):
#     # این تابع به client نیازی ندارد
#     conn = None
#     try:
#         # ... (کد داخلی این تابع بدون تغییر باقی می‌ماند)
#         conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
#         cur = conn.cursor()
#         query = "SELECT C.title, C.pdf_file_path FROM Enrollments E JOIN Courses C ON E.course_id = C.course_id WHERE E.user_id = %s LIMIT 1;"
#         cur.execute(query, (user_id,))
#         result = cur.fetchone()
#         cur.close()
#         if result: return {'title': result[0], 'pdf_path': result[1]}
#         return None
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(f"خطا در یافتن درس کاربر: {error}")
#         return None
#     finally:
#         if conn is not None: conn.close()

# def load_lesson_from_json(pdf_path, client):
#     try:
#         file_name = os.path.basename(pdf_path).replace('.pdf', '.json')
#         json_path = os.path.join('lessons', file_name)
#         with open(json_path, 'r', encoding='utf-8') as f:
#             lesson_content = json.load(f)
#         print(f"ربات: درس '{lesson_content['course_title']}' با موفقیت بارگذاری شد.")
#         return lesson_content
#     except Exception as e:
#         # در صورت خطا، از client برای صحبت کردن استفاده می‌شود
#         speak(f"خطا در بارگذاری فایل درس: {e}", client)
#         return None

# def is_confirmation(text):
#     # این تابع به client نیازی ندارد
#     text = text.lower().strip().replace('.', '')
#     replacements = {'ي': 'ی', 'ك': 'ک', '\u200c': ' '}
#     for char, replacement in replacements.items():
#         text = text.replace(char, replacement)
#     positive_keywords = ["بله", "آره", "آری", "حتما", "موافقم", "شروع کن", "آماده ام", "آمادم", "باشه", "باید"]
#     negative_keywords = ["نه", "نخیر", "فعلا نه", "آماده نیستم", "مخالفم"]
#     if any(keyword in text for keyword in negative_keywords): return False
#     if any(keyword in text for keyword in positive_keywords): return True
#     return False

# def recognize_command(text):
#     # این تابع به client نیازی ندارد
#     text_lower = text.lower()
#     if any(keyword in text_lower for keyword in ["تکرار کن", "دوباره بگو", "متوجه نشدم"]): return "REPEAT_CHUNK"
#     if any(keyword in text_lower for keyword in ["ادامه بده", "بعدی", "برو", "سوالی ندارم"]): return "CONTINUE_LESSON"
#     return "USER_QUESTION"

# def handle_user_question(question, client, lesson_content, current_chunk_index, audio_handler):
#     try:
#         future_chunks = [chunk for chunk in lesson_content['chunks'] if chunk['chunk_id'] > current_chunk_index + 1]
#         if future_chunks:
#             future_keywords = [kw for chunk in future_chunks for kw in chunk.get('keywords', [])]
#             prompt_check_future = f"سوال کاربر: '{question}'. لیست کلمات کلیدی آینده: {json.dumps(future_keywords, ensure_ascii=False)}. آیا سوال به این موضوعات آینده مرتبط است؟ پاسخ فقط JSON: {{\"is_future_topic\": true}} یا {{\"is_future_topic\": false}}"
#             response = client.chat.completions.create(model="gpt-4o", response_format={"type": "json_object"}, messages=[{"role": "user", "content": prompt_check_future}])
#             analysis = json.loads(response.choices[0].message.content)
#             if analysis.get("is_future_topic", False):
#                 speak("سوال خوبی پرسیدی! هنوز به این مبحث نرسیدیم. لطفاً تامل بفرمایید.", client, audio_handler)
#                 return
#         known_context = " ".join([f"موضوع: {chunk['title']}. محتوا: {chunk['content']}" for chunk in lesson_content['chunks'] if chunk['chunk_id'] <= current_chunk_index + 1])
#         prompt_answer = f"شما یک مدرس هستید. با توجه به این اطلاعات: '{known_context}'. به این سوال پاسخ بده: '{question}'."
#         answer_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_answer}])
#         answer = answer_response.choices[0].message.content
#         speak(answer, client, audio_handler, interruptible=True)
#     except Exception as e:
#         print(f"خطا در پردازش سوال کاربر: {e}")
#         speak("متاسفانه در پردازش سوال شما خطایی رخ داد.", client, audio_handler)

# # --- بخش 4: تابع اصلی برنامه ---

# def main():
#     try:
#         client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#     except Exception as e:
#         print(f"خطا در اتصال به OpenAI: {e}")
#         return

#     audio_handler = VADAudioHandler(client)
#     audio_handler.calibrate()
    
#     speak("سلام، برای شروع لطفاً نام کامل خود را بگویید.", client, audio_handler)
#     user_data = None
#     for _ in range(2):
#         user_name_text = audio_handler.listen_and_transcribe(context_prompt="نام من ... است.")
#         if not user_name_text:
#             speak("متاسفانه صدایی دریافت نکردم. لطفاً دوباره تلاش کنید.", client, audio_handler)
#             continue
#         potential_user = find_user_by_fuzzy_name(user_name_text)
#         if potential_user:
#             speak(f"متوجه شدم، {potential_user['first_name']}. درست است؟", client, audio_handler)
#             confirmation_text = audio_handler.listen_and_transcribe(context_prompt="بله. نه.")
#             if confirmation_text and is_confirmation(confirmation_text):
#                 user_data = potential_user
#                 break
#         speak("متاسفانه نام شما را تشخیص ندادم. لطفاً دوباره بگویید.", client, audio_handler)

#     if not user_data:
#         speak("شناسایی ناموفق بود. برنامه پایان یافت.", client, audio_handler)
#         return

#     course_info = get_enrolled_course_info(user_data['user_id'])
#     if not course_info:
#         speak(f"سلام {user_data['first_name']}. شما هنوز در هیچ درسی ثبت‌نام نکرده‌اید.", client, audio_handler)
#         return
    
#     speak(f"عالیه {user_data['first_name']}. می‌بینم که در درس «{course_info['title']}» ثبت‌نام کرده‌ای. آماده‌ای تا درس را شروع کنیم؟", client, audio_handler)
#     confirmation_text = audio_handler.listen_and_transcribe(context_prompt="بله. آره. آماده ام.")
#     if not confirmation_text or not is_confirmation(confirmation_text):
#          speak("بسیار خب، هر وقت آماده بودی من اینجا هستم.", client, audio_handler)
#          return

#     lesson = load_lesson_from_json(course_info['pdf_path'], client)
#     if not lesson: return

#     session_state = {'current_chunk_index': 0}
#     speak(f"عالیه! پس درس «{lesson['course_title']}» را شروع می‌کنیم. هر زمان سوالی داشتی، می‌توانی صحبت من را قطع کنی.", client, audio_handler)

#     while session_state['current_chunk_index'] < len(lesson['chunks']):
#         current_chunk = lesson['chunks'][session_state['current_chunk_index']]
#         prompt = f"موضوع زیر را به زبان ساده توضیح بده: {current_chunk['title']} - {current_chunk['content']}"
#         response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
#         teaching_text = response.choices[0].message.content
        
#         user_input = speak(teaching_text, client, audio_handler, interruptible=True)

#         if user_input and user_input.strip():
#             handle_user_question(user_input, client, lesson, session_state['current_chunk_index'], audio_handler)
#             speak("بسیار خب، برگردیم به درسی که در حال توضیح آن بودم.", client, audio_handler)
#             continue
#         elif user_input is not None:
#             speak("ببخشید، به نظر رسید چیزی گفتید. به توضیحاتم ادامه می‌دهم.", client, audio_handler)
#             continue
        
#         should_repeat_chunk = False
#         while True:
#             speak("آیا این بخش واضح بود یا سوالی دارید؟", client, audio_handler)
#             user_response = audio_handler.listen_and_transcribe(context_prompt="ادامه بده. سوال دارم. تکرار کن.")
#             if not user_response or recognize_command(user_response) == "CONTINUE_LESSON": break
#             command = recognize_command(user_response)
#             if command == "REPEAT_CHUNK":
#                 speak("حتما، این بخش را دوباره تکرار می‌کنم.", client, audio_handler)
#                 should_repeat_chunk = True
#                 break 
#             else:
#                 handle_user_question(user_response, client, lesson, session_state['current_chunk_index'], audio_handler)
        
#         if should_repeat_chunk: continue
#         session_state['current_chunk_index'] += 1

#     speak("این درس به پایان رسید. موفق باشی.", client, audio_handler)

# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("\nبرنامه در حال بسته شدن...")
#     except Exception as e:
#         print(f"\nیک خطای بحرانی رخ داد: {e}")


















import os
import psycopg2
import json
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from dotenv import load_dotenv
from openai import OpenAI  # <--- این خط حیاتی است و باید اضافه شود
import pygame
import time
import uuid
from collections import deque
import re

# ... (سایر import های شما)

class VADAudioHandler:
    """
    نسخه نهایی با سیستم دفاعی سه لایه در برابر هشدارهای کاذب (False Positives).
    """
    def __init__(self, client, silence_energy_threshold=50, silence_duration=1.2):
        self.client = client
        self.SILENCE_ENERGY_THRESHOLD = silence_energy_threshold
        self.SILENCE_DURATION = silence_duration
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = int(self.SAMPLE_RATE / 10)
        self.audio_queue = deque()
        self.is_speaking = False
        self.silent_chunks = 0
        self.required_silent_chunks = int(self.SILENCE_DURATION * (self.SAMPLE_RATE / self.CHUNK_SIZE))
        self.stream = None
        self.speech_start_energy_threshold = 500

        # --- لایه ۱ و ۲: بافر برای تحلیل الگو و میانگین انرژی ---
        self.chunk_buffer = deque(maxlen=4) # بافر را کمی بزرگتر می‌کنیم
        self.MIN_ENERGETIC_CHUNKS = 2       # حداقل تعداد تکه‌های پرانرژی مورد نیاز

        # --- لایه ۳: نشانگر تایید صحبت ---
        self.potential_speech_marker = False

    def calibrate(self, duration=2):
        # این تابع بدون تغییر باقی می‌ماند
        print("ربات (کالیبراسیون): برای تنظیم حساسیت میکروفون، لطفاً برای چند لحظه سکوت کنید...")
        print("--- شروع کالیبراسیون ---")
        energies = []
        print("در حال ضبط نویز محیط...")
        calibration_recording = sd.rec(int(duration * self.SAMPLE_RATE), samplerate=self.SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        num_chunks = len(calibration_recording) // self.CHUNK_SIZE
        for i in range(num_chunks):
            chunk = calibration_recording[i*self.CHUNK_SIZE:(i+1)*self.CHUNK_SIZE]
            energies.append(np.linalg.norm(chunk))
        if energies:
            average_noise = np.mean(energies)
            print(f"میانگین انرژی نویز محیط محاسبه شد: {average_noise:.2f}")
            self.speech_start_energy_threshold = (average_noise * 5.0) + 300
        else:
            self.speech_start_energy_threshold = 500
        print(f"--- کالیبراسیون تمام شد. آستانه انرژی برای شروع صحبت: {self.speech_start_energy_threshold:.2f} ---")
        print("ربات (کالیبراسیون): متشکرم. تنظیمات انجام شد.")

    def _reset_state(self):
        self.audio_queue.clear()
        self.is_speaking = False
        self.silent_chunks = 0
        self.chunk_buffer.clear()
        self.potential_speech_marker = False # ریست کردن نشانگر

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"خطای استریم صدا: {status}")
            return

        current_energy = np.linalg.norm(indata)

        if not self.is_speaking:
            self.chunk_buffer.append(indata.copy())

            # --- منطق جدید و پیشرفته تشخیص شروع صحبت ---
            if len(self.chunk_buffer) < self.chunk_buffer.maxlen:
                # تا زمانی که بافر پر نشده، هیچ تصمیمی نگیر
                return

            # لایه ۱: شمارش تکه‌های پرانرژی
            energetic_chunks_count = sum(1 for chunk in self.chunk_buffer if np.linalg.norm(chunk) > self.speech_start_energy_threshold)
            
            # لایه ۲: محاسبه میانگین انرژی بافر
            average_buffer_energy = np.mean([np.linalg.norm(chunk) for chunk in self.chunk_buffer])

            is_potential_speech = (energetic_chunks_count >= self.MIN_ENERGETIC_CHUNKS and 
                                   average_buffer_energy > self.speech_start_energy_threshold)

            # لایه ۳: استفاده از نشانگر تایید
            if is_potential_speech:
                if self.potential_speech_marker:
                    # این دومین نشانه متوالی است. صحبت را تایید کن!
                    print(f"\n--- الگوی صحبت پایدار تایید شد! (انرژی میانگین: {average_buffer_energy:.2f}) ---")
                    self.is_speaking = True
                    self.silent_chunks = 0
                    self.audio_queue.clear()
                    self.audio_queue.extend(self.chunk_buffer) # اضافه کردن صدای از قبل ضبط شده
                else:
                    # این اولین نشانه است. فقط نشانگر را فعال کن و منتظر بمان.
                    self.potential_speech_marker = True
            else:
                # الگو پایدار نبود، پس نشانگر را غیرفعال کن.
                self.potential_speech_marker = False
            return

        if self.is_speaking:
            self.audio_queue.append(indata.copy())
            if current_energy < self.SILENCE_ENERGY_THRESHOLD:
                self.silent_chunks += 1
                if self.silent_chunks > self.required_silent_chunks:
                    self.is_speaking = False
            else:
                self.silent_chunks = 0
    
    # تابع listen_and_transcribe بدون تغییر باقی می‌ماند
    def listen_and_transcribe(self, context_prompt="", timeout=7.0):
        self._reset_state()
        print("ربات: در حال گوش دادن به دستور/سوال شما...")
        self.stream = sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1, dtype='int16', blocksize=self.CHUNK_SIZE, callback=self._audio_callback)
        with self.stream:
            start_time = time.time()
            while not self.is_speaking and time.time() - start_time < timeout:
                time.sleep(0.1)
            if self.is_speaking:
                while self.is_speaking and time.time() - start_time < timeout:
                    time.sleep(0.1)
        print("\n--- گوش دادن متوقف شد. ---")
        if not self.audio_queue:
            print("ربات: صدایی شناسایی نشد.")
            return None
        recording = np.concatenate(list(self.audio_queue))
        temp_audio_file = f"temp_vad_audio_{uuid.uuid4()}.wav"
        write(temp_audio_file, self.SAMPLE_RATE, recording)
        try:
            with open(temp_audio_file, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="fa", prompt=context_prompt)
            transcribed_text = transcription.text.strip()
            if transcribed_text:
                print(f"ربات: متن شناسایی شده: '{transcribed_text}'")
                return transcribed_text
            else:
                print("ربات: متنی شناسایی نشد.")
                return ""
        except Exception as e:
            print(f"خطا در تبدیل صدا: {e}")
            return None
        finally:
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)

# --- بخش 3: تمام توابع کمکی برنامه ---

def speak(text, client, audio_handler=None, interruptible=False):
    user_interrupted_text = None
    sentences = re.split(r'(?<=[.!?])\s+', text)
    pygame.init()
    pygame.mixer.init()
    stream = None
    for sentence in sentences:
        if not sentence.strip(): continue
        if user_interrupted_text: break
        speech_file = f"temp_speech_{uuid.uuid4()}.mp3"
        try:
            print(f"ربات (در حال صحبت): {sentence}")
            response = client.audio.speech.create(model="tts-1", voice="nova", input=sentence)
            response.stream_to_file(speech_file)
            pygame.mixer.music.load(speech_file)
            if interruptible and audio_handler:
                audio_handler._reset_state()
                stream = sd.InputStream(samplerate=audio_handler.SAMPLE_RATE, channels=1, dtype='int16', blocksize=audio_handler.CHUNK_SIZE, callback=audio_handler._audio_callback)
                stream.start()
                print("--- حالت وقفه فعال شد. در حال گوش دادن به کاربر... ---")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if interruptible and audio_handler and audio_handler.is_speaking:
                    pygame.mixer.music.stop()
                    print("\n--- صحبت ربات توسط کاربر قطع شد! ---")
                    start_wait = time.time()
                    while audio_handler.is_speaking and time.time() - start_wait < 7.0:
                        time.sleep(0.1)
                    user_interrupted_text = "INTERRUPTED"
                    break
                time.sleep(0.01)
        finally:
            if stream and stream.active:
                stream.stop(); stream.close(); stream = None
                print("--- حالت وقفه غیرفعال شد. ---")
            if pygame.mixer.get_init():
                pygame.mixer.music.unload()
            if os.path.exists(speech_file):
                try: os.remove(speech_file)
                except Exception as e: print(f"خطا در حذف فایل موقت صوتی: {e}")
        if user_interrupted_text: break
    if user_interrupted_text == "INTERRUPTED":
        print("\n--- پردازش صدای ضبط شده کاربر پس از وقفه ---")
        if not audio_handler or not audio_handler.audio_queue:
            pygame.quit(); return None
        recording = np.concatenate(list(audio_handler.audio_queue))
        temp_audio_file = f"temp_interrupt_audio_{uuid.uuid4()}.wav"
        write(temp_audio_file, audio_handler.SAMPLE_RATE, recording)
        transcribed_text = None
        try:
            with open(temp_audio_file, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file, language="fa", prompt="توضیح بده. سوال دارم.")
            transcribed_text = transcription.text.strip()
            print(f"ربات: متن شناسایی شده از وقفه: '{transcribed_text}'")
        except Exception as e: print(f"خطا در تبدیل صدای وقفه: {e}")
        finally:
            if os.path.exists(temp_audio_file): os.remove(temp_audio_file)
        pygame.quit()
        return transcribed_text
    pygame.quit()
    return None

def find_user_by_fuzzy_name(transcribed_text):
    # این تابع به client نیازی ندارد
    conn = None
    try:
        # ... (کد داخلی این تابع بدون تغییر باقی می‌ماند)
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
        if result: return {'user_id': result[0], 'first_name': result[1]}
        return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"خطا در جستجوی کاربر: {error}")
        return None
    finally:
        if conn is not None: conn.close()

def get_enrolled_course_info(user_id):
    # این تابع به client نیازی ندارد
    conn = None
    try:
        # ... (کد داخلی این تابع بدون تغییر باقی می‌ماند)
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        query = "SELECT C.title, C.pdf_file_path FROM Enrollments E JOIN Courses C ON E.course_id = C.course_id WHERE E.user_id = %s LIMIT 1;"
        cur.execute(query, (user_id,))
        result = cur.fetchone()
        cur.close()
        if result: return {'title': result[0], 'pdf_path': result[1]}
        return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"خطا در یافتن درس کاربر: {error}")
        return None
    finally:
        if conn is not None: conn.close()

def load_lesson_from_json(pdf_path, client):
    try:
        file_name = os.path.basename(pdf_path).replace('.pdf', '.json')
        json_path = os.path.join('lessons', file_name)
        with open(json_path, 'r', encoding='utf-8') as f:
            lesson_content = json.load(f)
        print(f"ربات: درس '{lesson_content['course_title']}' با موفقیت بارگذاری شد.")
        return lesson_content
    except Exception as e:
        # در صورت خطا، از client برای صحبت کردن استفاده می‌شود
        speak(f"خطا در بارگذاری فایل درس: {e}", client)
        return None

def is_confirmation(text):
    # این تابع به client نیازی ندارد
    text = text.lower().strip().replace('.', '')
    replacements = {'ي': 'ی', 'ك': 'ک', '\u200c': ' '}
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    positive_keywords = ["بله", "آره", "آری", "حتما", "موافقم", "شروع کن", "آماده ام", "آمادم", "باشه", "باید"]
    negative_keywords = ["نه", "نخیر", "فعلا نه", "آماده نیستم", "مخالفم"]
    if any(keyword in text for keyword in negative_keywords): return False
    if any(keyword in text for keyword in positive_keywords): return True
    return False

def recognize_command(text):
    # این تابع به client نیازی ندارد
    text_lower = text.lower()
    if any(keyword in text_lower for keyword in ["تکرار کن", "دوباره بگو", "متوجه نشدم"]): return "REPEAT_CHUNK"
    if any(keyword in text_lower for keyword in ["ادامه بده", "بعدی", "برو", "سوالی ندارم"]): return "CONTINUE_LESSON"
    return "USER_QUESTION"

def handle_user_question(question, client, lesson_content, current_chunk_index, audio_handler):
    try:
        future_chunks = [chunk for chunk in lesson_content['chunks'] if chunk['chunk_id'] > current_chunk_index + 1]
        if future_chunks:
            future_keywords = [kw for chunk in future_chunks for kw in chunk.get('keywords', [])]
            prompt_check_future = f"سوال کاربر: '{question}'. لیست کلمات کلیدی آینده: {json.dumps(future_keywords, ensure_ascii=False)}. آیا سوال به این موضوعات آینده مرتبط است؟ پاسخ فقط JSON: {{\"is_future_topic\": true}} یا {{\"is_future_topic\": false}}"
            response = client.chat.completions.create(model="gpt-4o", response_format={"type": "json_object"}, messages=[{"role": "user", "content": prompt_check_future}])
            analysis = json.loads(response.choices[0].message.content)
            if analysis.get("is_future_topic", False):
                speak("سوال خوبی پرسیدی! هنوز به این مبحث نرسیدیم. لطفاً تامل بفرمایید.", client, audio_handler)
                return
        known_context = " ".join([f"موضوع: {chunk['title']}. محتوا: {chunk['content']}" for chunk in lesson_content['chunks'] if chunk['chunk_id'] <= current_chunk_index + 1])
        prompt_answer = f"شما یک مدرس هستید. با توجه به این اطلاعات: '{known_context}'. به این سوال پاسخ بده: '{question}'."
        answer_response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_answer}])
        answer = answer_response.choices[0].message.content
        speak(answer, client, audio_handler, interruptible=True)
    except Exception as e:
        print(f"خطا در پردازش سوال کاربر: {e}")
        speak("متاسفانه در پردازش سوال شما خطایی رخ داد.", client, audio_handler)

# --- بخش 4: تابع اصلی برنامه ---

def main():
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print(f"خطا در اتصال به OpenAI: {e}")
        return

    audio_handler = VADAudioHandler(client)
    audio_handler.calibrate()
    
    speak("سلام، برای شروع لطفاً نام کامل خود را بگویید.", client, audio_handler)
    user_data = None
    for _ in range(2):
        user_name_text = audio_handler.listen_and_transcribe(context_prompt="نام من ... است.")
        if not user_name_text:
            speak("متاسفانه صدایی دریافت نکردم. لطفاً دوباره تلاش کنید.", client, audio_handler)
            continue
        potential_user = find_user_by_fuzzy_name(user_name_text)
        if potential_user:
            speak(f"متوجه شدم، {potential_user['first_name']}. درست است؟", client, audio_handler)
            confirmation_text = audio_handler.listen_and_transcribe(context_prompt="بله. نه.")
            if confirmation_text and is_confirmation(confirmation_text):
                user_data = potential_user
                break
        speak("متاسفانه نام شما را تشخیص ندادم. لطفاً دوباره بگویید.", client, audio_handler)

    if not user_data:
        speak("شناسایی ناموفق بود. برنامه پایان یافت.", client, audio_handler)
        return

    course_info = get_enrolled_course_info(user_data['user_id'])
    if not course_info:
        speak(f"سلام {user_data['first_name']}. شما هنوز در هیچ درسی ثبت‌نام نکرده‌اید.", client, audio_handler)
        return
    
    speak(f"عالیه {user_data['first_name']}. می‌بینم که در درس «{course_info['title']}» ثبت‌نام کرده‌ای. آماده‌ای تا درس را شروع کنیم؟", client, audio_handler)
    confirmation_text = audio_handler.listen_and_transcribe(context_prompt="بله. آره. آماده ام.")
    if not confirmation_text or not is_confirmation(confirmation_text):
         speak("بسیار خب، هر وقت آماده بودی من اینجا هستم.", client, audio_handler)
         return

    lesson = load_lesson_from_json(course_info['pdf_path'], client)
    if not lesson: return

    session_state = {'current_chunk_index': 0}
    speak(f"عالیه! پس درس «{lesson['course_title']}» را شروع می‌کنیم. هر زمان سوالی داشتی، می‌توانی صحبت من را قطع کنی.", client, audio_handler)

    while session_state['current_chunk_index'] < len(lesson['chunks']):
        current_chunk = lesson['chunks'][session_state['current_chunk_index']]
        prompt = f"موضوع زیر را به زبان ساده توضیح بده: {current_chunk['title']} - {current_chunk['content']}"
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        teaching_text = response.choices[0].message.content
        
        user_input = speak(teaching_text, client, audio_handler, interruptible=True)

        if user_input and user_input.strip():
            handle_user_question(user_input, client, lesson, session_state['current_chunk_index'], audio_handler)
            speak("بسیار خب، برگردیم به درسی که در حال توضیح آن بودم.", client, audio_handler)
            continue
        elif user_input is not None:
            speak("ببخشید، به نظر رسید چیزی گفتید. به توضیحاتم ادامه می‌دهم.", client, audio_handler)
            continue
        
        should_repeat_chunk = False
        while True:
            speak("آیا این بخش واضح بود یا سوالی دارید؟", client, audio_handler)
            user_response = audio_handler.listen_and_transcribe(context_prompt="ادامه بده. سوال دارم. تکرار کن.")
            if not user_response or recognize_command(user_response) == "CONTINUE_LESSON": break
            command = recognize_command(user_response)
            if command == "REPEAT_CHUNK":
                speak("حتما، این بخش را دوباره تکرار می‌کنم.", client, audio_handler)
                should_repeat_chunk = True
                break 
            else:
                handle_user_question(user_response, client, lesson, session_state['current_chunk_index'], audio_handler)
        
        if should_repeat_chunk: continue
        session_state['current_chunk_index'] += 1

    speak("این درس به پایان رسید. موفق باشی.", client, audio_handler)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nبرنامه در حال بسته شدن...")
    except Exception as e:
        print(f"\nیک خطای بحرانی رخ داد: {e}")