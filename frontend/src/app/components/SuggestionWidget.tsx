'use client';
import { useState, useEffect } from 'react';
import { API_BASE } from '../contexts/AuthContext';

interface Props {
  token: string | null;
  onSelect?: (food: string) => void;
}

export default function SuggestionWidget({ token, onSelect }: Props) {
  const [suggestion, setSuggestion] = useState<any>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (token && !dismissed) {
      fetch(`${API_BASE}/api/smart/suggestions`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(r => r.json())
        .then(d => setSuggestion(d?.data))
        .catch(() => {});
    }
  }, [token, dismissed]);

  if (!suggestion || dismissed || !suggestion.recommendations?.length) return null;

  const rec = suggestion.recommendations[0];

  return (
    <div className="bg-gradient-to-r from-purple-900/50 to-blue-900/50 rounded-xl p-4 mb-4 border border-purple-500/30">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-purple-300 text-sm mb-1">💡 پیشنهاد روژان:</p>
          <p className="text-white font-medium">{rec.food}</p>
          <p className="text-slate-400 text-sm">{rec.reason}</p>
        </div>
        <button onClick={() => setDismissed(true)} className="text-slate-500 hover:text-slate-300">✕</button>
      </div>
      <div className="flex gap-2 mt-3">
        <button 
          onClick={() => onSelect?.(rec.food)}
          className="px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm"
        >
          سفارش بدم
        </button>
        <button 
          onClick={() => setDismissed(true)}
          className="px-4 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm"
        >
          بعداً
        </button>
      </div>
    </div>
  );
}
