'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { API_BASE } from '../../contexts/AuthContext';

interface Category {
  id: number;
  name: string;
  icon: string;
  sort_order: number;
}

interface MenuItem {
  id: number;
  name: string;
  description: string;
  price: number;
  discount_price: number | null;
  image_url: string | null;
  category_id: number;
  is_available: number;
}

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
  description: string;
}

interface CartItem {
  item: MenuItem;
  quantity: number;
}

export default function RestaurantPage() {
  const params = useParams();
  const restaurantId = params.id;

  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load cart from localStorage
    const savedCart = localStorage.getItem('cart');
    if (savedCart) {
      setCart(JSON.parse(savedCart));
    }

    // Fetch restaurant
    fetch(`${API_BASE}/restaurants/${restaurantId}`)
      .then(res => res.json())
      .then(data => setRestaurant(data))
      .catch(console.error);

    // Fetch menu
    fetch(`${API_BASE}/restaurants/${restaurantId}/menu`)
      .then(res => res.json())
      .then(data => {
        setCategories(data.categories || []);
        setMenuItems(data.items || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [restaurantId]);

  // Save cart to localStorage
  useEffect(() => {
    localStorage.setItem('cart', JSON.stringify(cart));
  }, [cart]);

  const addToCart = (item: MenuItem) => {
    setCart(prev => {
      const existing = prev.find(c => c.item.id === item.id);
      if (existing) {
        return prev.map(c => 
          c.item.id === item.id 
            ? { ...c, quantity: c.quantity + 1 }
            : c
        );
      }
      return [...prev, { item, quantity: 1 }];
    });
  };

  const removeFromCart = (itemId: number) => {
    setCart(prev => {
      const existing = prev.find(c => c.item.id === itemId);
      if (existing && existing.quantity > 1) {
        return prev.map(c => 
          c.item.id === itemId 
            ? { ...c, quantity: c.quantity - 1 }
            : c
        );
      }
      return prev.filter(c => c.item.id !== itemId);
    });
  };

  const getCartQuantity = (itemId: number) => {
    return cart.find(c => c.item.id === itemId)?.quantity || 0;
  };

  const totalItems = cart.reduce((sum, c) => sum + c.quantity, 0);
  const totalPrice = cart.reduce((sum, c) => sum + (c.item.price * c.quantity), 0);

  const filteredItems = selectedCategory
    ? menuItems.filter(item => item.category_id === selectedCategory)
    : menuItems;

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
          <div className="flex items-center gap-4">
            <Link href="/restaurants" className="text-slate-400 hover:text-white transition">
              ← برگشت
            </Link>
            <span className="text-2xl">{restaurant?.logo_url || '🍽️'}</span>
            <h1 className="text-xl font-bold text-white">{restaurant?.name}</h1>
          </div>
          <Link 
            href="/cart" 
            className="relative bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-full transition flex items-center gap-2"
          >
            🛒 سبد خرید
            {totalItems > 0 && (
              <span className="bg-pink-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                {totalItems}
              </span>
            )}
          </Link>
        </div>
      </header>

      {/* Restaurant Info */}
      <div className="bg-gradient-to-br from-purple-600/20 to-pink-600/20 border-b border-slate-700">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center gap-4 text-sm text-slate-300">
            <span className="text-yellow-400">⭐ {restaurant?.rating}</span>
            <span>📍 {restaurant?.address}</span>
            <span>📞 {restaurant?.phone}</span>
            <span className={restaurant?.is_open ? 'text-green-400' : 'text-red-400'}>
              {restaurant?.is_open ? '🟢 باز' : '🔴 بسته'}
            </span>
          </div>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Categories */}
        <div className="flex gap-2 overflow-x-auto pb-4 mb-6 scrollbar-hide">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-4 py-2 rounded-full whitespace-nowrap transition ${
              selectedCategory === null
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            همه
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-4 py-2 rounded-full whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>

        {/* Menu Items */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredItems.map(item => {
            const quantity = getCartQuantity(item.id);
            return (
              <div
                key={item.id}
                className="bg-slate-800/50 rounded-xl border border-slate-700 p-4 flex gap-4"
              >
                {/* Image */}
                <div className="w-24 h-24 bg-gradient-to-br from-purple-600/20 to-pink-600/20 rounded-lg flex items-center justify-center text-3xl flex-shrink-0">
                  🍽️
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-white mb-1">{item.name}</h3>
                  <p className="text-slate-400 text-sm mb-2 line-clamp-2">{item.description}</p>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-purple-400 font-bold">
                      {item.price.toLocaleString()} تومان
                    </span>

                    {/* Add/Remove buttons */}
                    {quantity === 0 ? (
                      <button
                        onClick={() => addToCart(item)}
                        className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-1.5 rounded-lg text-sm transition"
                      >
                        + افزودن
                      </button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => removeFromCart(item.id)}
                          className="w-8 h-8 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition"
                        >
                          −
                        </button>
                        <span className="text-white font-bold w-6 text-center">{quantity}</span>
                        <button
                          onClick={() => addToCart(item)}
                          className="w-8 h-8 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition"
                        >
                          +
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </main>

      {/* Fixed Cart Bar */}
      {totalItems > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-slate-800/95 backdrop-blur-lg border-t border-slate-700 p-4">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="text-white">
              <span className="text-slate-400">جمع کل:</span>{' '}
              <span className="font-bold text-lg">{totalPrice.toLocaleString()} تومان</span>
            </div>
            <Link
              href="/cart"
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-8 py-3 rounded-xl font-bold transition"
            >
              مشاهده سبد ({totalItems})
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
