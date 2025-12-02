'use client';
import { useState, useEffect } from 'react';
import { useAuth, API_BASE } from '../contexts/AuthContext';
import Link from 'next/link';

export default function AdminPanel() {
  const { user, token } = useAuth();
  const [provider, setProvider] = useState('gemini');
  const [changing, setChanging] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/api/smart/provider`)
      .then(r => r.json())
      .then(d => setProvider(d.current))
      .catch(() => console.log('Could not fetch provider'));
  }, []);

  const changeProvider = async (p: string) => {
    setChanging(true);
    setMessage('');
    try {
      const res = await fetch(`${API_BASE}/api/smart/provider`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ provider: p })
      });
      if (res.ok) {
        setProvider(p);
        setMessage(`✅ تغییر به ${p} انجام شد`);
      } else {
        setMessage('❌ خطا در تغییر');
      }
    } catch { setMessage('❌ خطا'); }
    setChanging(false);
  };

  // Check if admin (simple check - should be server-side in production)
  const isAdmin = user?.phone === '09123456789' || user?.is_admin;

  if (!user) return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400" dir="rtl">وارد شوید</div>;
  if (!isAdmin) return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-red-400" dir="rtl">⛔ دسترسی ندارید</div>;

  const providers = [
    { id: 'gemini', name: 'Gemini', icon: '🔷', desc: 'Google AI' },
    { id: 'openai', name: 'OpenAI', icon: '🟢', desc: 'GPT-4' },
    { id: 'claude', name: 'Claude', icon: '🟣', desc: 'Anthropic' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 p-4" dir="rtl">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-white">👑 پنل ادمین</h1>
          <Link href="/" className="text-slate-400 hover:text-white">← بازگشت</Link>
        </div>

        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
          <h2 className="text-lg font-bold text-white mb-4">🤖 انتخاب هوش مصنوعی</h2>
          <p className="text-slate-400 text-sm mb-4">مدل AI که برای پردازش استفاده میشه</p>
          
          <div className="grid grid-cols-3 gap-3">
            {providers.map(p => (
              <button
                key={p.id}
                onClick={() => changeProvider(p.id)}
                disabled={changing}
                className={`p-4 rounded-xl border-2 transition-all ${
                  provider === p.id 
                    ? 'border-purple-500 bg-purple-500/20' 
                    : 'border-slate-600 hover:border-slate-500'
                }`}
              >
                <div className="text-3xl mb-2">{p.icon}</div>
                <div className="text-white font-bold">{p.name}</div>
                <div className="text-slate-400 text-xs">{p.desc}</div>
                {provider === p.id && <div className="text-purple-400 text-xs mt-1">✓ فعال</div>}
              </button>
            ))}
          </div>

          {message && <p className="mt-4 text-center">{message}</p>}
          {changing && <p className="mt-4 text-center text-slate-400">در حال تغییر...</p>}
        </div>
      </div>
    </div>
  );
}
