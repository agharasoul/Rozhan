"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, Phone, PhoneOff, Loader2, Square } from "lucide-react";

// آدرس WebSocket - داینامیک بر اساس hostname و پروتکل
const getWsBase = () => {
  if (typeof window === 'undefined') return "wss://localhost:9999";
  const hostname = window.location.hostname;
  const isSecure = window.location.protocol === 'https:';
  return `${isSecure ? 'wss' : 'ws'}://${hostname}:9999`;
};

// احساسات و رنگ‌هاشون
const EMOTIONS: Record<string, { color: string; emoji: string; fa: string }> = {
  happy: { color: "bg-yellow-500", emoji: "😊", fa: "خوشحال" },
  sad: { color: "bg-blue-500", emoji: "😢", fa: "غمگین" },
  angry: { color: "bg-red-500", emoji: "😠", fa: "عصبانی" },
  anxious: { color: "bg-purple-500", emoji: "😰", fa: "مضطرب" },
  tired: { color: "bg-gray-500", emoji: "😴", fa: "خسته" },
  excited: { color: "bg-orange-500", emoji: "🤩", fa: "هیجان‌زده" },
  hurry: { color: "bg-pink-500", emoji: "⚡", fa: "عجله" },
  neutral: { color: "bg-zinc-500", emoji: "😐", fa: "خنثی" },
};

interface VoiceChatButtonProps {
  onMessage?: (text: string, role: "user" | "assistant") => void;
}

export default function VoiceChatButton({ onMessage }: VoiceChatButtonProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [emotion, setEmotion] = useState<string>("neutral");
  const [transcript, setTranscript] = useState("");
  const [userText, setUserText] = useState("");
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);

  // پخش صدای دریافتی (MP3)
  const playAudioChunk = useCallback(async (base64Audio: string, mimeType: string = "audio/mp3") => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      const audioData = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
      const ctx = audioContextRef.current;
      
      setIsSpeaking(true);
      
      // Decode audio data (works for MP3, WAV, etc.)
      const audioBuffer = await ctx.decodeAudioData(audioData.buffer.slice(0));
      
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);
      source.onended = () => {
        setIsSpeaking(false);
      };
      source.start();
    } catch (error) {
      console.error("Audio playback error:", error);
      setIsSpeaking(false);
    }
  }, []);

  // اتصال به WebSocket
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    setIsConnecting(true);
    
    try {
      const ws = new WebSocket(`${getWsBase()}/ws/voice-chat`);
      
      ws.onopen = () => {
        console.log("🎤 Voice chat WebSocket connected");
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case "connected":
            setIsConnected(true);
            setIsConnecting(false);
            console.log("✅ Voice session ready:", data.session_id);
            break;
          
          case "user_text":
            // متن شناسایی شده کاربر
            setUserText(data.data);
            onMessage?.(data.data, "user");
            break;
            
          case "audio":
            playAudioChunk(data.data, data.mime_type);
            if (data.emotion) setEmotion(data.emotion);
            break;
            
          case "text":
            setTranscript(data.data);
            setIsProcessing(false);
            if (data.emotion) setEmotion(data.emotion);
            onMessage?.(data.data, "assistant");
            break;
            
          case "turn_complete":
            setIsProcessing(false);
            break;
            
          case "error":
            console.error("Voice chat error:", data.message);
            setIsConnecting(false);
            setIsProcessing(false);
            break;
        }
      };
      
      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setIsConnecting(false);
        setIsConnected(false);
      };
      
      ws.onclose = () => {
        console.log("🔴 Voice chat disconnected");
        setIsConnected(false);
        setIsListening(false);
        stopRecording();
      };
      
      wsRef.current = ws;
      
    } catch (error) {
      console.error("Connection error:", error);
      setIsConnecting(false);
    }
  }, [onMessage, playAudioChunk]);

  // قطع اتصال
  const disconnect = useCallback(() => {
    stopRecording();
    
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: "end" }));
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setTranscript("");
    setEmotion("neutral");
  }, []);

  // شروع ضبط صدا
  const startRecording = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      await connect();
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      
      audioChunksRef.current = [];
      
      // استفاده از MediaRecorder برای ضبط
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // وقتی ضبط تموم شد، صدا رو ارسال کن
        if (audioChunksRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const arrayBuffer = await audioBlob.arrayBuffer();
          const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
          
          setIsProcessing(true);
          wsRef.current.send(JSON.stringify({
            type: "audio",
            data: base64,
            mime_type: "audio/webm"
          }));
        }
        
        // توقف tracks
        stream.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsListening(true);
      
    } catch (error) {
      console.error("Microphone error:", error);
      alert("دسترسی به میکروفن رد شد");
    }
  }, [connect]);

  // توقف ضبط و ارسال
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsListening(false);
  }, []);

  // Toggle مکالمه صوتی
  const toggleVoiceChat = useCallback(() => {
    if (isConnected) {
      if (isListening) {
        stopRecording();
      } else {
        startRecording();
      }
    } else {
      connect().then(() => {
        setTimeout(startRecording, 500);
      });
    }
  }, [isConnected, isListening, connect, startRecording, stopRecording]);

  // پاکسازی در unmount
  useEffect(() => {
    return () => {
      disconnect();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [disconnect]);

  const emotionInfo = EMOTIONS[emotion] || EMOTIONS.neutral;

  return (
    <div className="relative">
      {/* دکمه اصلی چت صوتی */}
      <button
        onClick={toggleVoiceChat}
        disabled={isConnecting || isProcessing}
        className={`
          relative flex items-center gap-2 px-4 py-2.5 rounded-full font-medium
          transition-all duration-300 shadow-lg
          ${isConnecting || isProcessing
            ? "bg-zinc-700 text-zinc-400 cursor-wait" 
            : isListening 
              ? "bg-gradient-to-r from-red-500 to-pink-500 text-white animate-pulse shadow-red-500/30" 
              : isConnected
                ? "bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-emerald-500/30"
                : "bg-gradient-to-r from-violet-500 to-purple-500 text-white hover:from-violet-600 hover:to-purple-600 shadow-violet-500/30"
          }
        `}
      >
        {isConnecting ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>در حال اتصال...</span>
          </>
        ) : isProcessing ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>در حال پردازش...</span>
          </>
        ) : isListening ? (
          <>
            <div className="relative">
              <Square className="w-5 h-5" />
            </div>
            <span>ارسال صدا</span>
          </>
        ) : isConnected ? (
          <>
            <Mic className="w-5 h-5" />
            <span>شروع صحبت</span>
          </>
        ) : (
          <>
            <Mic className="w-5 h-5" />
            <span>چت صوتی</span>
          </>
        )}
      </button>

      {/* نشانگر احساس */}
      {isConnected && (
        <div className={`
          absolute -top-2 -right-2 flex items-center justify-center
          w-8 h-8 rounded-full text-lg
          ${emotionInfo.color} shadow-lg
          transition-all duration-300
          ${isSpeaking ? "animate-bounce" : ""}
        `}>
          {emotionInfo.emoji}
        </div>
      )}

      {/* دکمه قطع */}
      {isConnected && (
        <button
          onClick={disconnect}
          className="absolute -bottom-1 -left-1 w-6 h-6 bg-red-500 hover:bg-red-600 rounded-full flex items-center justify-center shadow-lg transition-colors"
          title="قطع مکالمه"
        >
          <PhoneOff className="w-3 h-3 text-white" />
        </button>
      )}

      {/* نمایش متن (اختیاری) */}
      {transcript && isConnected && (
        <div className="absolute top-full mt-2 right-0 w-64 p-3 bg-zinc-800 rounded-xl shadow-xl border border-zinc-700 text-sm text-right" dir="rtl">
          <div className="flex items-center gap-2 mb-2">
            <span className={`w-2 h-2 rounded-full ${emotionInfo.color}`} />
            <span className="text-xs text-zinc-400">{emotionInfo.fa}</span>
          </div>
          <p className="text-zinc-200 line-clamp-3">{transcript}</p>
        </div>
      )}
    </div>
  );
}
