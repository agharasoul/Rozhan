"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: number;
  phone: string | null;
  email: string | null;
  name: string | null;
  is_admin?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isLoggedIn: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API_BASE - Dynamic: بر اساس hostname
const getApiBase = () => {
  if (typeof window === 'undefined') return "https://localhost:9999";
  const hostname = window.location.hostname;
  const isSecure = window.location.protocol === 'https:';
  return `${isSecure ? 'https' : 'http'}://${hostname}:9999`;
};
const API_BASE = typeof window !== 'undefined' ? getApiBase() : "https://localhost:9999";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // بارگذاری توکن از localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem('rozhan_token');
    if (savedToken) {
      // تأیید توکن
      fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${savedToken}` }
      })
        .then(res => {
          if (res.ok) return res.json();
          throw new Error('Invalid token');
        })
        .then(data => {
          setToken(savedToken);
          setUser(data.user);
        })
        .catch(() => {
          localStorage.removeItem('rozhan_token');
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem('rozhan_token', newToken);
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    if (token) {
      fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      }).catch(() => {});
    }
    localStorage.removeItem('rozhan_token');
    setToken(null);
    setUser(null);
  };

  const updateUser = (newUser: User) => {
    setUser(newUser);
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      isLoading,
      isLoggedIn: !!token && !!user,
      login,
      logout,
      updateUser
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { API_BASE };
