"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { 
  Video, VideoOff, Mic, MicOff, Send, X, 
  Camera, Smile, MessageSquare, Sparkles,
  Volume2, VolumeX, Brain, PhoneCall, PhoneOff
} from "lucide-react";
import { API_BASE } from "../contexts/AuthContext";

interface VideoChatProps {
  isOpen: boolean;
  onClose: () => void;
  token?: string | null;
}

interface Analysis {
  emotion: string;
  emotion_fa: string;
  emotion_confidence?: number;
  age_range?: string;
  gender?: string;
  environment?: string;
  food_suggestion?: string;
  face_count?: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  emotion?: string;
}

// رنگ احساسات
const EMOTION_COLORS: Record<string, string> = {
  happy: "bg-yellow-500",
  sad: "bg-blue-500",
  angry: "bg-red-500",
  surprised: "bg-purple-500",
  fearful: "bg-orange-500",
  disgusted: "bg-green-500",
  neutral: "bg-gray-500"
};

// ایموجی احساسات
const EMOTION_EMOJIS: Record<string, string> = {
  happy: "😊",
  sad: "😢",
  angry: "😠",
  surprised: "😮",
  fearful: "😨",
  disgusted: "🤢",
  neutral: "😐"
};

export default function VideoChat({ isOpen, onClose, token }: VideoChatProps) {
  // States
  const [isConnected, setIsConnected] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // 🎤 Voice Chat States
  const [isVoiceMode, setIsVoiceMode] = useState(false);  // حالت مکالمه صوتی
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [autoSpeak, setAutoSpeak] = useState(true);  // پخش خودکار پاسخ
  const [learnedInfo, setLearnedInfo] = useState<string[]>([]);  // اطلاعات یاد گرفته شده
  const [messageCount, setMessageCount] = useState(0);
  const [emotionMessage, setEmotionMessage] = useState<string | null>(null);

  // Refs
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyzeIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // شروع دوربین
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
        audio: true
      });
      
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      
      return true;
    } catch (err) {
      console.error("Camera error:", err);
      setError("دسترسی به دوربین رد شد");
      return false;
    }
  };

  // توقف دوربین
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  // گرفتن فریم از ویدیو
  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !canvasRef.current) return null;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    
    if (!ctx) return null;
    
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    return canvas.toDataURL("image/jpeg", 0.7);
  }, []);

  // اتصال WebSocket
  const connectWebSocket = useCallback(() => {
    const wsUrl = API_BASE.replace("http", "ws") + "/ws/video-chat";
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log("📹 WebSocket connected");
      setIsConnected(true);
      setError(null);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case "connected":
          setSessionId(data.session_id);
          // پیام خوش‌آمدگویی
          if (data.welcome) {
            setMessages(prev => [...prev, {
              id: "welcome",
              role: "assistant",
              content: data.welcome,
              emotion: "happy"
            }]);
          }
          break;
          
        case "analysis":
          setAnalysis(data.data);
          break;
          
        case "suggestion":
          setSuggestion(data.data);
          break;
          
        case "transcription":
          // 🎤 متن تشخیص داده شده از صدا
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: "user",
            content: data.data,
            emotion: data.audio_emotion
          }]);
          break;
          
        case "response":
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: "assistant",
            content: data.data,
            emotion: data.emotion
          }]);
          setIsLoading(false);
          setMessageCount(data.message_count || 0);
          
          // 🧠 اطلاعات یاد گرفته شده
          if (data.learned && data.learned.length > 0) {
            setLearnedInfo(prev => [...new Set([...prev, ...data.learned])]);
          }
          
          // TTS برای پاسخ (اگه autoSpeak فعاله)
          if (autoSpeak && !isMuted) {
            speakResponse(data.data);
          }
          break;
          
        case "emotion_change":
          // 📢 تغییر احساس تشخیص داده شد
          setEmotionMessage(data.message);
          setTimeout(() => setEmotionMessage(null), 5000);
          break;
          
        case "session_summary":
          // 📊 خلاصه session
          console.log("Session summary:", data.data);
          break;
          
        case "error":
          setError(data.message);
          setIsLoading(false);
          break;
      }
    };
    
    ws.onclose = () => {
      console.log("📹 WebSocket disconnected");
      setIsConnected(false);
    };
    
    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("خطا در اتصال");
    };
    
    wsRef.current = ws;
    
    return ws;
  }, [isMuted]);

  // ارسال فریم برای تحلیل
  const sendFrame = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (!isVideoOn) return;
    
    const frame = captureFrame();
    if (frame) {
      wsRef.current.send(JSON.stringify({
        type: "frame",
        data: frame
      }));
    }
  }, [captureFrame, isVideoOn]);

  // ارسال پیام
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    
    const userMessage = input.trim();
    setInput("");
    setIsLoading(true);
    
    // اضافه کردن پیام کاربر
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: "user",
      content: userMessage
    }]);
    
    // گرفتن فریم فعلی
    const frame = captureFrame();
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "message",
        data: userMessage,
        frame: frame
      }));
    } else {
      // Fallback به REST API
      try {
        const res = await fetch(`${API_BASE}/video-chat/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          },
          body: JSON.stringify({
            message: userMessage,
            frame: frame,
            session_id: sessionId
          })
        });
        
        const data = await res.json();
        
        if (data.success) {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: "assistant",
            content: data.response,
            emotion: data.emotion
          }]);
          
          if (data.analysis) {
            setAnalysis(data.analysis);
          }
        }
      } catch (err) {
        console.error("Chat error:", err);
        setError("خطا در ارسال پیام");
      } finally {
        setIsLoading(false);
      }
    }
  };

  // Text-to-Speech
  const speakResponse = async (text: string) => {
    try {
      setIsSpeaking(true);
      
      const res = await fetch(`${API_BASE}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.slice(0, 500) })
      });
      
      const data = await res.json();
      
      if (data.success && data.audio) {
        const audio = new Audio(data.audio);
        audioRef.current = audio;
        
        audio.onended = () => setIsSpeaking(false);
        audio.onerror = () => setIsSpeaking(false);
        
        await audio.play();
      } else {
        setIsSpeaking(false);
      }
    } catch (err) {
      setIsSpeaking(false);
    }
  };

  // متوقف کردن صدا
  const stopSpeaking = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsSpeaking(false);
  };

  // شروع/توقف ویدیو
  const toggleVideo = () => {
    if (streamRef.current) {
      const videoTrack = streamRef.current.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !isVideoOn;
        setIsVideoOn(!isVideoOn);
      }
    }
  };

  // شروع/توقف صدا
  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (isSpeaking) {
      stopSpeaking();
    }
  };

  // 🎤 شروع ضبط صدا
  const startRecording = async () => {
    if (!streamRef.current) return;
    
    try {
      audioChunksRef.current = [];
      
      const mediaRecorder = new MediaRecorder(streamRef.current, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioMessage(audioBlob);
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100);
      setIsRecording(true);
      setRecordingTime(0);
      
      // تایمر ضبط
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (err) {
      console.error("Recording error:", err);
      setError("خطا در ضبط صدا");
    }
  };

  // 🛑 توقف ضبط
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

  // 📤 ارسال پیام صوتی
  const sendAudioMessage = async (audioBlob: Blob) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    
    setIsLoading(true);
    
    try {
      // تبدیل به base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      
      reader.onloadend = () => {
        const base64Audio = (reader.result as string).split(',')[1];
        const frame = captureFrame();
        
        wsRef.current?.send(JSON.stringify({
          type: "audio",
          data: base64Audio,
          frame: frame,
          mime_type: "audio/webm"
        }));
      };
    } catch (err) {
      console.error("Send audio error:", err);
      setError("خطا در ارسال صدا");
      setIsLoading(false);
    }
  };

  // 🎙️ Toggle حالت مکالمه صوتی
  const toggleVoiceMode = () => {
    if (isVoiceMode) {
      // خروج از حالت صوتی
      if (isRecording) stopRecording();
      setIsVoiceMode(false);
    } else {
      // ورود به حالت صوتی
      setIsVoiceMode(true);
    }
  };

  // شروع session
  useEffect(() => {
    if (!isOpen) return;
    
    const init = async () => {
      const cameraStarted = await startCamera();
      if (cameraStarted) {
        connectWebSocket();
        
        // شروع تحلیل دوره‌ای (هر 3 ثانیه)
        analyzeIntervalRef.current = setInterval(sendFrame, 3000);
      }
    };
    
    init();
    
    return () => {
      // Cleanup
      if (analyzeIntervalRef.current) {
        clearInterval(analyzeIntervalRef.current);
      }
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
      }
      if (wsRef.current) {
        // ارسال پیام پایان قبل از بستن
        try {
          wsRef.current.send(JSON.stringify({ type: "end" }));
        } catch {}
        wsRef.current.close();
      }
      stopCamera();
      stopSpeaking();
    };
  }, [isOpen]);

  // اسکرول به پایین
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-2xl w-full max-w-4xl h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
            <h2 className="text-white font-bold text-lg">📹 چت ویدیویی با روژان</h2>
            {analysis?.emotion && (
              <span className={`px-2 py-1 rounded-full text-xs text-white ${EMOTION_COLORS[analysis.emotion]}`}>
                {EMOTION_EMOJIS[analysis.emotion]} {analysis.emotion_fa}
              </span>
            )}
            {isVoiceMode && (
              <span className="px-2 py-1 rounded-full text-xs bg-green-600 text-white flex items-center gap-1">
                <PhoneCall className="w-3 h-3" />
                مکالمه
              </span>
            )}
            {messageCount > 0 && (
              <span className="text-xs text-gray-400">
                {messageCount} پیام
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isSpeaking && (
              <span className="text-xs text-blue-400 animate-pulse">🔊 در حال صحبت...</span>
            )}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-full transition"
            >
              <X className="w-6 h-6 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Video Section */}
          <div className="w-1/2 p-4 flex flex-col gap-4">
            {/* Video Preview */}
            <div className="relative flex-1 bg-black rounded-xl overflow-hidden">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover ${!isVideoOn ? "hidden" : ""}`}
              />
              
              {!isVideoOn && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-800">
                  <VideoOff className="w-16 h-16 text-gray-500" />
                </div>
              )}
              
              {/* Emotion Badge */}
              {analysis && (
                <div className="absolute top-4 right-4 bg-black/70 rounded-lg p-3 text-white text-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <Smile className="w-4 h-4" />
                    <span>احساس: {EMOTION_EMOJIS[analysis.emotion]} {analysis.emotion_fa}</span>
                  </div>
                  {analysis.environment && (
                    <div className="text-gray-400 text-xs">
                      محیط: {analysis.environment}
                    </div>
                  )}
                </div>
              )}
              
              {/* Hidden Canvas for Frame Capture */}
              <canvas ref={canvasRef} className="hidden" />
            </div>

            {/* Emotion Change Message */}
            {emotionMessage && (
              <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-yellow-500 text-black px-4 py-2 rounded-full text-sm font-bold animate-bounce">
                {emotionMessage}
              </div>
            )}

            {/* Video Controls */}
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={toggleVideo}
                className={`p-3 rounded-full transition ${
                  isVideoOn ? "bg-gray-700 hover:bg-gray-600" : "bg-red-600 hover:bg-red-500"
                }`}
              >
                {isVideoOn ? (
                  <Video className="w-5 h-5 text-white" />
                ) : (
                  <VideoOff className="w-5 h-5 text-white" />
                )}
              </button>
              
              <button
                onClick={toggleMute}
                className={`p-3 rounded-full transition ${
                  !isMuted ? "bg-gray-700 hover:bg-gray-600" : "bg-red-600 hover:bg-red-500"
                }`}
              >
                {!isMuted ? (
                  <Volume2 className="w-5 h-5 text-white" />
                ) : (
                  <VolumeX className="w-5 h-5 text-white" />
                )}
              </button>
              
              {/* 🎤 دکمه مکالمه صوتی */}
              <button
                onClick={toggleVoiceMode}
                className={`p-3 rounded-full transition ${
                  isVoiceMode 
                    ? "bg-green-600 hover:bg-green-500 ring-2 ring-green-400" 
                    : "bg-gray-700 hover:bg-gray-600"
                }`}
                title={isVoiceMode ? "خروج از حالت صوتی" : "مکالمه صوتی"}
              >
                {isVoiceMode ? (
                  <PhoneCall className="w-5 h-5 text-white" />
                ) : (
                  <PhoneOff className="w-5 h-5 text-white" />
                )}
              </button>
              
              <button
                onClick={sendFrame}
                className="p-3 rounded-full bg-blue-600 hover:bg-blue-500 transition"
                title="تحلیل فوری"
              >
                <Camera className="w-5 h-5 text-white" />
              </button>
            </div>

            {/* 🎤 Voice Mode Controls */}
            {isVoiceMode && (
              <div className="bg-gray-800 rounded-xl p-4 mt-2">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-green-400 text-sm font-bold flex items-center gap-2">
                    <PhoneCall className="w-4 h-4" />
                    حالت مکالمه صوتی
                  </span>
                  <label className="flex items-center gap-2 text-xs text-gray-400">
                    <input 
                      type="checkbox" 
                      checked={autoSpeak}
                      onChange={(e) => setAutoSpeak(e.target.checked)}
                      className="rounded"
                    />
                    پخش خودکار
                  </label>
                </div>
                
                <div className="flex items-center justify-center gap-4">
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      disabled={isLoading}
                      className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-500 disabled:bg-gray-600 rounded-full text-white font-bold transition"
                    >
                      <Mic className="w-5 h-5" />
                      نگه دار و حرف بزن
                    </button>
                  ) : (
                    <button
                      onClick={stopRecording}
                      className="flex items-center gap-2 px-6 py-3 bg-red-500 animate-pulse rounded-full text-white font-bold"
                    >
                      <MicOff className="w-5 h-5" />
                      {recordingTime}s - رها کن
                    </button>
                  )}
                </div>
                
                {isLoading && (
                  <div className="text-center text-gray-400 text-sm mt-2">
                    در حال پردازش...
                  </div>
                )}
              </div>
            )}

            {/* 🧠 Learning Info */}
            {learnedInfo.length > 0 && (
              <div className="bg-purple-900/50 rounded-xl p-3 mt-2">
                <div className="flex items-center gap-2 text-purple-300 text-xs mb-1">
                  <Brain className="w-4 h-4" />
                  <span>یاد گرفتم:</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {learnedInfo.slice(-5).map((info, i) => (
                    <span key={i} className="px-2 py-0.5 bg-purple-800 rounded text-xs text-purple-200">
                      {info}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Suggestion */}
            {suggestion && (
              <div className="bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl p-4 text-white">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-5 h-5" />
                  <span className="font-bold">پیشنهاد روژان</span>
                </div>
                <p className="text-sm">{suggestion}</p>
              </div>
            )}
          </div>

          {/* Chat Section */}
          <div className="w-1/2 border-r border-gray-700 flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>سلام! 👋</p>
                  <p className="text-sm">من روژان هستم و دارم می‌بینمت!</p>
                  <p className="text-sm">چطور میتونم کمکت کنم؟</p>
                </div>
              )}
              
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-start" : "justify-end"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-700 text-white"
                    }`}
                  >
                    {msg.emotion && msg.role === "assistant" && (
                      <span className="text-xs opacity-70 block mb-1">
                        {EMOTION_EMOJIS[msg.emotion]}
                      </span>
                    )}
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-end">
                  <div className="bg-gray-700 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-gray-700">
              {error && (
                <div className="mb-2 text-red-400 text-sm text-center">
                  {error}
                </div>
              )}
              
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                  placeholder="پیامتو بنویس..."
                  className="flex-1 bg-gray-800 text-white rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isLoading}
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || isLoading}
                  className="p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 rounded-xl transition"
                >
                  <Send className="w-5 h-5 text-white" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
