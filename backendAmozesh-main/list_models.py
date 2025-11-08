# list_models.py
import google.generativeai as genai
from dotenv import load_dotenv
import os

# بارگذاری کلید API از فایل .env
load_dotenv()
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("خطا: متغیر GEMINI_API_KEY در فایل .env پیدا نشد.")
else:
    try:
        # پیکربندی کتابخانه با کلید API
        genai.configure(api_key=GEMINI_API_KEY)

        print("\n--- مدل‌های موجود برای کلید API شما ---")
        
        # درخواست لیست مدل‌ها از گوگل
        for m in genai.list_models():
            # ما فقط به مدل‌هایی نیاز داریم که قابلیت تولید محتوا (چت و صدا) را دارند
            if 'generateContent' in m.supported_generation_methods:
                print(f"نام مدل: {m.name}")
        
        print("----------------------------------------\n")
        print("لطفاً نام یکی از مدل‌های بالا را کپی کرده و در فایل app.py جایگزین کنید.")

    except Exception as e:
        print(f"یک خطای غیرمنتظره رخ داد: {e}")