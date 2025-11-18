// import { TestBed } from '@angular/core/testing';

// import { Gemini } from './gemini';

// describe('Gemini', () => {
//   let service: Gemini;

//   beforeEach(() => {
//     TestBed.configureTestingModule({});
//     service = TestBed.inject(Gemini);
//   });

//   it('should be created', () => {
//     expect(service).toBeTruthy();
//   });
// });
// src/app/services/gemini.service.spec.ts

import { TestBed } from '@angular/core/testing';
import { GeminiService } from './gemini.service'; // <-- اینجا را از Gemini به GeminiService تغییر دهید

describe('GeminiService', () => { // <-- اینجا را هم تغییر دهید
  let service: GeminiService; // <-- و اینجا

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(GeminiService); // <-- و اینجا
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});