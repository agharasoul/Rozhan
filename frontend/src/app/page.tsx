"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Plus, Camera, X, Image as ImageIcon, Download, User, LogOut, UtensilsCrossed, ShoppingCart, MessageSquare, Trash2, Menu, PanelLeftClose, History, Search, Clock, Volume2, VolumeX, Video } from "lucide-react";
import { useAuth, API_BASE } from "./contexts/AuthContext";
import LoginModal from "./components/LoginModal";
import SimpleVoiceChat from "./components/SimpleVoiceChat";
import SuggestionWidget from "./components/SuggestionWidget";
import VideoChat from "./components/VideoChat";
import Link from "next/link";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  image?: string;
}

interface ChatSession {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export default function Home() {
  const { user, token, isLoggedIn, logout, isLoading: authLoading } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showAttach, setShowAttach] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  
  // Chat History Sidebar
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [needsRetry, setNeedsRetry] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightTerm, setHighlightTerm] = useState(''); // کلمه جستجو شده برای highlight
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0); // شماره نتیجه فعلی
  const [matchIds, setMatchIds] = useState<string[]>([]); // لیست id پیام‌های دارای کلمه
  const highlightRefs = useRef<Map<string, HTMLDivElement>>(new Map()); // ref برای همه پیام‌های match
  const [speakingId, setSpeakingId] = useState<string | null>(null); // id پیامی که در حال خوندنه
  const [showVideoChat, setShowVideoChat] = useState(false); // 📹 چت ویدیویی
  const [selectedVoice, setSelectedVoice] = useState('Kore'); // صدای پیش‌فرض Gemini
  const [showVoiceMenu, setShowVoiceMenu] = useState(false);
  
  // لیست صداها - Gemini TTS
  const voices = [
    { id: 'Kore', name: '👩 کوره (طبیعی)', gender: 'زن' },
    { id: 'Aoede', name: '👩 آئودی (ملایم)', gender: 'زن' },
    { id: 'Leda', name: '👩 لدا (شاد)', gender: 'زن' },
    { id: 'Zephyr', name: '👩 زفیر (حرفه‌ای)', gender: 'زن' },
    { id: 'Puck', name: '👨 پاک (صمیمی)', gender: 'مرد' },
    { id: 'Charon', name: '👨 کارون (رسمی)', gender: 'مرد' },
    { id: 'Fenrir', name: '👨 فنریر (قوی)', gender: 'مرد' },
    { id: 'Orus', name: '👨 اوروس (آرام)', gender: 'مرد' },
  ];
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [videoChatAnalysis, setVideoChatAnalysis] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const streamRef = useRef<MediaStream | null>(null);
  const videoChatRef = useRef<HTMLVideoElement>(null);
  const videoChatStreamRef = useRef<MediaStream | null>(null);
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const [showInstall, setShowInstall] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  
  // برای جلوگیری از race condition
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef<number>(0);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadSessions = async (query?: string) => {
    if (!token) return;
    setLoadingSessions(true);
    try {
      const url = query?.trim() 
        ? `${API_BASE}/chat/sessions?q=${encodeURIComponent(query.trim())}`
        : `${API_BASE}/chat/sessions`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (e) {
      console.error('Error loading sessions:', e);
    } finally {
      setLoadingSessions(false);
    }
  };

  // Load sessions on login (فقط یکبار)
  const hasLoadedRef = useRef(false);
  useEffect(() => {
    if (isLoggedIn && token && !hasLoadedRef.current) {
      hasLoadedRef.current = true;
      loadSessions();
    }
    if (!isLoggedIn) {
      hasLoadedRef.current = false;
      setSessions([]);
      setCurrentSessionId(null);
    }
  }, [isLoggedIn]);

  // جستجوی real-time با debounce (فقط وقتی sidebar بازه)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    if (!sidebarOpen || !token) return;
    
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    searchTimeoutRef.current = setTimeout(() => {
      loadSessions(searchQuery);
    }, 400);
    
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery, sidebarOpen]);

  // محاسبه لیست پیام‌های دارای کلمه جستجو
  useEffect(() => {
    if (highlightTerm && messages.length > 0) {
      const ids = messages
        .filter(m => m.content.toLowerCase().includes(highlightTerm.toLowerCase()))
        .map(m => m.id);
      setMatchIds(ids);
      setCurrentMatchIndex(0);
    } else {
      setMatchIds([]);
      setCurrentMatchIndex(0);
    }
  }, [messages, highlightTerm]);

  // Scroll به نتیجه فعلی
  useEffect(() => {
    if (matchIds.length > 0 && highlightTerm) {
      const currentId = matchIds[currentMatchIndex];
      const element = highlightRefs.current.get(currentId);
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
    }
  }, [currentMatchIndex, matchIds, highlightTerm]);

  // توابع navigation
  const goToNextMatch = () => {
    if (matchIds.length > 0) {
      setCurrentMatchIndex(prev => (prev + 1) % matchIds.length);
    }
  };

  const goToPrevMatch = () => {
    if (matchIds.length > 0) {
      setCurrentMatchIndex(prev => (prev - 1 + matchIds.length) % matchIds.length);
    }
  };

  // 🔊 Text-to-Speech برای کم‌بیناها (با پشتیبانی فارسی)
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  const speakText = async (text: string, msgId: string) => {
    // اگه در حال خوندن همین پیامه، متوقف کن
    if (speakingId === msgId) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setSpeakingId(null);
      return;
    }

    // متوقف کردن هر صدای قبلی
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    setSpeakingId(msgId);

    try {
      // درخواست به backend برای TTS
      const response = await fetch(`${API_BASE}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 2000), voice: selectedVoice })
      });

      const data = await response.json();

      if (data.success && data.audio) {
        // پخش صدا
        const audio = new Audio(data.audio);
        audioRef.current = audio;
        
        audio.onended = () => {
          setSpeakingId(null);
          audioRef.current = null;
        };
        
        audio.onerror = () => {
          setSpeakingId(null);
          audioRef.current = null;
        };

        await audio.play();
      } else {
        setSpeakingId(null);
      }
    } catch (error) {
      console.error('TTS error:', error);
      setSpeakingId(null);
    }
  };

  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setSpeakingId(null);
  };

  // Cleanup: متوقف کردن صدا وقتی کامپوننت unmount میشه
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
    };
  }, []);

  
  const loadSessionMessages = async (sessionId: number, searchTerm?: string) => {
    if (!token) return;
    
    // افزایش requestId برای باطل کردن درخواست‌های قبلی
    requestIdRef.current += 1;
    
    // لغو درخواست چت در حال انتظار
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    
    try {
      const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      const loadedMessages = (data.messages || []).map((m: any) => ({
        id: m.id.toString(),
        role: m.role as "user" | "assistant",
        content: m.content,
        image: m.image_url
      }));
      
      setMessages(loadedMessages);
      setCurrentSessionId(sessionId);
      setSidebarOpen(false);
      
      // ذخیره کلمه جستجو برای highlight
      if (searchTerm?.trim()) {
        setHighlightTerm(searchTerm.trim());
      } else {
        setHighlightTerm('');
      }
      
      // اگه آخرین پیام از کاربر بود، فلگ بذار که نیاز به جواب داره
      if (loadedMessages.length > 0) {
        const lastMessage = loadedMessages[loadedMessages.length - 1];
        if (lastMessage.role === 'user') {
          setNeedsRetry(true);
        } else {
          setNeedsRetry(false);
        }
      } else {
        setNeedsRetry(false);
      }
    } catch (e) {
      console.error('Error loading session:', e);
    }
  };
  
  // گرفتن جواب برای آخرین پیام بدون جواب
  const retryLastMessage = async () => {
    if (!currentSessionId || messages.length === 0) return;
    
    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role !== 'user') return;
    
    setIsLoading(true);
    setNeedsRetry(false);
    
    requestIdRef.current += 1;
    const thisRequestId = requestIdRef.current;
    
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const controller = new AbortController();
      abortControllerRef.current = controller;
      
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ 
          message: lastMessage.content, 
          image: lastMessage.image,
          session_id: currentSessionId 
        }),
        signal: controller.signal,
      });
      
      const data = await res.json();
      
      if (thisRequestId !== requestIdRef.current) {
        return;
      }
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      if (error.name !== 'AbortError' && thisRequestId === requestIdRef.current) {
        console.error("Retry error:", error);
        setNeedsRetry(true); // اگه خطا شد دوباره نشون بده
      }
    } finally {
      if (thisRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
      abortControllerRef.current = null;
    }
  };

  const deleteSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!token) return;
    try {
      await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      loadSessions();
    } catch (e) {
      console.error('Error deleting session:', e);
    }
  };

  const startNewChat = () => {
    // افزایش requestId برای باطل کردن درخواست‌های قبلی
    requestIdRef.current += 1;
    // لغو درخواست چت در حال انتظار
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setNeedsRetry(false);
    
    setCurrentSessionId(null);
    setMessages([]);
    setSidebarOpen(false);
    setHighlightTerm('');
    setSearchQuery('');
    setMatchIds([]);
    setCurrentMatchIndex(0);
  };

  useEffect(() => {
    // تشخیص موبایل
    const checkMobile = () => {
      setIsMobile(/iPhone|iPad|iPod|Android/i.test(navigator.userAgent));
    };
    checkMobile();
    
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e);
      setShowInstall(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (installPrompt) {
      installPrompt.prompt();
      const result = await installPrompt.userChoice;
      if (result.outcome === "accepted") {
        setShowInstall(false);
      }
      setInstallPrompt(null);
    } else {
      // برای iOS و مرورگرهایی که beforeinstallprompt ندارن
      alert("برای نصب:\n\n📱 Android: منوی مرورگر ⋮ → Add to Home screen\n\n🍎 iPhone: دکمه Share → Add to Home Screen");
    }
  };

  const sendMessage = async () => {
    if (!input.trim() && !selectedImage) return;

    // ذخیره مقادیر قبل از پاک کردن
    const messageText = input;
    const messageImage = selectedImage;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      image: messageImage || undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSelectedImage(null);
    setIsLoading(true);
    
    // ذخیره requestId برای چک کردن بعداً
    requestIdRef.current += 1;
    const thisRequestId = requestIdRef.current;
    const requestSessionId = currentSessionId;
        
    // لغو درخواست قبلی اگه وجود داره
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    try {
      // ارسال به Backend با توکن (اگر لاگین باشد)
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
            
      const controller = new AbortController();
      abortControllerRef.current = controller;
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ 
          message: messageText, 
          image: messageImage,
          session_id: requestSessionId 
        }),
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);

      const data = await res.json();
      
      // فقط اگه این درخواست هنوز معتبره، جواب رو نشون بده
      if (thisRequestId !== requestIdRef.current) {
        return;
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setNeedsRetry(false);
      
      // اگر session جدید ساخته شد، ذخیره کن و لیست رو آپدیت کن
      if (data.session_id && data.session_id !== requestSessionId) {
        setCurrentSessionId(data.session_id);
        loadSessions();
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return;
      }
      // فقط اگه این درخواست هنوز معتبره، خطا رو نشون بده
      if (thisRequestId !== requestIdRef.current) {
        return;
      }
      console.error("Chat error:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "خطا در اتصال به سرور",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      // فقط اگه این درخواست هنوز معتبره، loading رو بردار
      if (thisRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
      abortControllerRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result as string);
        setShowAttach(false);
      };
      reader.readAsDataURL(file);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // انتخاب بهترین فرمت پشتیبانی‌شده
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
        ? 'audio/webm' 
        : MediaRecorder.isTypeSupported('audio/mp4') 
          ? 'audio/mp4' 
          : 'audio/wav';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // متوقف کردن stream
        stream.getTracks().forEach(track => track.stop());
        
        // ساخت فایل صوتی با همان mime type
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        
        // ارسال به سرور برای تبدیل به متن
        await transcribeAudio(audioBlob, mimeType);
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // شمارنده زمان
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (error) {
      alert("دسترسی به میکروفن رد شد");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  };

  const transcribeAudio = async (audioBlob: Blob, mimeType: string) => {
    setIsTranscribing(true);
    try {
      // تبدیل به base64
      const reader = new FileReader();
      const base64Promise = new Promise<string>((resolve) => {
        reader.onloadend = () => {
          const base64 = reader.result as string;
          resolve(base64.split(',')[1]); // حذف prefix
        };
      });
      reader.readAsDataURL(audioBlob);
      const base64Audio = await base64Promise;
      
      // ارسال به Backend
      const response = await fetch(`${API_BASE}/transcribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: base64Audio, mime_type: mimeType }),
      });
      
      const data = await response.json();
      
      if (data.text) {
        setInput(prev => prev ? prev + " " + data.text : data.text);
      }
    } catch (error) {
      console.error("خطا در تبدیل صدا:", error);
    } finally {
      setIsTranscribing(false);
      setRecordingTime(0);
    }
  };

  const openCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: "environment" } 
      });
      streamRef.current = stream;
      setShowCamera(true);
      setShowAttach(false);
      
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }, 100);
    } catch {
      alert("دسترسی به دوربین رد شد");
    }
  };

  const capturePhoto = () => {
    if (videoRef.current) {
      const canvas = document.createElement("canvas");
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx?.drawImage(videoRef.current, 0, 0);
      setSelectedImage(canvas.toDataURL("image/jpeg"));
      closeCamera();
    }
  };

  const closeCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    setShowCamera(false);
  };

  // 🎬 چت تصویری زنده
  const startVideoChat = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: "user", width: 640, height: 480 } 
      });
      videoChatStreamRef.current = stream;
      setShowVideoChat(true);
      setShowAttach(false);
      setVideoChatAnalysis(null);
      
      setTimeout(() => {
        if (videoChatRef.current) {
          videoChatRef.current.srcObject = stream;
        }
      }, 100);
    } catch {
      alert("دسترسی به دوربین رد شد");
    }
  };

  const analyzeVideoFrame = async () => {
    if (!videoChatRef.current || isAnalyzing) return;
    
    setIsAnalyzing(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = videoChatRef.current.videoWidth || 640;
      canvas.height = videoChatRef.current.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      ctx?.drawImage(videoChatRef.current, 0, 0);
      const imageData = canvas.toDataURL("image/jpeg", 0.8);
      
      const response = await fetch(`${API_BASE}/analyze/image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData, mode: 'describe' })
      });
      
      const data = await response.json();
      if (data.success) {
        setVideoChatAnalysis(data.analysis);
      }
    } catch (error) {
      console.error("Video analysis error:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const sendVideoFrame = async () => {
    if (!videoChatRef.current) return;
    
    const canvas = document.createElement("canvas");
    canvas.width = videoChatRef.current.videoWidth || 640;
    canvas.height = videoChatRef.current.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx?.drawImage(videoChatRef.current, 0, 0);
    const imageData = canvas.toDataURL("image/jpeg", 0.8);
    
    setSelectedImage(imageData);
    closeVideoChat();
  };

  const closeVideoChat = () => {
    if (videoChatStreamRef.current) {
      videoChatStreamRef.current.getTracks().forEach(track => track.stop());
    }
    setShowVideoChat(false);
    setVideoChatAnalysis(null);
  };

  return (
    <div className="fixed inset-0 flex bg-[#0d0d0d] text-white overflow-hidden">
      {/* History Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Modern History Sidebar - Slides from RIGHT */}
      <aside 
        className={`fixed top-0 right-0 z-[101] h-full w-80 max-w-[85vw] bg-gradient-to-b from-zinc-900 to-zinc-950 flex flex-col transition-transform duration-300 ease-out shadow-2xl ${
          sidebarOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        dir="rtl"
      >
        {/* Sidebar Header - Gradient */}
        <div className="bg-gradient-to-l from-emerald-600 to-teal-600 p-4 pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                <History className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-bold text-white text-lg">تاریخچه چت</h2>
                <p className="text-white/70 text-xs">{sessions.length} گفتگو</p>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 hover:bg-white/20 rounded-xl transition-colors"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-4">
          <button
            onClick={startNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-3.5 bg-gradient-to-l from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 rounded-xl transition-all text-white font-medium shadow-lg shadow-emerald-500/20"
          >
            <Plus className="w-5 h-5" />
            <span>گفتگوی جدید</span>
          </button>
        </div>

        {/* Search Box - Real-time */}
        <div className="px-4 pb-3">
          <div className="relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="جستجو در تاریخچه..."
              className="w-full bg-zinc-800/50 border border-zinc-700/50 rounded-xl py-2.5 pr-10 pl-4 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50 transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute left-3 top-1/2 -translate-y-1/2 p-1 hover:bg-zinc-700 rounded-full transition-colors"
              >
                <X className="w-3 h-3 text-zinc-400" />
              </button>
            )}
          </div>
        </div>

        {/* Sessions List with Date Groups */}
        <div className="flex-1 overflow-y-auto px-4 pb-4">
          {loadingSessions ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="w-8 h-8 text-zinc-600" />
              </div>
              <p className="text-zinc-500 text-sm">هنوز گفتگویی ندارید</p>
              <p className="text-zinc-600 text-xs mt-1">اولین پیام رو بفرست!</p>
            </div>
          ) : (
            <>
              {/* Group sessions by date */}
              {(() => {
                const now = new Date();
                const today: ChatSession[] = [];
                const yesterday: ChatSession[] = [];
                const thisWeek: ChatSession[] = [];
                const older: ChatSession[] = [];
                
                // فیلتر سمت سرور انجام میشه، اینجا فقط گروه‌بندی
                sessions.forEach(session => {
                  const date = new Date(session.updated_at || session.created_at);
                  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
                  
                  if (diffDays === 0) today.push(session);
                  else if (diffDays === 1) yesterday.push(session);
                  else if (diffDays < 7) thisWeek.push(session);
                  else older.push(session);
                });

                const renderGroup = (title: string, items: ChatSession[], icon: string) => {
                  if (items.length === 0) return null;
                  return (
                    <div key={title} className="mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="text-lg">{icon}</span>
                        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">{title}</span>
                        <div className="flex-1 h-px bg-gradient-to-l from-transparent to-zinc-700" />
                      </div>
                      <div className="space-y-2">
                        {items.map((session) => (
                          <div
                            key={session.id}
                            onClick={() => loadSessionMessages(session.id, searchQuery)}
                            className={`group relative p-3 rounded-xl cursor-pointer transition-all ${
                              currentSessionId === session.id 
                                ? 'bg-emerald-500/20 border border-emerald-500/30' 
                                : 'bg-zinc-800/50 hover:bg-zinc-800 border border-transparent hover:border-zinc-700'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                                currentSessionId === session.id ? 'bg-emerald-500' : 'bg-zinc-700'
                              }`}>
                                <MessageSquare className="w-4 h-4 text-white" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-white truncate">{session.title}</p>
                                <div className="flex items-center gap-2 mt-1">
                                  <Clock className="w-3 h-3 text-zinc-500" />
                                  <span className="text-xs text-zinc-500">
                                    {new Date(session.updated_at || session.created_at).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' })}
                                  </span>
                                  <span className="text-xs text-zinc-600">•</span>
                                  <span className="text-xs text-zinc-500">{session.message_count} پیام</span>
                                </div>
                              </div>
                            </div>
                            <button
                              onClick={(e) => deleteSession(session.id, e)}
                              className="absolute left-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-2 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-all"
                            >
                              <Trash2 className="w-4 h-4 text-red-400" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                };

                const hasResults = today.length + yesterday.length + thisWeek.length + older.length > 0;

                return (
                  <>
                    {searchQuery && !hasResults ? (
                      <div className="text-center py-8">
                        <Search className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                        <p className="text-zinc-500 text-sm">نتیجه‌ای برای "{searchQuery}" یافت نشد</p>
                      </div>
                    ) : (
                      <>
                        {renderGroup('امروز', today, '📅')}
                        {renderGroup('دیروز', yesterday, '📆')}
                        {renderGroup('هفته گذشته', thisWeek, '🗓️')}
                        {renderGroup('قبل‌تر', older, '📁')}
                      </>
                    )}
                  </>
                );
              })()}
            </>
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header - Fixed */}
        <header className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-[#0d0d0d]">
          <div className="flex items-center gap-3">
            {/* History Button - Responsive */}
            {isLoggedIn && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1.5 bg-gradient-to-l from-emerald-600 to-teal-600 rounded-full hover:from-emerald-700 hover:to-teal-700 transition-all shadow-lg shadow-emerald-500/20"
              >
                <History className="w-4 h-4 text-white" />
                <span className="hidden min-[400px]:inline text-xs sm:text-sm text-white font-medium">تاریخچه</span>
                {sessions.length > 0 && (
                  <span className="bg-white/20 text-white text-[10px] sm:text-xs px-1 sm:px-1.5 py-0.5 rounded-full min-w-[18px] sm:min-w-[20px] text-center">
                    {sessions.length}
                  </span>
                )}
              </button>
            )}
            {(showInstall || isMobile) && (
              <button
                onClick={handleInstall}
                className="flex items-center gap-1 px-2 py-1 bg-white text-black rounded-lg text-[10px] sm:text-xs font-medium hover:bg-zinc-200 transition-colors"
              >
                <Download className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                <span className="hidden sm:inline">نصب</span>
              </button>
            )}
            {/* Navigation Links - Hidden on very small screens */}
            <Link
              href="/restaurants"
              className="hidden min-[400px]:flex items-center gap-1 px-2 sm:px-3 py-1.5 bg-zinc-800 rounded-full hover:bg-zinc-700 transition-colors text-xs sm:text-sm"
            >
              <UtensilsCrossed className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span className="hidden sm:inline">رستوران‌ها</span>
            </Link>
            <Link
              href="/cart"
              className="hidden min-[400px]:flex items-center gap-1 px-2 sm:px-3 py-1.5 bg-zinc-800 rounded-full hover:bg-zinc-700 transition-colors text-xs sm:text-sm"
            >
              <ShoppingCart className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span className="hidden sm:inline">سبد</span>
            </Link>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
              {/* 📹 دکمه چت ویدیویی */}
              <button
                onClick={() => setShowVideoChat(true)}
                className="p-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full hover:opacity-90 transition-opacity"
                title="چت ویدیویی"
              >
                <Video className="w-4 h-4 text-white" />
              </button>
              
              <SimpleVoiceChat 
                sessionId={currentSessionId || undefined}
                onMessage={(text, role) => {
                  const newMsg: Message = {
                    id: Date.now().toString(),
                    role,
                    content: text,
                  };
                  setMessages((prev) => [...prev, newMsg]);
                }}
              />
            </div>
        
        {/* User Menu - Responsive */}
        <div className="relative flex-shrink-0">
          {isLoggedIn ? (
            <>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1.5 bg-zinc-800 rounded-full hover:bg-zinc-700 transition-colors"
              >
                <User className="w-4 h-4" />
                <span className="text-xs sm:text-sm max-w-[80px] sm:max-w-[120px] truncate font-medium">
                  {user?.name || (user?.phone ? `کاربر ${user.phone.slice(-4)}` : user?.email?.split('@')[0])}
                </span>
              </button>
              
              {showUserMenu && (
                <div className="absolute left-0 mt-2 w-48 bg-zinc-800 rounded-xl shadow-lg border border-zinc-700 overflow-hidden z-50">
                  <div className="px-4 py-3 border-b border-zinc-700">
                    <p className="text-sm text-white font-medium">{user?.name || 'کاربر'}</p>
                    <p className="text-xs text-zinc-400">{user?.phone || user?.email}</p>
                  </div>
                  <Link
                    href="/profile"
                    onClick={() => setShowUserMenu(false)}
                    className="w-full px-4 py-3 flex items-center gap-2 text-zinc-300 hover:bg-zinc-700/50 transition-colors"
                  >
                    <User className="w-4 h-4" />
                    <span className="text-sm">پروفایل من</span>
                  </Link>
                  <button
                    onClick={() => { logout(); setShowUserMenu(false); }}
                    className="w-full px-4 py-3 flex items-center gap-2 text-red-400 hover:bg-zinc-700/50 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    <span className="text-sm">خروج</span>
                  </button>
                </div>
              )}
            </>
          ) : (
            <button
              onClick={() => setShowLoginModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 rounded-full hover:bg-blue-700 transition-colors text-sm"
            >
              <User className="w-4 h-4" />
              ورود
            </button>
          )}
        </div>
      </header>

      {/* Messages - Scrollable */}
      <main className="flex-1 overflow-y-auto px-4 py-4" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none', WebkitOverflowScrolling: 'touch' }}>
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center px-4">
              <h2 className="text-xl font-medium text-zinc-300 mb-2">سلام، چطور میتونم کمکت کنم؟</h2>
              <p className="text-zinc-500 text-sm">پیام بنویس، عکس بفرست، یا صحبت کن</p>
            </div>
          )}

          {/* ویجت پیشنهاد هوشمند */}
          {messages.length === 0 && token && (
            <SuggestionWidget 
              token={token} 
              onSelect={(food) => setInput(`میخوام ${food} سفارش بدم`)} 
            />
          )}
          
          {(() => {
            // تابع highlight کردن متن
            const highlightText = (text: string) => {
              if (!highlightTerm) return text;
              const regex = new RegExp(`(${highlightTerm})`, 'gi');
              const parts = text.split(regex);
              return parts.map((part, i) => 
                part.toLowerCase() === highlightTerm.toLowerCase() 
                  ? <mark key={i} className="bg-yellow-400 text-black px-1 rounded">{part}</mark>
                  : part
              );
            };

            return messages.map((msg) => {
              const hasMatch = highlightTerm && msg.content.toLowerCase().includes(highlightTerm.toLowerCase());
              const isCurrentMatch = matchIds[currentMatchIndex] === msg.id;
              
              return (
                <div
                  key={msg.id}
                  ref={hasMatch ? (el) => { if (el) highlightRefs.current.set(msg.id, el); } : undefined}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 transition-all ${
                      msg.role === "user"
                        ? "bg-zinc-700 text-white"
                        : "bg-zinc-800/50 text-zinc-100"
                    } ${hasMatch ? "ring-2 shadow-lg" : ""} ${
                      isCurrentMatch 
                        ? "ring-yellow-400 shadow-yellow-400/30 scale-[1.02]" 
                        : hasMatch 
                          ? "ring-yellow-400/30 shadow-yellow-400/10" 
                          : ""
                    }`}
                  >
                    {msg.image && (
                      <img
                        src={msg.image}
                        alt="uploaded"
                        className="max-w-full rounded-lg mb-2 max-h-64 object-cover"
                      />
                    )}
                    <p className="whitespace-pre-wrap leading-relaxed">{highlightText(msg.content)}</p>
                    
                    {/* 🔊 دکمه خواندن برای کم‌بیناها - فقط برای پیام‌های روژان */}
                    {msg.role === "assistant" && (
                      <div className="mt-2 flex items-center gap-2">
                        <button
                          onClick={() => speakText(msg.content, msg.id)}
                          className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg transition-all ${
                            speakingId === msg.id
                              ? "bg-emerald-500 text-white"
                              : "bg-zinc-700/50 text-zinc-400 hover:bg-zinc-700 hover:text-white"
                          }`}
                          title={speakingId === msg.id ? "متوقف کردن" : "خواندن پیام"}
                        >
                          {speakingId === msg.id ? (
                            <>
                              <VolumeX className="w-3.5 h-3.5" />
                              <span>توقف</span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="w-3.5 h-3.5" />
                              <span>بخوان</span>
                            </>
                          )}
                        </button>
                        
                        {/* انتخاب صدا */}
                        <div className="relative">
                          <button
                            onClick={() => setShowVoiceMenu(!showVoiceMenu)}
                            className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-zinc-700/50 text-zinc-400 hover:bg-zinc-700 hover:text-white transition-all"
                            title="انتخاب صدا"
                          >
                            <span>🎤</span>
                            <span className="max-w-[80px] truncate">{voices.find(v => v.id === selectedVoice)?.name.split(' ')[1] || 'صدا'}</span>
                          </button>
                          
                          {showVoiceMenu && (
                            <div className="absolute bottom-full right-0 mb-1 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 min-w-[180px]">
                              <div className="p-2 border-b border-zinc-700">
                                <span className="text-xs text-zinc-400">انتخاب صدا:</span>
                              </div>
                              {voices.map(voice => (
                                <button
                                  key={voice.id}
                                  onClick={() => {
                                    setSelectedVoice(voice.id);
                                    setShowVoiceMenu(false);
                                  }}
                                  className={`w-full px-3 py-2 text-right text-sm flex items-center justify-between hover:bg-zinc-700 transition-colors ${
                                    selectedVoice === voice.id ? 'bg-zinc-700 text-emerald-400' : 'text-zinc-300'
                                  }`}
                                >
                                  <span>{voice.name}</span>
                                  <span className="text-xs text-zinc-500">{voice.gender}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            });
          })()}
          
          {/* نوار navigation جستجو با فلش بالا/پایین */}
          {highlightTerm && matchIds.length > 0 && (
            <div className="flex justify-center sticky bottom-2">
              <div className="flex items-center gap-2 px-3 py-2 bg-zinc-800 rounded-full shadow-lg border border-zinc-700">
                {/* فلش بالا */}
                <button
                  onClick={goToPrevMatch}
                  className="p-2 hover:bg-zinc-700 rounded-full transition-colors"
                  title="نتیجه قبلی"
                >
                  <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>

                {/* شمارنده */}
                <div className="px-3 py-1 bg-yellow-500 text-black rounded-full text-sm font-medium min-w-[60px] text-center">
                  {currentMatchIndex + 1} / {matchIds.length}
                </div>

                {/* فلش پایین */}
                <button
                  onClick={goToNextMatch}
                  className="p-2 hover:bg-zinc-700 rounded-full transition-colors"
                  title="نتیجه بعدی"
                >
                  <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* دکمه بستن */}
                <button
                  onClick={() => {
                    setHighlightTerm('');
                    setSearchQuery('');
                    setMatchIds([]);
                    scrollToBottom();
                  }}
                  className="p-2 hover:bg-red-500/20 rounded-full transition-colors mr-1"
                  title="پاک کردن جستجو"
                >
                  <X className="w-4 h-4 text-red-400" />
                </button>
              </div>
            </div>
          )}

          {/* دکمه ارسال مجدد اگه جواب نگرفته */}
          {needsRetry && !isLoading && (
            <div className="flex justify-center">
              <button
                onClick={retryLastMessage}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-full transition-colors text-sm"
              >
                <Send className="w-4 h-4" />
                دریافت جواب
              </button>
            </div>
          )}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-zinc-800/50 rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                  <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                  <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Camera Modal */}
      {showCamera && (
        <div className="fixed inset-0 bg-black z-50 flex flex-col">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="flex-1 object-cover"
          />
          <div className="absolute bottom-8 left-0 right-0 flex justify-center gap-6">
            <button
              onClick={closeCamera}
              className="w-14 h-14 rounded-full bg-zinc-800 flex items-center justify-center"
            >
              <X className="w-6 h-6" />
            </button>
            <button
              onClick={capturePhoto}
              className="w-16 h-16 rounded-full bg-white flex items-center justify-center"
            >
              <div className="w-12 h-12 rounded-full border-4 border-zinc-900"></div>
            </button>
          </div>
        </div>
      )}

      {/* Video Chat Modal */}
      {showVideoChat && (
        <div className="fixed inset-0 bg-black z-50 flex flex-col">
          <div className="absolute top-4 left-4 right-4 flex justify-between items-center z-10">
            <span className="text-white text-lg font-bold">🎬 چت تصویری</span>
            <button
              onClick={closeVideoChat}
              className="w-10 h-10 rounded-full bg-zinc-800/80 flex items-center justify-center"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <video
            ref={videoChatRef}
            autoPlay
            playsInline
            muted
            className="flex-1 object-cover"
          />
          
          {/* Analysis Result */}
          {videoChatAnalysis && (
            <div className="absolute top-16 left-4 right-4 bg-black/70 rounded-xl p-3 max-h-32 overflow-y-auto">
              <p className="text-sm text-white" dir="rtl">{videoChatAnalysis}</p>
            </div>
          )}
          
          <div className="absolute bottom-8 left-0 right-0 flex justify-center gap-4">
            <button
              onClick={analyzeVideoFrame}
              disabled={isAnalyzing}
              className="px-6 py-3 rounded-full bg-emerald-600 hover:bg-emerald-700 flex items-center gap-2 disabled:opacity-50"
            >
              {isAnalyzing ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              )}
              <span>تحلیل</span>
            </button>
            <button
              onClick={sendVideoFrame}
              className="px-6 py-3 rounded-full bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
            >
              <Send className="w-5 h-5" />
              <span>ارسال به چت</span>
            </button>
          </div>
        </div>
      )}

      {/* Selected Image Preview with Caption hint */}
      {selectedImage && (
        <div className="px-4 py-2 border-t border-zinc-800">
          <div className="max-w-3xl mx-auto flex items-center gap-3">
            <div className="relative flex-shrink-0">
              <img
                src={selectedImage}
                alt="preview"
                className="h-16 w-16 rounded-lg object-cover"
              />
              <button
                onClick={() => setSelectedImage(null)}
                className="absolute -top-2 -right-2 w-5 h-5 bg-zinc-700 rounded-full flex items-center justify-center"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
            <p className="text-xs text-zinc-400" dir="rtl">
              💡 میتونی کپشن یا سوالی درباره عکس بنویسی...
            </p>
          </div>
        </div>
      )}

      {/* Input Area - Fixed */}
      <footer className="flex-shrink-0 border-t border-zinc-800 px-3 py-3 bg-[#0d0d0d]">
        <div className="max-w-2xl mx-auto">
          <div dir="ltr" className="flex items-center gap-2 bg-zinc-800 rounded-2xl p-2">
            {/* Attach Button - LEFT */}
            <div className="relative flex-shrink-0">
              <button
                onClick={() => setShowAttach(!showAttach)}
                className="w-9 h-9 rounded-full hover:bg-zinc-700 flex items-center justify-center transition-colors"
              >
                <Plus className="w-5 h-5 text-zinc-400" />
              </button>
              
              {/* Attach Menu */}
              {showAttach && (
                <div className="absolute bottom-12 left-0 bg-zinc-900 rounded-xl border border-zinc-700 py-2 min-w-[140px] shadow-xl z-50">
                  <button
                    onClick={() => { fileInputRef.current?.click(); setShowAttach(false); }}
                    className="w-full px-3 py-2 hover:bg-zinc-800 flex items-center gap-2 transition-colors"
                  >
                    <ImageIcon className="w-4 h-4 text-zinc-400" />
                    <span className="text-sm">عکس</span>
                  </button>
                  <button
                    onClick={() => { openCamera(); setShowAttach(false); }}
                    className="w-full px-3 py-2 hover:bg-zinc-800 flex items-center gap-2 transition-colors"
                  >
                    <Camera className="w-4 h-4 text-zinc-400" />
                    <span className="text-sm">دوربین</span>
                  </button>
                  <button
                    onClick={() => { startVideoChat(); }}
                    className="w-full px-3 py-2 hover:bg-zinc-800 flex items-center gap-2 transition-colors border-t border-zinc-700"
                  >
                    <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span className="text-sm text-emerald-400">چت تصویری</span>
                  </button>
                </div>
              )}
            </div>

            {/* Text Input - CENTER */}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedImage ? "کپشن یا سوال درباره عکس..." : "پیام..."}
              rows={1}
              dir="rtl"
              className="flex-1 bg-transparent text-white placeholder-zinc-500 resize-none outline-none py-1.5 px-2 max-h-24 text-sm text-right"
              style={{ scrollbarWidth: 'none' }}
            />

            {/* Mic Button - RIGHT */}
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isTranscribing}
              className={`flex-shrink-0 rounded-full flex items-center justify-center transition-all gap-1.5 ${
                isRecording 
                  ? "bg-red-500 animate-pulse px-3 h-9" 
                  : isTranscribing
                    ? "bg-zinc-600 px-3 h-9"
                    : "w-9 h-9 hover:bg-zinc-700"
              }`}
            >
              {isTranscribing ? (
                <>
                  <svg className="w-4 h-4 text-white animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" strokeOpacity="0.3"/>
                    <path d="M12 2a10 10 0 0 1 10 10"/>
                  </svg>
                  <span className="text-xs text-white">...</span>
                </>
              ) : isRecording ? (
                <>
                  <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  </svg>
                  <span className="text-xs text-white font-mono">
                    {Math.floor(recordingTime / 60)}:{(recordingTime % 60).toString().padStart(2, '0')}
                  </span>
                </>
              ) : (
                <svg className="w-4 h-4 text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" x2="12" y1="19" y2="22"/>
                </svg>
              )}
            </button>

            {/* Send Button - RIGHT */}
            <button
              onClick={sendMessage}
              disabled={!input.trim() && !selectedImage}
              className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-colors ${
                input.trim() || selectedImage
                  ? "bg-white text-black"
                  : "bg-zinc-700 text-zinc-500"
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </footer>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleImageUpload}
        className="hidden"
      />

      {/* Login Modal */}
      <LoginModal 
        isOpen={showLoginModal} 
        onClose={() => setShowLoginModal(false)} 
      />

      {/* 📹 Video Chat Modal */}
      <VideoChat
        isOpen={showVideoChat}
        onClose={() => setShowVideoChat(false)}
        token={token}
      />
      </div>{/* End Main Chat Area */}
    </div>
  );
}
