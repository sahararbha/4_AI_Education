// // src/app/services/gemini.service.ts

// import { Injectable } from '@angular/core';
// import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai';

// @Injectable({
//   providedIn: 'root'
// })
// export class GeminiService {

//   private genAI: GoogleGenerativeAI;

//   constructor() {
//     // کلید API واقعی و کامل خود را اینجا کپی کنید
//     const API_KEY = 'AIzaSyAebbRZnupQ4cz4E7_ozyA51D_yMQJv5Cg';

//     this.genAI = new GoogleGenerativeAI(API_KEY);
//   }

//   async generateText(prompt: string): Promise<string> {
//     try {
//       const safetySettings = [
//         { category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE },
//         { category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE },
//         { category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE },
//         { category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE },
//       ];

//       const model = this.genAI.getGenerativeModel({
//         model: "gemini-pro",
//         safetySettings
//       });

//       const result = await model.generateContent(prompt);
//       const response = await result.response;
//       const text = response.text();
//       return text;

//     } catch (error) {
//       console.error('خطا در ارتباط با Gemini API:', error);
//       return 'متاسفانه در دریافت پاسخ از هوش مصنوعی مشکلی پیش آمد.';
//     }
//   }
// }

// src/app/services/gemini.service.ts

// import { Injectable } from '@angular/core';
// import { HttpClient } from '@angular/common/http';
// import { firstValueFrom } from 'rxjs';

// @Injectable({
//   providedIn: 'root'
// })
// export class GeminiService {
//   private apiKey = 'AIzaSyAebbRZnupQ4cz4E7_ozyA51D_yMQJv5Cg'; // <-- کلید API را اینجا قرار دهید
  
//   // **هشدار امنیتی:** این روش کلید API شما را در معرض دید قرار می‌دهد
//   // و فقط برای تست مناسب است.
//   private corsProxy = 'https://cors-anywhere.herokuapp.com/';
//   private googleApiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${this.apiKey}`;
  
//   private fullApiUrl = this.corsProxy + this.googleApiUrl;

//   constructor(private http: HttpClient) { }

//   async generateText(prompt: string): Promise<string> {
//     const requestBody = {
//       contents: [{ parts: [{ text: prompt }] }]
//     };

//     try {
//       // درخواست به پروکسی CORS ارسال می‌شود
//       const response = await firstValueFrom(
//         this.http.post<any>(this.fullApiUrl, requestBody)
//       );
      
//       // استخراج پاسخ از ساختار JSON گوگل
//       if (response && response.candidates && response.candidates.length > 0) {
//         return response.candidates[0].content.parts[0].text;
//       } else {
//         // اگر پاسخی وجود نداشت یا ساختار آن متفاوت بود
//         console.error("پاسخ نامعتبر از API دریافت شد:", response);
//         return "پاسخ نامعتبر یا خالی از هوش مصنوعی دریافت شد.";
//       }

//     } catch (error) {
//       console.error('خطا در ارتباط با Gemini API از طریق پروکسی CORS:', error);
//       return 'متاسفانه در دریافت پاسخ از هوش مصنوعی مشکلی پیش آمد.';
//     }
//   }
// }


// src/app/services/gemini.service.tsبرای Flask

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class GeminiService {
  // آدرس کامل سرور بک‌اند ما
  private backendUrl = 'http://localhost:5000/api/gemini-query';

  constructor(private http: HttpClient) { }

  async generateText(prompt: string): Promise<string> {
    try {
      // یک درخواست POST به بک‌اند خودمان (Flask) می‌فرستیم
      const response = await firstValueFrom(
        this.http.post<{ response: string }>(this.backendUrl, { prompt: prompt })
      );
      return response.response;

    } catch (error) {
      console.error('خطا در ارتباط با سرور بک‌اند:', error);
      // این همان پیامی است که در سایت به کاربر نمایش داده می‌شود
      return 'متاسفانه در دریافت پاسخ از هوش مصنوعی مشکلی پیش آمد.';
    }
  }
}