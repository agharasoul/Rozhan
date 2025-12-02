"use client";

import { useState, useRef, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Mic, Square, Loader2, Volume2 } from "lucide-react";

// آدرس API - داینامیک بر اساس hostname و پروتکل
const getApiBase = () => {
  if (typeof window === 'undefined') return "https://localhost:9999";
  const hostname = window.location.hostname;
  const isSecure = window.location.protocol === 'https:';
  return `${isSecure ? 'https' : 'http'}://${hostname}:9999`;
};

interface SimpleVoiceChatProps {
  onMessage?: (text: string, role: "user" | "assistant") => void;
  sessionId?: string;
}

type VoiceState = "idle" | "recording" | "processing" | "speaking";

export default function SimpleVoiceChat({ onMessage, sessionId }: SimpleVoiceChatProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  
  const { token } = useAuth();

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const recordingTimeoutRef = useRef<number | null>(null);

  // شروع ضبط صدا
  const startRecording = useCallback(async () => {
    try {
      // چک کردن پشتیبانی مرورگر
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("مرورگر شما از ضبط صدا پشتیبانی نمی‌کند");
        return;
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      
      // پیدا کردن MIME type پشتیبانی شده
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
        mimeType = 'audio/ogg';
      }
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // توقف stream
        stream.getTracks().forEach(track => track.stop());
        
        // پردازش صدا
        await processAudio();
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // هر 100ms یه chunk

      // محدود کردن طول ضبط برای کاهش تأخیر (مثلاً حداکثر ۸ ثانیه)
      if (recordingTimeoutRef.current) {
        clearTimeout(recordingTimeoutRef.current);
      }
      recordingTimeoutRef.current = window.setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.stop();
          setState("processing");
        }
      }, 8000);
      setState("recording");
      setTranscript("");
      setResponse("");
      
    } catch (error: any) {
      console.error("خطا در دسترسی به میکروفن:", error);
      if (error.name === 'NotAllowedError') {
        alert("لطفاً دسترسی به میکروفن را در تنظیمات مرورگر فعال کنید");
      } else if (error.name === 'NotFoundError') {
        alert("میکروفنی پیدا نشد");
      } else {
        alert("خطا در دسترسی به میکروفن: " + error.message);
      }
      setState("idle");
    }
  }, []);

  // توقف ضبط
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setState("processing");
    }
    if (recordingTimeoutRef.current) {
      clearTimeout(recordingTimeoutRef.current);
      recordingTimeoutRef.current = null;
    }
  }, []);

  // تبدیل Blob به base64
  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  // پردازش صدا: transcribe → chat → tts
  const processAudio = useCallback(async () => {
    const API_BASE = getApiBase();
    
    try {
      console.log("🎤 شروع پردازش صدا...");
      console.log("تعداد chunks:", audioChunksRef.current.length);
      
      // 1. تبدیل صدا به Blob
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      console.log("سایز Blob:", audioBlob.size, "bytes");
      
      if (audioBlob.size < 1000) {
        console.warn("صدا خیلی کوتاه بود");
        setState("idle");
        return;
      }
      
      // 2. تبدیل به base64
      const audioBase64 = await blobToBase64(audioBlob);
      console.log("سایز base64:", audioBase64.length);
      
      // 3. Transcribe - تبدیل صدا به متن
      console.log("📤 ارسال به /transcribe...");
      const transcribeRes = await fetch(`${API_BASE}/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audio: audioBase64,
          mime_type: 'audio/webm',
        }),
      });
      
      console.log("📥 پاسخ transcribe:", transcribeRes.status);
      
      if (!transcribeRes.ok) {
        const errText = await transcribeRes.text();
        console.error("خطای transcribe:", errText);
        throw new Error("خطا در تبدیل صدا به متن");
      }
      
      const transcribeData = await transcribeRes.json();
      const userText = transcribeData.text || "";
      console.log("✅ متن تشخیص داده شده:", userText);
      
      if (!userText.trim()) {
        console.warn("متنی تشخیص داده نشد");
        setState("idle");
        return;
      }
      
      setTranscript(userText);
      onMessage?.(userText, "user");
      
      // 4. Chat - گرفتن پاسخ از Gemini
      console.log("📤 ارسال به /chat...");
      const chatBody: any = { message: userText };
      // فقط اگه sessionId عدد باشه بفرست
      if (sessionId && typeof sessionId === 'number') {
        chatBody.session_id = sessionId;
      }

      const chatHeaders: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      // اگر کاربر لاگین باشد، توکن را برای یادگیری پروفایل بفرست
      if (token) {
        chatHeaders['Authorization'] = `Bearer ${token}`;
      }

      const chatRes = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: chatHeaders,
        body: JSON.stringify(chatBody),
      });
      
      console.log("📥 پاسخ chat:", chatRes.status);
      
      if (!chatRes.ok) {
        const errText = await chatRes.text();
        console.error("خطای chat:", errText);
        throw new Error("خطا در دریافت پاسخ");
      }
      
      const chatData = await chatRes.json();
      const assistantText = chatData.response || "";
      const assistantEmotion: string = chatData.emotion || "neutral";
      console.log("✅ پاسخ روژان:", assistantText.substring(0, 100));
      console.log("😃 احساس تشخیص‌داده‌شده:", assistantEmotion);
      
      setResponse(assistantText);
      onMessage?.(assistantText, "assistant");
      
      // 5. TTS - تبدیل متن به صدا
      console.log("📤 ارسال به /tts...");
      setState("speaking");

      // انتخاب صدا بر اساس احساس کاربر
      let ttsVoice = "fa-IR-FaridNeural"; // پیش‌فرض: فرید (شاد/خنثی)
      if (assistantEmotion === "sad" || assistantEmotion === "disappointed") {
        ttsVoice = "fa-IR-DilaraNeural"; // غمگین/دلخور → دیلارا
      } else if (assistantEmotion === "angry") {
        // عصبانی → صدای خنثی مردانه برای آرام کردن فضا
        ttsVoice = "fa-IR-FaridNeural";
      } else if (assistantEmotion === "hurry") {
        // عجله → همان فرید، ولی می‌توانیم بعداً متن را کوتاه‌تر کنیم
        ttsVoice = "fa-IR-FaridNeural";
      }

      const ttsRes = await fetch(`${API_BASE}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: assistantText,
          voice: ttsVoice,
        }),
      });
      
      console.log("📥 پاسخ tts:", ttsRes.status);
      
      if (!ttsRes.ok) {
        const errText = await ttsRes.text();
        console.error("خطای tts:", errText);
        throw new Error("خطا در تبدیل متن به صدا");
      }
      
      const ttsData = await ttsRes.json();
      
      if (ttsData.audio) {
        console.log("🔊 پخش صدا...");
        console.log("سایز audio:", ttsData.audio.length);
        console.log("شروع audio:", ttsData.audio.substring(0, 50));
        
        // اگه data URI کامل بود مستقیم استفاده کن، وگرنه بساز
        const audioSrc = ttsData.audio.startsWith('data:') 
          ? ttsData.audio 
          : `data:audio/mpeg;base64,${ttsData.audio}`;
        
        console.log("audioSrc شروع:", audioSrc.substring(0, 50));
        
        const audio = new Audio(audioSrc);
        audioRef.current = audio;
        
        audio.oncanplaythrough = () => {
          console.log("✅ صدا آماده پخش");
        };
        
        audio.onended = () => {
          console.log("✅ پخش تمام شد");
          setState("idle");
        };
        
        audio.onerror = (e) => {
          console.error("❌ خطای پخش صدا:", e);
          console.error("audio error code:", audio.error?.code);
          console.error("audio error message:", audio.error?.message);
          setState("idle");
        };
        
        try {
          await audio.play();
          console.log("▶️ پخش شروع شد");
        } catch (playError) {
          console.error("❌ خطای play():", playError);
          setState("idle");
        }
      } else {
        console.warn("صدایی دریافت نشد - ttsData:", ttsData);
        setState("idle");
      }
      
    } catch (error) {
      console.error("❌ خطا در پردازش:", error);
      setState("idle");
    }
  }, [sessionId, onMessage, token]);

  // Toggle ضبط
  const toggleRecording = useCallback(() => {
    if (state === "idle") {
      startRecording();
    } else if (state === "recording") {
      stopRecording();
    } else if (state === "speaking") {
      // توقف پخش
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setState("idle");
    }
  }, [state, startRecording, stopRecording]);

  // رنگ و آیکون بر اساس وضعیت
  const getButtonStyle = () => {
    switch (state) {
      case "recording":
        return "bg-red-500 hover:bg-red-600 animate-pulse";
      case "processing":
        return "bg-yellow-500 cursor-wait";
      case "speaking":
        return "bg-emerald-500 hover:bg-emerald-600";
      default:
        return "bg-violet-500 hover:bg-violet-600";
    }
  };

  const getIcon = () => {
    switch (state) {
      case "recording":
        return <Square className="w-5 h-5 fill-current" />;
      case "processing":
        return <Loader2 className="w-5 h-5 animate-spin" />;
      case "speaking":
        return <Volume2 className="w-5 h-5" />;
      default:
        return <Mic className="w-5 h-5" />;
    }
  };

  const getLabel = () => {
    switch (state) {
      case "recording":
        return "در حال ضبط...";
      case "processing":
        return "در حال پردازش...";
      case "speaking":
        return "در حال پخش...";
      default:
        return "چت صوتی";
    }
  };

  return (
    <div className="relative">
      {/* دکمه اصلی */}
      <button
        onClick={toggleRecording}
        disabled={state === "processing"}
        className={`
          flex items-center gap-2 px-4 py-2.5 rounded-full font-medium
          text-white shadow-lg transition-all duration-300
          ${getButtonStyle()}
        `}
      >
        {getIcon()}
        <span className="text-sm">{getLabel()}</span>
      </button>

      {/* نمایش متن (اختیاری) */}
      {false && (transcript || response) && (
        <div 
          className="absolute top-full mt-2 right-0 w-72 p-3 bg-zinc-800 rounded-xl shadow-xl border border-zinc-700 text-sm text-right z-50"
          dir="rtl"
        >
          {transcript && (
            <div className="mb-2">
              <span className="text-xs text-zinc-400">شما:</span>
              <p className="text-zinc-300 line-clamp-2">{transcript}</p>
            </div>
          )}
          {response && (
            <div>
              <span className="text-xs text-emerald-400">روژان:</span>
              <p className="text-zinc-200 line-clamp-3">{response}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
