'use client';
import { useState, useEffect } from 'react';
import { useAuth, API_BASE } from '../contexts/AuthContext';
import Link from 'next/link';

interface CardProps {
  icon: string;
  title: string;
  value: string | number;
}

const Card = ({icon, title, value}: CardProps) => (
  <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
    <div className="text-2xl mb-2">{icon}</div>
    <div className="text-slate-400 text-sm">{title}</div>
    <div className="text-white font-bold">{value}</div>
  </div>
);

export default function SmartDashboard() {
  const { user, token } = useAuth();
  interface Pattern {
    day: string;
    food: string;
  }
  interface DashboardData {
    profile?: {
      total_fields?: number;
      profile?: { favorite_foods?: string[] };
      warnings?: string[];
      summary?: string;
    };
    patterns?: Pattern[];
  }
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      const h = { Authorization: `Bearer ${token}` };
      Promise.all([
        fetch(`${API_BASE}/auth/smart-profile`, {headers: h}).then(r=>r.json()).catch(()=>({})),
        fetch(`${API_BASE}/api/smart/patterns`, {headers: h}).then(r=>r.json()).catch(()=>({})),
      ]).then(([p, pt]) => {
        setData({ profile: p, patterns: pt?.data?.patterns || [] });
        setLoading(false);
      });
    } else setLoading(false);
  }, [token]);

  if (!user) return <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400" dir="rtl">برای مشاهده وارد شوید</div>;
  if (loading) return <div className="min-h-screen bg-slate-900 flex items-center justify-center"><div className="animate-spin h-8 w-8 border-2 border-purple-500 border-t-transparent rounded-full"/></div>;

  const { profile, patterns } = data;
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 p-4" dir="rtl">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-white">🧠 داشبورد هوشمند</h1>
          <Link href="/" className="text-slate-400 hover:text-white">← بازگشت</Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <Card icon="📊" title="فیلدها" value={profile?.total_fields || 0} />
          <Card icon="🍕" title="محبوب" value={profile?.profile?.favorite_foods?.[0] || '-'} />
          <Card icon="📈" title="الگوها" value={patterns?.length || 0} />
          <Card icon="⚠️" title="هشدار" value={profile?.warnings?.length || 0} />
        </div>
        {profile?.warnings?.length > 0 && (
          <div className="bg-red-900/30 rounded-xl p-4 mb-4 border border-red-500/30">
            <h2 className="font-bold text-red-400 mb-2">⚠️ هشدارها</h2>
            {profile.warnings.map((w: string, i: number) => <p key={i} className="text-red-300">{w}</p>)}
          </div>
        )}
        {patterns?.length > 0 && (
          <div className="bg-slate-800/50 rounded-xl p-4 mb-4 border border-blue-500/30">
            <h2 className="font-bold text-blue-400 mb-2">📈 الگوها</h2>
            {patterns.map((p: Pattern, i: number) => <p key={i} className="text-slate-300">📅 {p.day}: {p.food}</p>)}
          </div>
        )}
        {profile?.summary && (
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-600">
            <h2 className="font-bold text-slate-300 mb-2">📝 خلاصه</h2>
            <p className="text-slate-400 whitespace-pre-wrap">{profile.summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}
