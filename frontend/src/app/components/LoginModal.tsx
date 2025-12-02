"use client";

import React, { useState } from 'react';
import { X, Phone, Mail, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth, API_BASE } from '../contexts/AuthContext';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const { login } = useAuth();
  const [step, setStep] = useState<'input' | 'verify'>('input');
  const [method, setMethod] = useState<'phone' | 'email'>('phone');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleSendCode = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${API_BASE}/auth/send-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(method === 'phone' ? { phone } : { email })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setMessage(data.message);
        setStep('verify');
      } else {
        setError(data.detail || 'خطا در ارسال کد');
      }
    } catch {
      setError('خطا در اتصال به سرور');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerify = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${API_BASE}/auth/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          ...(method === 'phone' ? { phone } : { email })
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        login(data.token, data.user);
        onClose();
        resetForm();
      } else {
        setError(data.detail || 'کد نامعتبر');
      }
    } catch {
      setError('خطا در اتصال به سرور');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setStep('input');
    setPhone('');
    setEmail('');
    setCode('');
    setError('');
    setMessage('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 rounded-2xl w-full max-w-md p-6 relative" dir="rtl">
        {/* Close Button */}
        <button
          onClick={() => { onClose(); resetForm(); }}
          className="absolute top-4 left-4 text-zinc-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold text-white mb-2">
            {step === 'input' ? 'ورود / ثبت‌نام' : 'تأیید کد'}
          </h2>
          <p className="text-zinc-400 text-sm">
            {step === 'input' && 'با موبایل یا ایمیل وارد شوید'}
          </p>
          {step === 'verify' && message && (
            <div className="mt-3 p-3 bg-green-500/20 border border-green-500/50 rounded-lg">
              <p className="text-green-400 text-lg font-bold">{message}</p>
            </div>
          )}
        </div>

        {step === 'input' ? (
          <>
            {/* Method Tabs */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setMethod('phone')}
                className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors ${
                  method === 'phone' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                }`}
              >
                <Phone className="w-4 h-4" />
                موبایل
              </button>
              <button
                onClick={() => setMethod('email')}
                className={`flex-1 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors ${
                  method === 'email' 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                }`}
              >
                <Mail className="w-4 h-4" />
                ایمیل
              </button>
            </div>

            {/* Input */}
            {method === 'phone' ? (
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="09123456789"
                className="w-full bg-zinc-800 text-white rounded-lg px-4 py-3 mb-4 outline-none focus:ring-2 focus:ring-blue-500 text-left"
                dir="ltr"
              />
            ) : (
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@example.com"
                className="w-full bg-zinc-800 text-white rounded-lg px-4 py-3 mb-4 outline-none focus:ring-2 focus:ring-blue-500 text-left"
                dir="ltr"
              />
            )}

            {/* Error */}
            {error && (
              <p className="text-red-400 text-sm mb-4">{error}</p>
            )}

            {/* Submit */}
            <button
              onClick={handleSendCode}
              disabled={isLoading || (method === 'phone' ? !phone : !email)}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  ارسال کد تأیید
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </>
        ) : (
          <>
            {/* Code Input */}
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="کد 6 رقمی"
              className="w-full bg-zinc-800 text-white rounded-lg px-4 py-3 mb-4 outline-none focus:ring-2 focus:ring-blue-500 text-center text-2xl tracking-widest"
              dir="ltr"
              maxLength={6}
            />

            {/* Error */}
            {error && (
              <p className="text-red-400 text-sm mb-4">{error}</p>
            )}

            {/* Submit */}
            <button
              onClick={handleVerify}
              disabled={isLoading || code.length !== 6}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-white py-3 rounded-lg flex items-center justify-center gap-2 transition-colors mb-3"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                'تأیید و ورود'
              )}
            </button>

            {/* Back */}
            <button
              onClick={() => { setStep('input'); setCode(''); setError(''); }}
              className="w-full text-zinc-400 hover:text-white py-2 text-sm"
            >
              ارسال مجدد کد
            </button>
          </>
        )}

        {/* Footer */}
        <p className="text-zinc-500 text-xs text-center mt-4">
          با ورود، شرایط استفاده را می‌پذیرید
        </p>
      </div>
    </div>
  );
}
