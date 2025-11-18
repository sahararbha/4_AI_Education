// src/app/app.component.ts


import { Component, ChangeDetectionStrategy, signal, ElementRef, ViewChild, AfterViewInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule, DatePipe } from '@angular/common';
import * as THREE from 'three'; 
import { GLTFLoader, GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js'; 



const FLASK_BASE_URL = 'https://amozeshbd.runflare.run';

// =======================================================
// تعریف اینترفیس‌ها (Interfaces)
// =======================================================

interface Lesson { title: string; duration: string; isFree?: boolean; }
interface Section { title: string; lessonCount: number; totalDuration: string; lessons: Lesson[]; }
interface Instructor { name: string; price: string; }
interface CourseData {
  title: string;
  breadcrumbs: string[];
  tags: string[];
  rating: number;
  reviews: number;
  description: string;
  instructor: Instructor;
  prerequisites: string;
  lastUpdate: string;
  duration: string;
  status: string;
  price: string;
  originalPrice: string;
  progress: number;
  chapters: number;
  quizzes: number;
  shareLink: string;
  benefits: string[];
  sections: Section[];
  currentLessonText: string;
}
interface ChatMessage { sender: 'user' | 'ai'; message: string; timestamp: Date; }


@Component({
  selector: 'app-root',
  templateUrl: './app.html', 
  standalone: true,
  imports: [CommonModule, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements AfterViewInit, OnDestroy { 
  
  // ارجاع به div در HTML با استفاده از #threeContainer
  @ViewChild('threeContainer', { static: false }) threeContainer!: ElementRef;

  // // تزریق HttpClient در سازنده (constructor injection)
  // constructor(private http: HttpClient) {
  //   this.chatHistory.set([
  //     { sender: 'ai', message: 'سلام! من مشاور AI دوره هستم. برای شروع آموزش صوتی دکمه Play را بزنید یا سؤال خود را بپرسید.', timestamp: new Date() }
  //   ]);
  // }
  // تزریق HttpClient و GeminiService در سازنده
  constructor(private http: HttpClient) { // <-- فقط HttpClient باقی می‌ماند
  this.chatHistory.set([
    { sender: 'ai', message: 'سلام! من مشاور AI دوره هستم. برای شروع آموزش صوتی دکمه Play را بزنید یا سؤال خود را بپرسید.', timestamp: new Date() }
  ]);
}

  // =======================================================
  // سیگنال‌ها و متغیرهای حالت (State Signals & Variables)
  // =======================================================

  activeTab = signal<string>('content');
  expandedSection = signal<number | null>(0);
  isFullScreenVideo = signal(false);
  isAudioPlaying = signal(false);
  private audioPlayer: HTMLAudioElement | null = null;

  chatHistory = signal<ChatMessage[]>([]);
  currentChatInput = signal<string>('');

  lessonChunks = signal<string[]>([]);
  currentChunkIndex = signal(0);

  isRecording = signal(false);
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;

  currentTime = signal(0);
  duration = signal(0);

  // --- متغیرهای جدید برای مدیریت تب‌های موبایل در حالت تمام صفحه ---
  activeMobileTab = signal<'whiteboard' | 'chunks' | 'chat'>('whiteboard');
  // --------------------------

  // --- متغیرهای Three.js (انتقال یافته از کد اول) ---
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private renderer!: THREE.WebGLRenderer;
  private avatarMesh: THREE.Object3D | null = null; 
  private animationMixer: THREE.AnimationMixer | null = null; 
  private clock = new THREE.Clock();
  
  private actions: { [key: string]: THREE.AnimationAction } = {};
  private activeAction: THREE.AnimationAction | null = null;
  private morphMesh: THREE.Mesh | null = null; 
  
  // --- متغیرهای جدید برای انیمیشن چرخشی (Speaking Animation Cycling) ---
  private speakingAnimations: string[] = ['2', 'Armature.001']; 
  private nextSpeakingAnimIndex: number = 0; 
  // --------------------------


  // داده‌های دوره (سیگنال)
  course = signal<CourseData>({
    title: 'مفاهیم علم داده و یادگیری ماشین',
    breadcrumbs: ['خانه', 'برنامه نویسی', 'پایتون', 'یادگیری ماشین'],
    tags: ['داده‌محور', 'محبوب کاربران', 'تخصصی', 'گواهی‌نامه'],
    rating: 4.5, reviews: 340,
    description: 'دوره آموزش پایتون...', instructor: { name: 'نام مدرس', price: '56,000 تومان' },
    prerequisites: 'دارد', lastUpdate: '1401/05/25', duration: '20 ساعت', status: 'تکمیل شده',
    price: '4,800,000', originalPrice: '6,000,000', progress: 40, chapters: 8, quizzes: 12, shareLink: 'abz.com/s/ababababababab',
    benefits: [
      'آشنایی با مفاهیم توابع، ماژول‌ها و نحوه خواندن و پردازش فایل‌های متنی و اکسل',
      'درک جامع از ساخت برنامه‌نویسی شیءگرا',
      'انجام تمرین‌ها و پروژه‌های واقعی برای رسیدن به سطح پیشرفته'
    ],
    // =======================================================
    // **متن گسترش یافته درس پایتون**
    // =======================================================
    currentLessonText: `
      🔹 معرفی زبان پایتون: پایتون یک زبان برنامه‌نویسی سطح بالا، همه‌منظوره و تفسیرشده است که در سال ۱۹۹۱ توسط گیدو فان روسوم معرفی شد. هدف از طراحی آن، سادگی در نوشتن و خواندن کد بود؛ به طوری که حتی افراد تازه‌کار هم بتوانند به‌سرعت برنامه‌نویسی را یاد بگیرند.
      🔹 انواع داده‌های پایه (Basic Data Types): پایتون از انواع داده‌های اصلی مانند اعداد صحیح (Integer)، اعداد اعشاری (Float)، رشته‌ها (String) و بولی‌ها (Boolean) پشتیبانی می‌کند. برای مثال، age = 30 یک عدد صحیح است و name = "Ali" یک رشته است.
      🔹 ساختارهای داده پیشرفته: برای کار با مجموعه‌ای از داده‌ها، ساختارهایی مانند لیست‌ها (Lists) که قابل تغییر هستند (Mutable) و با کروشه [] تعریف می‌شوند، تاپل‌ها (Tuples) که غیرقابل تغییر (Immutable) هستند و دیکشنری‌ها (Dictionaries) که برای ذخیره‌ی جفت‌های کلید-مقدار استفاده می‌شوند و با آکولاد {} تعریف می‌شوند، بسیار حیاتی‌اند.
      🔹 ساختارهای کنترلی: جریان اجرای کد با دستوراتی مانند if, elif, و else کنترل می‌شود. حلقه‌ها (Loops) مانند for و while برای تکرار اجرای یک بلوک کد استفاده می‌شود. برای مثال، حلقه‌ی for برای پیمایش روی عناصر یک لیست بسیار رایج است.
      🔹 تعریف و استفاده از توابع: توابع با کلمه کلیدی def تعریف می‌شوند و به سازماندهی بهتر کد و جلوگیری از تکرار کمک می‌کنند. تعریف تابع به این صورت است: def greet(name): return f"سلام {name}"
      🔹 کاربردهای پایتون: پایتون به دلیل کتابخانه‌های غنی، در حوزه‌های مختلفی مانند هوش مصنوعی و یادگیری ماشین (AI & ML)، تحلیل داده و آمار، توسعه وب (با فریمورک‌هایی مانند جنگو و فلسک) و اتوماسیون (اسکریپت‌نویسی) کاربرد گسترده‌ای دارد. 
      🔹 مزایا و معایب پایتون: مزایا شامل یادگیری آسان، خوانایی بالا و جامعه کاربری بزرگ است. معایب آن سرعت اجرای پایین‌تر (نسبت به C++ یا Java) و مصرف بیشتر حافظه است که در کارهای با عملکرد بالا باید در نظر گرفته شود.
      `,
    sections: [
      { title: 'مقدمه', lessonCount: 4, totalDuration: '03:41:15', lessons: [{ title: 'مروری بر محتوای دوره', duration: '03:11' }, { title: 'چرا پایتون؟', duration: '03:11' }, { title: 'چطوری از این دوره بهتر استفاده کنم؟', duration: '03:11' }, { title: 'چطوری از این دوره بهتر استفاده کنم؟', duration: '03:11', isFree: true },] },
      { title: 'بخش دوم: مبانی پایتون', lessonCount: 2, totalDuration: '01:15:30', lessons: [{ title: 'متغیرها و انواع داده', duration: '45:10' }, { title: 'ساختارهای کنترلی', duration: '30:20' },] },
      { title: 'بخش سوم: توابع و ماژول‌ها', lessonCount: 3, totalDuration: '02:05:00', lessons: [{ title: 'تعریف تابع', duration: '50:00' }, { title: 'ماژول‌های استاندارد', duration: '40:00' }, { title: 'نصب پکیج با pip', duration: '35:00' },] }
    ]
  });


  // =======================================================
  // توابع چرخه حیات (Lifecycle Hooks)
  // =======================================================

  ngAfterViewInit(): void {
    // نیازی به فراخوانی در اینجا نیست، زیرا initThreeJs در playVideo فراخوانی می‌شود
  }

  ngOnDestroy(): void {
    this.disposeThreeJs();
  }

  // =======================================================
  // منطق Three.js (انیمیشن و آواتار)
  // =======================================================

  private initThreeJs(): void {
    if (!this.threeContainer) return;

    this.scene = new THREE.Scene();
    // **رنگ اولیه پس‌زمینه (مثلاً به آبی روشن)**
    this.scene.background = new THREE.Color("#93C5FD"); 

    const container = this.threeContainer.nativeElement as HTMLElement;
    const width = container.clientWidth;
    const height = container.clientHeight;

    this.camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100); 
    this.camera.position.set(0, 1.5, 3); // تنظیم موقعیت دوربین

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); // alpha: true برای شفافیت
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(window.devicePixelRatio); 
    this.renderer.setClearColor(0x000000, 0); // پس‌زمینه شفاف (اگرچه background تنظیم شده، این خط برای اطمینان از شفافیت canvas قبل از جایگزینی background است)
    container.appendChild(this.renderer.domElement);

    // چراغ‌ها
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8); 
    this.scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.5);
    directionalLight.position.set(3, 5, 3);
    this.scene.add(directionalLight);

    this.loadAvatar();

    window.addEventListener('resize', this.onWindowResize.bind(this));
    this.animate();
  }


  private loadAvatar(): void {
    const loader = new GLTFLoader();
    // فرض: فایل Robot.glb در پوشه src/assets قرار دارد
    const modelPath = 'assets/Robot.glb'; 
    
    console.log(`DEBUG: Attempting to load model from: ${modelPath}`); 

    loader.load(
      modelPath,
      (gltf: GLTF) => { 
        const loadedMesh = gltf.scene; 
        this.avatarMesh = loadedMesh; 
        
        loadedMesh.position.y = 0; // تنظیم ارتفاع آواتار
        // **افزایش مقیاس آواتار**
        loadedMesh.position.set(0.0, 0, 0); 
        loadedMesh.scale.set(1.3, 1.3, 1.3); 
        this.scene.add(loadedMesh); 
        
        // 1. Animation Mixer & Actions (انیمیشن‌های بدنی)
        if (gltf.animations.length > 0) {
          this.animationMixer = new THREE.AnimationMixer(loadedMesh); 
          gltf.animations.forEach((clip) => {
              this.actions[clip.name] = this.animationMixer!.clipAction(clip);
          });
          console.log("🎬 Available animations:", Object.keys(this.actions));
          this.playAnimation('0', 0); // پخش انیمیشن سکون پیش‌فرض (بدون Fade)
        }
        
        // 2. Morph Targets (Shape Keys - حالات چهره)
        loadedMesh.traverse((child) => {
          // برای جلوگیری از خطای TypeScript، از type casting استفاده می‌کنیم
          if ((child as THREE.Mesh).isMesh && (child as THREE.Mesh).morphTargetInfluences) {
            this.morphMesh = child as THREE.Mesh;
            console.log("🎭 Morph Targets:", this.morphMesh.morphTargetDictionary);
          }
        });

        console.log("INFO: Robot.glb loaded successfully.");
        
        // تنظیم رنگ پس‌زمینه آواتار
        this.setAvatarBackgroundColor("#93C5FD"); 
        
      },
      (xhr: ProgressEvent) => { 
        console.log(`INFO: ${Math.round(xhr.loaded / xhr.total * 100)}% loaded`);
      },
      (error: any) => { 
        console.error('FATAL ERROR: Failed to load GLB model:', error);
        // Fallback: یک مکعب قرمز در صورت عدم موفقیت در بارگذاری مدل
        const geometry = new THREE.BoxGeometry(1, 1, 1);
        const material = new THREE.MeshPhongMaterial({ color: 0xff0000 });
        this.avatarMesh = new THREE.Mesh(geometry, material);
        this.avatarMesh.position.y = 1;
        this.scene.add(this.avatarMesh);
      }
    );
  }

  /**
   * تابع حلقه انیمیشن.
   */
  private animate = () => {
    requestAnimationFrame(this.animate);
    const delta = this.clock.getDelta();

    if (this.renderer && this.camera) {
      if (this.animationMixer) {
          this.animationMixer.update(delta);
      }
      this.renderer.render(this.scene, this.camera);
    }
  }

  /**
   * مدیریت تغییر اندازه صفحه.
   */
  private onWindowResize(): void {
    if (this.threeContainer && this.camera && this.renderer) {
      const container = this.threeContainer.nativeElement as HTMLElement;
      this.camera.aspect = container.clientWidth / container.clientHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(container.clientWidth, container.clientHeight);
    }
  }

  /**
   * پاکسازی Three.js.
   */
  private disposeThreeJs(): void {
    if (this.renderer) {
      this.renderer.dispose();
      // حذف canvas از DOM
      if (this.threeContainer && this.renderer.domElement.parentNode) {
        this.threeContainer.nativeElement.removeChild(this.renderer.domElement);
      }
    }
    window.removeEventListener('resize', this.onWindowResize.bind(this));
    // سایر موارد پاکسازی (صحنه، هندسه‌ها، متریال‌ها)
  }

  /**
   * پخش انیمیشن بدنی آواتار بر اساس نام، با محو تدریجی.
   * @param name نام کلیپ انیمیشن
   * @param duration مدت زمان محو شدن به ثانیه (پیش‌فرض 0 برای تغییر فوری)
   */
  public playAnimation(name: string, duration: number = 0) {
    const nextAction = this.actions[name];
    if (!nextAction || !this.animationMixer) {
        console.warn("⛔ Animation not found or Mixer not ready:", name);
        return;
    }
    
    // اگر همان انیمیشن فعال است، کاری نکنید 
    if (this.activeAction === nextAction) {
        if (duration === 0) {
            nextAction.stop().reset().play();
        }
        return; 
    }

    if (this.activeAction) {
        // محو کردن انیمیشن قبلی
        this.activeAction.fadeOut(duration);
    }
    
    // اجرای انیمیشن جدید
    nextAction
        .reset() 
        .setLoop(THREE.LoopRepeat, Infinity) 
        .setEffectiveWeight(1) 
        .fadeIn(duration)      
        .play();

    this.activeAction = nextAction;
    console.log(`▶️ Fading (${duration}s) to animation: ${name}`);
  }


  /**
   * تنظیم حالات چهره آواتار (Shape Keys).
   * @param name نام Shape Key (مثلاً 'Happy', 'Basic', 'Blink')
   */
  public setExpression(name: string) {
    if (!this.morphMesh || !this.morphMesh.morphTargetDictionary || !this.morphMesh.morphTargetInfluences) return;
    
    const dict = this.morphMesh.morphTargetDictionary;
    const infl = this.morphMesh.morphTargetInfluences;
    
    // صفر کردن همه حالات چهره
    for (let i = 0; i < infl.length; i++) infl[i] = 0;
    
    // تنظیم حالت چهره مورد نظر
    if (dict[name] !== undefined) infl[dict[name]] = 1;
    console.log("😎 Expression set:", name);
  }
  
  /**
   * انتخاب انیمیشن بعدی گفتار به صورت چرخشی (Cycling).
   */
  private getNextSpeakingAnimation(): string {
    const availableAnims = this.speakingAnimations.filter(name => this.actions[name]);
    
    if (availableAnims.length === 0) return '0'; 
    
    const nextAnim = availableAnims[this.nextSpeakingAnimIndex];
    
    this.nextSpeakingAnimIndex = (this.nextSpeakingAnimIndex + 1) % availableAnims.length;
    
    return nextAnim;
  }
  
  /**
   * تغییر رنگ پس‌زمینه صحنه (پشت آواتار).
   * @param color رنگ جدید به صورت شیء THREE.Color یا رشته هگزادسیمال (مثلاً 0x00ff00 یا '#00ff00').
   */
public setAvatarBackgroundColor(color: THREE.Color | string | number) {
  if (!this.scene) {
    console.warn("⛔ Three.js scene not initialized yet.");
    return;
  }

  // اگر رنگ با شفافیت کامل باشد، background را تنظیم می‌کنیم.
  // اگر از رشته یا عدد استفاده شده باشد، به THREE.Color تبدیل می‌کنیم.
  this.scene.background = color instanceof THREE.Color ? color : new THREE.Color(color);
  console.log(`🖼️ Scene background color set to: ${this.scene.background.getHexString()}`);
}



  // =======================================================
  // توابع کمکی برای Template (Getters)
  // =======================================================
  
  /**
   * دسترسی به لیست بخش‌های درس برای نمایش در Template
   */
  getLessonChunks(): string[] {
    return this.lessonChunks();
  }

  /**
   * بررسی می‌کند آیا پخش‌کننده صوتی آماده ادامه پخش (Resume) است یا خیر.
   */
  isPlayerReadyAndStopped(): boolean {
    return this.audioPlayer !== null && !this.audioPlayer.ended && this.audioPlayer.paused;
  }

  /**
   * برمی‌گرداند متن بخش فعلی درس که در حال پخش است.
   */
  getCurrentLessonChunkText(): string {
    const chunks = this.lessonChunks();
    const index = this.currentChunkIndex();
    if (chunks.length > 0 && index >= 0 && index < chunks.length) {
      return chunks[index];
    }
    return '... در حال بارگذاری متن درس ...';
  }

  /**
   * تبدیل ثانیه به فرمت زمان (مثلاً 04:00).
   */
  formatTime(seconds: number): string {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    const formattedMinutes = String(minutes).padStart(2, '0');
    const formattedSeconds = String(remainingSeconds).padStart(2, '0');
    return `${formattedMinutes}:${formattedSeconds}`;
  }

  // =======================================================
  // توابع مدیریت UI
  // =======================================================

  selectTab(tab: string) { this.activeTab.set(tab); }
  toggleSection(index: number) { this.expandedSection.set(this.expandedSection() === index ? null : index); }
  
  // --- توابع جدید برای ریسپانسیو موبایل ---
  setActiveMobileTab(tab: 'whiteboard' | 'chunks' | 'chat') { 
    this.activeMobileTab.set(tab); 
  }
  
  toggleMobileMenu() {
      console.log('Mobile menu toggled (UI state not implemented for simplicity).');
      // در اینجا منطق نمایش/پنهان‌سازی منوی اصلی موبایل قرار می‌گیرد
  }
  // ----------------------------------------
  
  closeVideo() { 
    this.isFullScreenVideo.set(false); 
    document.body.style.overflow = 'auto'; 
    this.disposeThreeJs(); 
  }

  // =======================================================
  // منطق اصلی پخش صوتی درس
  // =======================================================

  /**
   * پخش یک بخش خاص از درس بر اساس شاخص.
   * @param index شاخص بخش مورد نظر در lessonChunks
   */
  playSpecificChunk(index: number) {
    if (index === this.currentChunkIndex() && this.isAudioPlaying()) {
      console.log(`INFO: Chunk ${index} is already playing.`);
      return;
    }
    
    const chunks = this.lessonChunks();
    if (index >= 0 && index < chunks.length) {
      this.currentChunkIndex.set(index);
      this.nextLesson(index, false); // شروع پخش از این بخش، بدون افزایش شاخص در nextLesson
    } else {
      console.error(`ERROR: Invalid chunk index: ${index}`);
    }
  }


  /**
   * شروع پخش صوتی درس به صورت تمام صفحه.
   */
  playVideo() {
    if (this.isAudioPlaying() || this.isFullScreenVideo()) return;

    this.isFullScreenVideo.set(true);
    document.body.style.overflow = 'hidden';

    if (this.lessonChunks().length === 0) {
      const fullText = this.course().currentLessonText;
      
      // **افزودن پیام معرفی دستیار AI**
      const introText = 'سلام! من دستیار آموزشی هوش مصنوعی این دوره هستم. در این بخش قصد دارم مفاهیم پایه پایتون را برای شما مرور کنم. بیایید شروع کنیم.';
      
      // جدا کردن متن درس اصلی
      const contentChunks = fullText.split('🔹')
        .filter((c: string) => c.trim().length > 0)
        .map(c => '🔹 ' + c.trim());
        
      // ترکیب متن معرفی با بخش‌های درس
      const allChunks = [introText, ...contentChunks]; 
      
      this.lessonChunks.set(allChunks);
      this.currentChunkIndex.set(0); // شروع از بخش معرفی
    }

    // راه اندازی آواتار
    setTimeout(() => {
      this.initThreeJs();
    }, 0); 

    this.nextLesson(this.currentChunkIndex(), true); // شروع از بخش فعلی (که اکنون معرفی است)
  }

  /**
   * پخش بخش بعدی از درس.
   * @param index شاخص بخش برای پخش
   * @param isSequential آیا این فراخوانی برای پخش خودکار بخش‌های بعدی است؟ (false برای فراخوانی مستقیم)
   */
  nextLesson(index: number, isSequential: boolean = true) {
    const chunks = this.lessonChunks();
    if (index >= chunks.length) {
      this.chatHistory.update(history => [...history, {
        sender: 'ai', message: '✅ آموزش صوتی این بخش به پایان رسید. برای سؤالات بیشتر آماده‌ام.', timestamp: new Date()
      }]);
      this.isAudioPlaying.set(false);
      this.playAnimation('0', 0.5); // انیمیشن سکون (با Fade Out)
      this.setExpression('Basic'); // حالت عادی چهره
      return;
    }

    // اگر از طریق playSpecificChunk فراخوانی نشده باشد، شاخص را به‌روز کن
    if (isSequential) {
      this.currentChunkIndex.set(index);
    }
    
    const textToRead = chunks[index];

    console.log(`INFO: Requesting TTS for chunk ${index + 1}/${chunks.length}`);

    this.http.post<{ tts_url?: string }>(`${FLASK_BASE_URL}/api/gemini-tts-start`, {
      text_to_read: textToRead
    }).subscribe({
      next: (res) => {
        this.chatHistory.update(history => [...history, {
          sender: 'ai', message: `▶️ پخش بخش ${index + 1}: ${textToRead.substring(0, 60)}...`, timestamp: new Date()
        }]);

        if (res.tts_url) {
          this.readTextAloud(res.tts_url, isSequential); // autoNext = isSequential
        }
      },
      error: (err) => {
        console.error("API Error: Failed to start TTS.", err);
        this.chatHistory.update(history => [...history, {
          sender: 'ai', message: 'خطا در شروع پخش صوتی. (اتصال به سرور Flask را بررسی کنید)', timestamp: new Date()
        }]);
        this.readTextAloud('/assets/tts_audio/placeholder-tts.mp3', isSequential);
      }
    });
  }

  /**
   * تغییر زمان پخش بر اساس نوار پیشرفت (Scrubbing).
   */
  seekTo(event: Event) {
    const target = event.target as HTMLInputElement;
    const seekTime = parseFloat(target.value);
    
    if (this.audioPlayer && !isNaN(seekTime)) {
      this.audioPlayer.currentTime = seekTime;
      this.currentTime.set(seekTime);
    }
  }

  /**
   * تابع اصلی برای پخش فایل صوتی. (با کنترل آواتار)
   */
  readTextAloud(ttsUrl: string, autoNext: boolean = false) {
    if (this.audioPlayer) {
      this.audioPlayer.pause();
      this.audioPlayer.onended = null;
      this.audioPlayer.onerror = null;
      this.audioPlayer.onloadedmetadata = null; 
      this.audioPlayer.ontimeupdate = null; 
      this.audioPlayer = null;
    }

    const flaskTtsUrl = `${FLASK_BASE_URL}${ttsUrl}`;
    this.audioPlayer = new Audio(flaskTtsUrl);

    this.audioPlayer.onloadedmetadata = () => {
      this.duration.set(this.audioPlayer!.duration);
      this.currentTime.set(this.audioPlayer!.currentTime);
    };

    this.audioPlayer.ontimeupdate = () => {
      this.currentTime.set(this.audioPlayer!.currentTime);
    };
    
    this.audioPlayer.play()
      .then(() => {
        this.isAudioPlaying.set(true);
        // ** کنترل آواتار: شروع انیمیشن چرخشی با Fade In **
        const nextAnim = this.getNextSpeakingAnimation(); 
        this.playAnimation(nextAnim, 0.5); // Fade In
        this.setExpression('Happy');
        console.log(`Audio started successfully. Source: ${flaskTtsUrl}`);
      })
      .catch(error => {
        console.error("AUDIO PLAYBACK BLOCKED (Autoplay):", error);
        this.isAudioPlaying.set(false);
        this.chatHistory.update(history => [...history, {
          sender: 'ai', message: 'مرورگر پخش خودکار صدا را مسدود کرده است. لطفاً برای فعال‌سازی، یک بار روی صفحه کلیک کرده و دوباره تلاش کنید.', timestamp: new Date()
        }]);
      });

    this.audioPlayer.onended = () => {
      this.isAudioPlaying.set(false);
      this.audioPlayer = null;
      // ** کنترل آواتار: توقف انیمیشن (بازگشت به '0') با Fade Out **
      this.playAnimation('0', 0.5); // Fade Out
      this.setExpression('Basic');
      if (autoNext) {
        this.nextLesson(this.currentChunkIndex() + 1, true); // پخش بخش بعدی
      } else {
        console.log("Finished playing AI chat response.");
      }
    };

    this.audioPlayer.onerror = () => {
      this.isAudioPlaying.set(false);
      this.audioPlayer = null;
      // ** کنترل آواتار در صورت خطا **
      this.playAnimation('0', 0.5); // Fade Out
      this.setExpression('Basic');
      console.error('Audio load error on:', flaskTtsUrl);
    };
  }

  /**
   * مدیریت دکمه اصلی پخش/مکث/ادامه.
   */
  togglePlayback() {
    if (this.isRecording()) return; 
    
    if (this.isAudioPlaying()) {
      this.audioPlayer?.pause();
      this.isAudioPlaying.set(false);
      this.playAnimation('0', 0.5); // Fade Out به سکون
      this.setExpression('Basic');
    } else if (this.isPlayerReadyAndStopped()) {
      this.audioPlayer?.play()
        .then(() => {
          this.isAudioPlaying.set(true);
          // ** هنگام ادامه پخش - استفاده از انیمیشن چرخشی با Fade In **
          const nextAnim = this.getNextSpeakingAnimation(); 
          this.playAnimation(nextAnim, 0.5); // Fade In
          this.setExpression('Happy');
        })
        .catch(e => console.error("Resume failed:", e));
    } else {
      this.nextLesson(this.currentChunkIndex(), true); // شروع یا ادامه از بخش فعلی
    }
  }

  // =======================================================
  // منطق ضبط صدا
  // =======================================================

  /**
   * شروع یا توقف ضبط صدا از میکروفون.
   */
  toggleVoiceRecording() {
    if (this.isRecording()) {
      this.stopRecording();
    } else {
      if (this.isAudioPlaying()) {
        this.audioPlayer?.pause();
        this.isAudioPlaying.set(false);
        this.playAnimation('0', 0.5); // Fade Out
        this.setExpression('Basic');
      }
      this.startRecording();
    }
  }

  private async startRecording() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: 'audio/webm' });
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      this.mediaRecorder.onstop = () => {
        this.processRecordedAudio();
      };

      this.mediaRecorder.start();
      this.isRecording.set(true);
      // حالت چهره را هنگام شروع ضبط به Angry تغییر دهید
      this.setExpression('Angry'); 
      this.chatHistory.update(history => [...history, { sender: 'ai', message: '🎙️ در حال ضبط... برای ارسال، دوباره دکمه میکروفون را بزنید.', timestamp: new Date() }]);

    } catch (err) {
      console.error('Could not start recording:', err);
      this.chatHistory.update(history => [...history, { sender: 'ai', message: 'خطا: دسترسی به میکروفون مسدود شده است.', timestamp: new Date() }]);
    }
  }

  private stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.isRecording.set(false);
      this.stream?.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
  }

  private processRecordedAudio() {
    if (this.audioChunks.length === 0) return;

    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice_query.webm');

    // حالت چهره را هنگام شروع پردازش صدا به Angry تغییر دهید
    this.setExpression('Angry'); 
    this.chatHistory.update(history => [...history, { sender: 'user', message: '... (در حال تبدیل ویس به متن)', timestamp: new Date() }]);

    this.http.post<{ transcript: string }>(`${FLASK_BASE_URL}/api/whisper-stt`, formData).subscribe({
      next: (res) => {
        const transcript = res.transcript.trim();
        if (transcript) {
          this.sendMessage(transcript, true); // true = isVoiceQuery
        } else {
          this.chatHistory.update(history => [...history, { sender: 'ai', message: 'صدای واضحی تشخیص داده نشد. لطفاً دوباره تلاش کنید.', timestamp: new Date() }]);
          // بازگشت به حالت عادی در صورت خطا
          this.setExpression('Basic');
        }
      },
      error: (err) => {
        console.error("Whisper API Error:", err);
        this.chatHistory.update(history => [...history, { sender: 'ai', message: 'خطا در سرویس تبدیل صدا به متن.', timestamp: new Date() }]);
        // بازگشت به حالت عادی در صورت خطا
        this.setExpression('Basic');
      }
    });
  }

  // =======================================================
  // منطق چت‌بات
  // =======================================================

  /**
   * ارسال پیام به چت‌بات و دریافت پاسخ صوتی.
   */
  // src/app/app.component.ts

// ... (در داخل کلاس AppComponent)

  /**
   * ارسال پیام به چت‌بات و دریافت پاسخ از Gemini API.
   */
/**
 * ارسال پیام به بک‌اند Flask و دریافت پاسخ.
 */
sendMessage(message: string = this.currentChatInput(), isVoiceQuery: boolean = false) {
  if (!message.trim()) return;

  // توقف پخش صوتی فعلی
  if (this.isAudioPlaying()) {
    this.audioPlayer?.pause();
    this.isAudioPlaying.set(false);
    this.playAnimation('0', 0.5); 
    this.setExpression('Basic');
  }

  const lessonText = this.course().currentLessonText;

  // مدیریت پیام کاربر در تاریخچه چت (برای سوالات صوتی و متنی)
  if (isVoiceQuery) {
      this.chatHistory.update(history => {
          const lastMessage = history[history.length - 1];
          if (lastMessage && lastMessage.sender === 'user' && lastMessage.message.includes('در حال تبدیل ویس به متن')) {
              lastMessage.message = message;
          } else {
              history.push({ sender: 'user', message: message, timestamp: new Date() });
          }
          return [...history];
      });
  } else {
      this.chatHistory.update(history => [...history, { sender: 'user', message: message, timestamp: new Date() }]);
      this.currentChatInput.set('');
  }
  
  // تغییر حالت چهره به حالت "در حال پردازش"
  this.setExpression('Angry'); 

  // ارسال درخواست به بک‌اند Flask
  this.http.post<{ response: string, tts_url?: string }>(`${FLASK_BASE_URL}/api/gemini-query`, {
    prompt: message,    // <-- فقط سوال کاربر
    context: lessonText // <-- فقط متن درس
  }).subscribe({
    next: (res) => {
      this.chatHistory.update(history => [...history, { sender: 'ai', message: res.response, timestamp: new Date() }]);
      if (res.tts_url) {
        // پخش پاسخ صوتی دریافت شده از بک‌اند
        this.readTextAloud(res.tts_url, false);
      } else {
        // اگر پاسخ صوتی نبود، به حالت عادی برگرد
        this.setExpression('Basic'); 
      }
    },
    error: (err) => {
      console.error("API Error: Failed to get AI response.", err);
      this.chatHistory.update(history => [...history, { sender: 'ai', message: 'خطا: ارتباط با مشاور AI برقرار نشد.', timestamp: new Date() }]);
      // بازگشت به حالت عادی در صورت خطا
      this.setExpression('Basic');
    }
  });
}
  
}