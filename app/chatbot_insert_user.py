import os
import psycopg2
import json
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from playsound import playsound

# --- قدم 1: بارگذاری متغیرهای محیطی ---
load_dotenv()

# --- قدم 2: تنظیمات اولیه ---
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception as e:
    print(f"خطا در اتصال به OpenAI: مطمئن شوید OPENAI_API_KEY در فایل .env صحیح و معتبر است.")
    print(e)
    exit()

DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "5432"


# --- قدم 3: تابع برای صحبت کردن ربات (Text-to-Speech) ---
def speak(text):
    """
    متن ورودی را به OpenAI می‌فرستد، فایل صوتی دریافت می‌کند و آن را پخش می‌کند.
    """
    temp_speech_file = "temp_bot_speech.mp3"
    try:
        # نمایش متنی که ربات می‌گوید (برای راحتی کاربر و خطایابی)
        print(f"ربات (در حال صحبت): {text}")

        # ارسال درخواست به API تبدیل متن به گفتار OpenAI
        response = client.audio.speech.create(
            model="tts-1",      # مدل استاندارد و با کیفیت
            voice="nova",       # انتخاب یکی از صداهای موجود (nova صدای زنانه و واضحی دارد)
            input=text
        )

        # ذخیره فایل صوتی دریافت شده
        response.stream_to_file(temp_speech_file)

        # پخش فایل صوتی
        playsound(temp_speech_file)

    except Exception as e:
        print(f"خطا در تولید یا پخش صدا: {e}")
    finally:
        # حذف فایل صوتی موقت پس از پخش
        if os.path.exists(temp_speech_file):
            os.remove(temp_speech_file)


# --- قدم 4: تابع برای ضبط صدا و تبدیل آن به متن ---
def record_audio_and_transcribe():
    sample_rate = 44100
    duration = 7
    temp_audio_file = "temp_user_audio.wav"
    try:
        print(f"ربات: لطفاً به مدت {duration} ثانیه صحبت کنید... (شروع ضبط)")
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.int16)
        sd.wait()
        print("ربات: ضبط تمام شد. در حال ارسال برای پردازش...")
        write(temp_audio_file, sample_rate, recording)
        with open(temp_audio_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        os.remove(temp_audio_file)
        print(f"ربات: متن شناسایی شده: '{transcription.text}'")
        return transcription.text
    except Exception as e:
        print(f"خطا در فرآیند ضبط یا تبدیل صدا: {e}")
        if os.path.exists(temp_audio_file):
            os.remove(temp_audio_file)
        return None


# --- قدم 5: تابع برای استخراج اطلاعات کاربر با هوش مصنوعی ---
def extract_user_info_with_openai(text):
    print("ربات: در حال پردازش اطلاعات شما با هوش مصنوعی...")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "شما یک دستیار هوشمند هستید که نام (first_name)، نام خانوادگی (last_name) و ایمیل (email) را از متن استخراج کرده و فقط به صورت یک آبجکت JSON خروجی می‌دهید."},
                {"role": "user", "content": text}
            ]
        )
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        print(f"خطا در ارتباط با OpenAI یا پردازش پاسخ: {e}")
        return None


# --- قدم 6: تابع برای درج اطلاعات و بازگرداندن شناسه کاربر ---
def insert_user_into_db(user_info):
    """
    کاربر جدید را درج کرده و شناسه (ID) او را برمی‌گرداند.
    """
    conn = None
    new_user_id = None
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        username = user_info['email'].split('@')[0]
        password_hash = "a_very_secure_hashed_password_placeholder"
        
        insert_query = """
            INSERT INTO Users (username, password_hash, email, first_name, last_name) 
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING user_id;
        """
        cur.execute(insert_query, (username, password_hash, user_info['email'], user_info['first_name'], user_info['last_name']))
        
        new_user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        print(f"ربات: کاربر '{user_info['first_name']}' با شناسه {new_user_id} با موفقیت در پایگاه داده ثبت شد.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"خطا در عملیات پایگاه داده: {error}")
        if conn:
            conn.rollback()
    finally:
        if conn is not None:
            conn.close()
        return new_user_id


# --- قدم 7: تابع برای خواندن نام کاربر از پایگاه داده ---
def get_user_first_name_by_id(user_id):
    """
    با استفاده از شناسه کاربر، نام کوچک او را از جدول Users می‌خواند.
    """
    conn = None
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        cur = conn.cursor()
        select_query = "SELECT first_name FROM Users WHERE user_id = %s"
        cur.execute(select_query, (user_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            return result[0]
        return None
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"خطا در خواندن اطلاعات کاربر: {error}")
        return None
    finally:
        if conn is not None:
            conn.close()


# --- قدم 8: اجرای اصلی برنامه ---
def main():
    # 1. ربات پیام خوش‌آمدگویی را به صورت صوتی پخش می‌کند
    welcome_message = "سلام! من راهنمای هوشمند شما برای یادگیری هستم. برای شروع، لطفاً نام کامل و ایمیل خود را بگویید. مثلاً: «مریم محمدی، ایمیل m.mohammadi@outlook.com». هر وقت آماده بودید، شروع کنید."
    speak(welcome_message)

    # 2. کاربر به صورت صوتی پاسخ می‌دهد
    transcribed_text = record_audio_and_transcribe()
    if not transcribed_text:
        speak("متاسفانه ورودی صوتی دریافت نشد. لطفاً برنامه را دوباره اجرا کنید.")
        return

    # 3. اطلاعات از صدای کاربر استخراج و در دیتابیس ذخیره می‌شود
    extracted_info = extract_user_info_with_openai(transcribed_text)
    if not (extracted_info and 'first_name' in extracted_info and 'email' in extracted_info):
        speak("متاسفانه نتوانستم اطلاعات شما را به درستی استخراج کنم. لطفاً دوباره تلاش کنید.")
        return
    
    print(f"ربات: اطلاعات زیر استخراج شد: {extracted_info}")
    new_user_id = insert_user_into_db(extracted_info)

    # 4. ربات با استفاده از اطلاعات جدید، مکالمه را ادامه می‌دهد
    if new_user_id:
        first_name = get_user_first_name_by_id(new_user_id)
        if first_name:
            next_step_message = f"بسیار خب {first_name}، آماده‌ای تا درس را شروع کنیم؟"
            speak(next_step_message)
        else:
            speak("اطلاعات شما ثبت شد، اما در بازیابی نام شما مشکلی پیش آمد.")
    else:
        speak("در ثبت اطلاعات شما در پایگاه داده مشکلی پیش آمد. لطفاً با پشتیبانی تماس بگیرید.")


if __name__ == "__main__":
    main()