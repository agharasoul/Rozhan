'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '../contexts/AuthContext';

interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: number;
}

interface CartItem {
  item: MenuItem;
  quantity: number;
}

export default function CartPage() {
  const { user, token } = useAuth();
  const [cart, setCart] = useState<CartItem[]>([]);
  const [note, setNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);

  useEffect(() => {
    const savedCart = localStorage.getItem('cart');
    if (savedCart) {
      setCart(JSON.parse(savedCart));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('cart', JSON.stringify(cart));
  }, [cart]);

  const updateQuantity = (itemId: number, delta: number) => {
    setCart(prev => {
      return prev.map(c => {
        if (c.item.id === itemId) {
          const newQty = c.quantity + delta;
          return newQty > 0 ? { ...c, quantity: newQty } : c;
        }
        return c;
      }).filter(c => c.quantity > 0);
    });
  };

  const removeItem = (itemId: number) => {
    setCart(prev => prev.filter(c => c.item.id !== itemId));
  };

  const clearCart = () => {
    setCart([]);
    localStorage.removeItem('cart');
  };

  const subtotal = cart.reduce((sum, c) => sum + (c.item.price * c.quantity), 0);
  const deliveryFee = 15000;
  const total = subtotal + deliveryFee;

  const submitOrder = async () => {
    if (!user) {
      alert('لطفاً ابتدا وارد شوید');
      return;
    }

    setIsSubmitting(true);

    // Simulate order submission
    await new Promise(resolve => setTimeout(resolve, 1500));

    setOrderSuccess(true);
    clearCart();
    setIsSubmitting(false);
  };

  if (orderSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center" dir="rtl">
        <div className="text-center">
          <div className="text-6xl mb-6">✅</div>
          <h1 className="text-2xl font-bold text-white mb-4">سفارش شما ثبت شد!</h1>
          <p className="text-slate-400 mb-8">به زودی با شما تماس می‌گیریم</p>
          <div className="flex gap-4 justify-center">
            <Link
              href="/restaurants"
              className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl transition"
            >
              ادامه خرید
            </Link>
            <Link
              href="/"
              className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-xl transition"
            >
              چت با روژان
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800" dir="rtl">
      {/* Header */}
      <header className="bg-slate-800/50 backdrop-blur-lg border-b border-slate-700 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/restaurants" className="text-slate-400 hover:text-white transition">
              ← برگشت
            </Link>
            <h1 className="text-xl font-bold text-white">🛒 سبد خرید</h1>
          </div>
          {cart.length > 0 && (
            <button
              onClick={clearCart}
              className="text-red-400 hover:text-red-300 text-sm transition"
            >
              پاک کردن همه
            </button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {cart.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-6xl mb-6">🛒</div>
            <h2 className="text-xl font-bold text-white mb-2">سبد خرید خالی است</h2>
            <p className="text-slate-400 mb-6">برای سفارش، غذا اضافه کنید</p>
            <Link
              href="/restaurants"
              className="inline-block bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl transition"
            >
              مشاهده رستوران‌ها
            </Link>
          </div>
        ) : (
          <div className="grid md:grid-cols-3 gap-6">
            {/* Cart Items */}
            <div className="md:col-span-2 space-y-4">
              {cart.map(({ item, quantity }) => (
                <div
                  key={item.id}
                  className="bg-slate-800/50 rounded-xl border border-slate-700 p-4 flex gap-4"
                >
                  <div className="w-20 h-20 bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-lg flex items-center justify-center text-2xl flex-shrink-0">
                    🍽️
                  </div>

                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-bold text-white">{item.name}</h3>
                      <button
                        onClick={() => removeItem(item.id)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        حذف
                      </button>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-purple-400 font-bold">
                        {(item.price * quantity).toLocaleString()} تومان
                      </span>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQuantity(item.id, -1)}
                          className="w-8 h-8 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
                        >
                          −
                        </button>
                        <span className="text-white font-bold w-6 text-center">{quantity}</span>
                        <button
                          onClick={() => updateQuantity(item.id, 1)}
                          className="w-8 h-8 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition"
                        >
                          +
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Note */}
              <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4">
                <label className="block text-slate-300 mb-2 text-sm">توضیحات سفارش (اختیاری)</label>
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="مثلاً: بدون پیاز، تند باشه..."
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg p-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 resize-none"
                  rows={3}
                />
              </div>
            </div>

            {/* Order Summary */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6 h-fit sticky top-24">
              <h3 className="text-lg font-bold text-white mb-4">خلاصه سفارش</h3>

              <div className="space-y-3 text-sm mb-6">
                <div className="flex justify-between text-slate-300">
                  <span>جمع سفارش</span>
                  <span>{subtotal.toLocaleString()} تومان</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>هزینه ارسال</span>
                  <span>{deliveryFee.toLocaleString()} تومان</span>
                </div>
                <div className="border-t border-slate-700 pt-3 flex justify-between text-white font-bold">
                  <span>جمع کل</span>
                  <span className="text-purple-400">{total.toLocaleString()} تومان</span>
                </div>
              </div>

              {!user ? (
                <div className="text-center">
                  <p className="text-slate-400 text-sm mb-4">برای ثبت سفارش وارد شوید</p>
                  <Link
                    href="/"
                    className="block w-full bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-bold transition text-center"
                  >
                    ورود / ثبت‌نام
                  </Link>
                </div>
              ) : (
                <button
                  onClick={submitOrder}
                  disabled={isSubmitting}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 text-white py-3 rounded-xl font-bold transition"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      در حال ثبت...
                    </span>
                  ) : (
                    'ثبت سفارش'
                  )}
                </button>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
