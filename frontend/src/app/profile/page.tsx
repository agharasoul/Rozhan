'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth, API_BASE } from '../contexts/AuthContext';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  phone: string | null;
  email: string | null;
  name: string | null;
}

interface Profile {
  favorite_foods: string[];
  allergies: string[];
  dietary_preferences: string[];
  spice_level: string;
  total_orders: number;
  loyalty_tier: string;
  extra_data: Record<string, unknown>;
}

// Helper to safely parse JSON array fields
const parseArrayField = (value: unknown): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
};

// Helper to safely parse JSON object fields
const parseObjectField = (value: unknown): Record<string, unknown> => {
  if (!value) return {};
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
      return {};
    } catch {
      return {};
    }
  }
  return {};
};

export default function ProfilePage() {
  const { user, token, logout, updateUser } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    favorite_foods: '',
    allergies: '',
    dietary_preferences: '',
  });

  useEffect(() => {
    if (!user) {
      router.push('/');
      return;
    }

    setFormData(prev => ({
      ...prev,
      name: user.name || '',
    }));

    // Fetch profile
    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (data.profile) {
          setProfile(data.profile);
          setFormData({
            name: data.user?.name || '',
            favorite_foods: parseArrayField(data.profile.favorite_foods).join(', '),
            allergies: parseArrayField(data.profile.allergies).join(', '),
            dietary_preferences: parseArrayField(data.profile.dietary_preferences).join(', '),
          });
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [user, token, router]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');

  const handleSave = async () => {
    setSaving(true);
    setSaveError('');
    
    const payload = {
      name: formData.name,
      favorite_foods: formData.favorite_foods.split(',').map(s => s.trim()).filter(Boolean),
      allergies: formData.allergies.split(',').map(s => s.trim()).filter(Boolean),
      dietary_preferences: formData.dietary_preferences.split(',').map(s => s.trim()).filter(Boolean),
    };
    
    console.log("Saving profile:", payload, "to:", `${API_BASE}/auth/profile`);
    
    try {
      const res = await fetch(`${API_BASE}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      
      console.log("Profile save response:", res.status);
      
      const data = await res.json();
      console.log("Profile save data:", data);
      
      if (!res.ok) {
        console.error("Profile save error:", data);
        throw new Error(data.detail || 'خطا در ذخیره');
      }
      
      // آپدیت state بدون reload
      if (data.user) {
        updateUser(data.user as User);
      }
      if (data.profile) {
        setProfile(data.profile);
      }
      
      setEditing(false);
      alert('پروفایل با موفقیت ذخیره شد!');
    } catch (error) {
      console.error(error);
      setSaveError(error instanceof Error ? error.message : 'خطا در ذخیره پروفایل');
    } finally {
      setSaving(false);
    }
  };

  const getTierInfo = (tier: string) => {
    const tiers: Record<string, { color: string; icon: string; name: string }> = {
      bronze: { color: 'from-amber-600 to-amber-800', icon: '🥉', name: 'برنز' },
      silver: { color: 'from-slate-400 to-slate-600', icon: '🥈', name: 'نقره' },
      gold: { color: 'from-yellow-400 to-yellow-600', icon: '🥇', name: 'طلا' },
      platinum: { color: 'from-cyan-400 to-cyan-600', icon: '💎', name: 'پلاتین' },
      diamond: { color: 'from-purple-400 to-pink-600', icon: '👑', name: 'الماس' },
    };
    return tiers[tier] || tiers.bronze;
  };

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  const tierInfo = getTierInfo(profile?.loyalty_tier || 'bronze');

  return (
    <div className="fixed inset-0 bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col" dir="rtl">
      {/* Header */}
      <header className="flex-shrink-0 bg-slate-800/50 backdrop-blur-lg border-b border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-slate-400 hover:text-white transition">
              ← برگشت
            </Link>
            <h1 className="text-xl font-bold text-white">👤 پروفایل</h1>
          </div>
          <button
            onClick={() => {
              logout();
              router.push('/');
            }}
            className="text-red-400 hover:text-red-300 text-sm transition"
          >
            خروج
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 pb-20 space-y-6">
        {/* User Card */}
        <div className={`bg-gradient-to-r ${tierInfo.color} rounded-2xl p-6 text-white`}>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center text-3xl">
              {tierInfo.icon}
            </div>
            <div>
              <h2 className="text-2xl font-bold">{user.name || 'کاربر'}</h2>
              <p className="opacity-80">{user.email || user.phone}</p>
              <p className="text-sm opacity-60 mt-1">
                سطح {tierInfo.name} • {profile?.total_orders || 0} سفارش
              </p>
            </div>
          </div>
        </div>

        {/* Profile Info */}
        <div className="bg-slate-800/50 rounded-2xl border border-slate-700 overflow-hidden">
          <div className="p-6 border-b border-slate-700 flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">اطلاعات من</h3>
            {!editing && (
              <button
                onClick={() => setEditing(true)}
                className="text-purple-400 hover:text-purple-300 text-sm"
              >
                ویرایش
              </button>
            )}
          </div>

          <div className="p-6 space-y-4">
            {editing ? (
              <>
                <div>
                  <label className="block text-slate-400 text-sm mb-2">نام</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-sm mb-2">غذاهای مورد علاقه (با کاما جدا کنید)</label>
                  <input
                    type="text"
                    value={formData.favorite_foods}
                    onChange={(e) => setFormData(prev => ({ ...prev, favorite_foods: e.target.value }))}
                    placeholder="پیتزا، برگر، کباب"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-sm mb-2">آلرژی‌ها</label>
                  <input
                    type="text"
                    value={formData.allergies}
                    onChange={(e) => setFormData(prev => ({ ...prev, allergies: e.target.value }))}
                    placeholder="بادام، لاکتوز"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 text-sm mb-2">رژیم غذایی</label>
                  <input
                    type="text"
                    value={formData.dietary_preferences}
                    onChange={(e) => setFormData(prev => ({ ...prev, dietary_preferences: e.target.value }))}
                    placeholder="گیاهی، بدون گلوتن"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                </div>
                {saveError && (
                  <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-2 rounded-lg text-sm">
                    {saveError}
                  </div>
                )}
                <div className="flex gap-3 pt-4">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex-1 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:cursor-wait text-white py-3 rounded-xl font-bold transition"
                  >
                    {saving ? 'در حال ذخیره...' : 'ذخیره'}
                  </button>
                  <button
                    onClick={() => setEditing(false)}
                    disabled={saving}
                    className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-3 rounded-xl font-bold transition"
                  >
                    انصراف
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center justify-between py-3 border-b border-slate-700">
                  <span className="text-slate-400">غذاهای مورد علاقه</span>
                  <span className="text-white">
                    {parseArrayField(profile?.favorite_foods).length ? parseArrayField(profile?.favorite_foods).join('، ') : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-slate-700">
                  <span className="text-slate-400">آلرژی‌ها</span>
                  <span className="text-white">
                    {parseArrayField(profile?.allergies).length ? parseArrayField(profile?.allergies).join('، ') : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-slate-700">
                  <span className="text-slate-400">رژیم غذایی</span>
                  <span className="text-white">
                    {parseArrayField(profile?.dietary_preferences).length ? parseArrayField(profile?.dietary_preferences).join('، ') : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between py-3">
                  <span className="text-slate-400">سطح تندی</span>
                  <span className="text-white">{profile?.spice_level || '—'}</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Smart Learned Data */}
        {(() => {
          const extraData = parseObjectField(profile?.extra_data);
          const filteredEntries = Object.entries(extraData)
            .filter(([key, value]) => 
              !key.startsWith('_') &&
              !key.includes('update') && 
              !key.includes('history') &&
              !key.includes('mentioned') &&
              typeof value === 'string'
            );
          
          if (filteredEntries.length === 0) return null;
          
          const labels: Record<string, string> = {
            name: '👤 نام',
            age: '🎂 سن',
            city: '🏙️ شهر',
            job: '💼 شغل',
            birthday: '🎁 تولد',
            last_emotion: '🎭 آخرین احساس',
            satisfaction_level: '⭐ رضایت',
          };
          
          return (
            <div className="bg-slate-800/50 rounded-2xl border border-slate-700 overflow-hidden">
              <div className="p-6 border-b border-slate-700">
                <h3 className="text-lg font-bold text-white">🧠 اطلاعات یاد گرفته شده</h3>
                <p className="text-slate-400 text-sm mt-1">این اطلاعات از چت‌های شما استخراج شده</p>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4">
                  {filteredEntries.map(([key, value]) => (
                    <div key={key} className="bg-slate-700/30 rounded-lg p-3">
                      <span className="text-slate-400 text-sm block mb-1">{labels[key] || key}</span>
                      <span className="text-white">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Quick Links */}
        <div className="grid grid-cols-3 gap-4">
          <Link
            href="/"
            className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 text-center hover:border-purple-500 transition"
          >
            <span className="text-3xl block mb-2">💬</span>
            <span className="text-white font-medium">چت با روژان</span>
          </Link>
          <Link
            href="/restaurants"
            className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 text-center hover:border-purple-500 transition"
          >
            <span className="text-3xl block mb-2">🍽️</span>
            <span className="text-white font-medium">رستوران‌ها</span>
          </Link>
          <Link
            href="/smart"
            className="bg-gradient-to-br from-purple-900/50 to-blue-900/50 rounded-xl border border-purple-500/50 p-6 text-center hover:border-purple-400 transition"
          >
            <span className="text-3xl block mb-2">🧠</span>
            <span className="text-white font-medium">داشبورد هوشمند</span>
          </Link>
        </div>
        </div>
      </main>
    </div>
  );
}
