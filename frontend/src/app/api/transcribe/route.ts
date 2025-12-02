/**
 * 🎤 API Route برای تبدیل صدا به متن
 * بدون نیاز به سرور جداگانه!
 */

import { NextRequest, NextResponse } from 'next/server';

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';
const MODEL = 'models/gemini-1.5-flash';
const API_URL = `https://generativelanguage.googleapis.com/v1beta/${MODEL}:generateContent`;

export async function POST(request: NextRequest) {
  try {
    const { audio, mime_type = 'audio/webm' } = await request.json();

    if (!audio) {
      return NextResponse.json({ error: 'No audio provided' }, { status: 400 });
    }

    if (!GEMINI_API_KEY) {
      return NextResponse.json({ error: 'API key not configured' }, { status: 500 });
    }

    const response = await fetch(`${API_URL}?key=${GEMINI_API_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{
          parts: [
            {
              text: 'این یک فایل صوتی فارسی است. لطفاً دقیقاً متن گفته‌شده را بنویس. فقط متن، بدون هیچ توضیح اضافه‌ای.'
            },
            {
              inline_data: {
                mime_type: mime_type,
                data: audio
              }
            }
          ]
        }]
      })
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Gemini API error' }, { status: response.status });
    }

    const result = await response.json();
    const text = result.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '';

    return NextResponse.json({ text });

  } catch (error) {
    console.error('Transcribe error:', error);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
