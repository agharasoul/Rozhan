/**
 * 💬 API Route برای چت با Gemini
 * بدون نیاز به سرور جداگانه!
 */

import { NextRequest, NextResponse } from 'next/server';

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'AIzaSyD4-5eb9mI0Rf7-iFwCx7YGpF38mDsxJ0E';
const MODEL = 'models/gemini-1.5-flash';
const API_URL = `https://generativelanguage.googleapis.com/v1beta/${MODEL}:generateContent`;

export async function POST(request: NextRequest) {
  try {
    const { message, image } = await request.json();
    
    console.log('Chat request:', { message: message?.slice(0, 50), hasImage: !!image, apiKey: GEMINI_API_KEY?.slice(0, 15) + '...' });

    if (!message && !image) {
      return NextResponse.json({ error: 'No message or image provided' }, { status: 400 });
    }

    if (!GEMINI_API_KEY) {
      console.error('API key is missing!');
      return NextResponse.json({ error: 'API key not configured' }, { status: 500 });
    }

    // ساخت parts
    interface GeminiPart {
      text?: string;
      inline_data?: {
        mime_type: string;
        data: string;
      };
    }
    const parts: GeminiPart[] = [];
    
    if (image) {
      // حذف prefix از base64
      const base64Data = image.includes(',') ? image.split(',')[1] : image;
      parts.push({
        inline_data: {
          mime_type: 'image/jpeg',
          data: base64Data
        }
      });
      
      // اگه متن نداره، یه prompt پیش‌فرض بذار
      if (message) {
        parts.push({ text: message });
      } else {
        parts.push({ text: 'این تصویر رو توضیح بده. فارسی جواب بده.' });
      }
    } else if (message) {
      parts.push({ text: message });
    }

    const response = await fetch(`${API_URL}?key=${GEMINI_API_KEY}`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      },
      body: JSON.stringify({
        contents: [{ parts }]
      })
    });

    console.log('Gemini response status:', response.status);
    
    const responseText = await response.text();
    console.log('Gemini response:', responseText.slice(0, 200));
    
    if (!response.ok) {
      console.error('Gemini error:', responseText);
      return NextResponse.json({ error: 'Gemini API error', detail: responseText }, { status: response.status });
    }
    
    const result = JSON.parse(responseText);
    const answerText = result.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '';

    return NextResponse.json({ response: answerText, customer_id: 'default' });

  } catch (error) {
    console.error('Chat error:', error);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
