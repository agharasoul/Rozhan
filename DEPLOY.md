# 🚀 راهنمای Deploy روژان

## روش ۱: Docker Compose (کامل)

```bash
# Build و Run
docker-compose up -d --build

# مشاهده logs
docker-compose logs -f

# Stop
docker-compose down
```

آدرس‌ها:
- Frontend: http://localhost:3000
- Backend: http://localhost:9999
- pgAdmin: http://localhost:5050

---

## روش ۲: Deploy جداگانه

### Backend (Railway/Render)

1. یه سرویس PostgreSQL بساز (Neon.tech رایگانه)
2. یه سرویس Redis بساز (Upstash رایگانه)
3. Environment variables:
   ```
   DATABASE_URL=postgresql://...
   REDIS_URL=redis://...
   GEMINI_API_KEY=...
   ```
4. Deploy از GitHub

### Frontend (Vercel)

1. به Vercel وصل شو
2. Repo رو import کن
3. Root directory: `frontend`
4. Environment:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```

---

## Environment Variables مورد نیاز

### Backend
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string  
- `GEMINI_API_KEY` - Google Gemini API key

### Frontend
- `NEXT_PUBLIC_API_URL` - Backend API URL
