'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { API_BASE } from '../contexts/AuthContext';

interface Restaurant {
  id: number;
  name: string;
  logo_url: string;
  address: string;
  phone: string;
  rating: number;
  delivery_fee: number;
  min_order_amount: number;
  is_open: number;
}

export default function RestaurantsPage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/restaurants`)
      .then(res => res.json())
      .then(data => {
        setRestaurants(data.restaurants || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800" dir="rtl">
      {/* Header */}
      <header className="bg-slate-800/50 backdrop-blur-lg border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            🌟 روژان
          </Link>
          <nav className="flex gap-4">
            <Link href="/" className="text-slate-300 hover:text-white transition">چت</Link>
            <Link href="/restaurants" className="text-purple-400 font-medium">رستوران‌ها</Link>
            <Link href="/cart" className="text-slate-300 hover:text-white transition">🛒 سبد</Link>
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-white mb-8">🍽️ رستوران‌ها</h1>

        {restaurants.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-slate-400 text-lg">هنوز رستورانی اضافه نشده!</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {restaurants.map(restaurant => (
              <Link
                key={restaurant.id}
                href={`/restaurants/${restaurant.id}`}
                className="bg-slate-800/50 rounded-2xl overflow-hidden border border-slate-700 hover:border-purple-500 transition-all hover:scale-[1.02] group"
              >
                {/* Logo */}
                <div className="h-40 bg-gradient-to-br from-purple-600/20 to-pink-600/20 flex items-center justify-center text-6xl">
                  {restaurant.logo_url || '🍽️'}
                </div>

                {/* Info */}
                <div className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <h2 className="text-xl font-bold text-white group-hover:text-purple-400 transition">
                      {restaurant.name}
                    </h2>
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      restaurant.is_open 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                      {restaurant.is_open ? 'باز' : 'بسته'}
                    </span>
                  </div>

                  <p className="text-slate-400 text-sm mb-4 line-clamp-1">
                    📍 {restaurant.address}
                  </p>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-yellow-400">
                      ⭐ {restaurant.rating}
                    </span>
                    <span className="text-slate-400">
                      🚚 {restaurant.delivery_fee.toLocaleString()} تومان
                    </span>
                  </div>

                  <div className="mt-3 pt-3 border-t border-slate-700 text-xs text-slate-500">
                    حداقل سفارش: {restaurant.min_order_amount.toLocaleString()} تومان
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
