import threading
import time
import os
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from openai import OpenAI
from dotenv import load_dotenv
from playsound import playsound

# --- بخش 1: تنظیمات اولیه ---
load_dotenv()
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"خطا در اتصال به OpenAI: {e}")
    exit()

# متغیرهای اشتراکی بین نخ‌ها
# این پرچم به نخ Speaker می‌گوید که آیا باید صحبتش را قطع کند یا نه
user_is_speaking_flag = threading.Event()
# برای ذخیره فایل صوتی ضبط شده کاربر
user_audio_data = []

# --- بخش 2: توابع کمکی ---

def text_to_speech_file(text, filename="temp_bot_speech.mp3"):
    """متن را به فایل صوتی تبدیل و ذخیره می‌کند، اما آن را پخش نمی‌کند."""
    try:
        print(f"ربات (در حال آماده‌سازی صدا): {text}")
        response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
        response.stream_to_file(filename)
        return True
    except Exception as e:
        print(f"خطا در تولید صدا: {e}")
        return False

def transcribe_audio_file(filename="temp_user_audio.wav"):
    """فایل صوتی را به متن تبدیل می‌کند."""
    try:
        with open(filename, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        print(f"ربات: متن شناسایی شده: '{transcription.text}'")
        return transcription.text
    except Exception as e:
        print(f"خطا در تبدیل صدا به متن: {e}")
        return ""

def get_ai_response(text):
    """یک پاسخ ساده از AI برای متن ورودی می‌گیرد."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "شما یک دستیار هوشمند هستید که به سوالات پاسخ کوتاه و مفید می‌دهید."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"خطا در دریافت پاسخ از AI: {e}")
        return "متاسفانه در پردازش درخواست شما مشکلی پیش آمد."

# --- بخش 3: منطق اصلی Barge-in (نخ‌ها) ---

def speaker_thread_func(text):
    """
    این تابع در یک نخ جداگانه اجرا می‌شود.
    وظیفه آن پخش صدای ربات است، اما به طور مداوم پرچم را چک می‌کند.
    """
    speech_file = "temp_bot_speech.mp3"
    if not text_to_speech_file(text, speech_file):
        return

    print("--- نخ Speaker: شروع به صحبت کردن ربات ---")
    
    # ما از یک کتابخانه دیگر برای پخش استفاده نمی‌کنیم، بلکه خودمان آن را مدیریت می‌کنیم
    # تا بتوانیم آن را متوقف کنیم. این بخش کمی پیچیده است و از sounddevice استفاده می‌کند.
    # برای سادگی، در این دمو از playsound استفاده می‌کنیم و با یک حلقه شبیه‌سازی می‌کنیم.
    
    # شبیه‌سازی پخش صدا در قطعات کوچک
    duration_of_speech = 5 # فرض می‌کنیم صحبت ربات 5 ثانیه طول می‌کشد
    for i in range(duration_of_speech * 10): # هر 100 میلی‌ثانیه چک می‌کنیم
        if user_is_speaking_flag.is_set():
            print("\n--- نخ Speaker: کاربر صحبت کرد! صحبت ربات قطع شد. ---")
            # در یک سیستم واقعی، اینجا دستور توقف پخش صدا را ارسال می‌کنیم.
            return
        time.sleep(0.1)
    
    # اگر حلقه تمام شد و کاربر صحبت نکرده بود، صدا را کامل پخش می‌کنیم
    if not user_is_speaking_flag.is_set():
        playsound(speech_file)
        print("--- نخ Speaker: صحبت ربات به پایان رسید. ---")
    
    if os.path.exists(speech_file):
        os.remove(speech_file)


def listener_thread_func():
    """
    این تابع در یک نخ جداگانه اجرا می‌شود.
    وظیفه آن گوش دادن مداوم به میکروفون برای تشخیص صدای کاربر است.
    """
    global user_audio_data
    user_audio_data = []
    
    sample_rate = 16000
    chunk_size = 1024
    # آستانه انرژی صدا برای تشخیص صحبت (این مقدار ممکن است نیاز به تنظیم داشته باشد)
    energy_threshold = 400 
    silence_chunks_needed = 10 # تعداد قطعات سکوت برای پایان دادن به ضبط
    
    silence_counter = 0
    is_recording = False

    print("--- نخ Listener: شروع به گوش دادن به میکروفون... ---")

    def audio_callback(indata, frames, time, status):
        nonlocal is_recording, silence_counter
        global user_audio_data

        # محاسبه انرژی (بلندی) صدا
        energy = np.linalg.norm(indata) * 10
        
        if energy > energy_threshold:
            # کاربر در حال صحبت است
            if not is_recording:
                print("\n--- نخ Listener: صدای کاربر تشخیص داده شد! شروع ضبط... ---")
                is_recording = True
                user_is_speaking_flag.set() # پرچم را برای قطع کردن صحبت ربات فعال کن
            
            user_audio_data.append(indata.copy())
            silence_counter = 0
        else:
            # سکوت
            if is_recording:
                silence_counter += 1
                if silence_counter > silence_chunks_needed:
                    # ضبط تمام شد
                    is_recording = False
                    raise sd.CallbackStop # متوقف کردن استریم

    # شروع استریم صدا از میکروفون
    with sd.InputStream(callback=audio_callback, samplerate=sample_rate, channels=1, blocksize=chunk_size):
        while not user_is_speaking_flag.is_set():
            # منتظر می‌مانیم تا کاربر شروع به صحبت کند
            time.sleep(0.1)
        
        # اگر کاربر صحبت کرد، منتظر می‌مانیم تا صحبتش تمام شود
        while is_recording:
            time.sleep(0.1)

    print("--- نخ Listener: گوش دادن متوقف شد. ---")


# --- بخش 4: اجرای اصلی برنامه ---
def main():
    global user_audio_data
    
    bot_message = "سلام! من یک ربات هوشمند هستم و در حال توضیح یک مطلب طولانی هستم. من به صحبت ادامه می‌دهم تا زمانی که شما صحبت من را قطع کنید و سوال خود را بپرسید. لطفاً امتحان کنید."
    
    # 1. نخ Listener را راه‌اندازی کن تا در پس‌زمینه به میکروفون گوش دهد
    listener = threading.Thread(target=listener_thread_func)
    listener.start()
    
    # 2. کمی تاخیر برای آماده شدن Listener
    time.sleep(1)
    
    # 3. نخ Speaker را راه‌اندازی کن تا ربات شروع به صحبت کند
    speaker = threading.Thread(target=speaker_thread_func, args=(bot_message,))
    speaker.start()
    
    # 4. منتظر بمان تا هر دو نخ کار خود را تمام کنند
    listener.join()
    speaker.join()
    
    # 5. اگر کاربر صحبت کرده بود، صدای او را پردازش کن
    if user_audio_data:
        print("\n--- برنامه اصلی: پردازش صدای ضبط شده کاربر ---")
        # تبدیل لیست داده‌های صوتی به یک آرایه numpy
        user_recording = np.concatenate(user_audio_data, axis=0)
        user_audio_file = "temp_user_audio.wav"
        write(user_audio_file, 16000, user_recording)
        
        # تبدیل صدای کاربر به متن
        user_text = transcribe_audio_file(user_audio_file)
        
        if user_text:
            # دریافت پاسخ از AI
            ai_response = get_ai_response(user_text)
            
            # پخش پاسخ ربات
            response_speech_file = "temp_bot_response.mp3"
            if text_to_speech_file(ai_response, response_speech_file):
                playsound(response_speech_file)
                os.remove(response_speech_file)

        if os.path.exists(user_audio_file):
            os.remove(user_audio_file)
    else:
        print("\n--- برنامه اصلی: کاربر صحبت ربات را قطع نکرد. ---")

    print("\n--- دمو به پایان رسید. ---")


if __name__ == "__main__":
    main()