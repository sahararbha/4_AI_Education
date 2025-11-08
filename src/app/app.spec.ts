// src/app/app.spec.ts - اصلاح شده برای استفاده از نام فایل صحیح

import { TestBed } from '@angular/core/testing';
// **اصلاح نهایی:** تغییر مسیر وارد کردن به './app'
import { AppComponent } from './app'; 

describe('AppComponent', () => { 
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent], 
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent); 
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', () => {
    const fixture = TestBed.createComponent(AppComponent); 
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toBeTruthy(); 
  });
});