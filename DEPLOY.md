# WMS — bepul public deploy (Neon + Render + Vercel)

Arxitektura: **Frontend → Vercel**, **Backend → Render** (fon workerlari + SSE),
**Postgres → Neon**. Frontend `/api/*` so'rovlarини Vercel rewrite orqali Render'ga
uzatadi — CORS muammosi yo'q.

```
Brauzer → Vercel (React SPA) ──/api/*──▶ Render (FastAPI) ──▶ Neon (Postgres)
```

---

## 1. Neon — Postgres (bepul)

1. https://neon.tech → **Create project** (region: Europe/Frankfurt tavsiya).
2. Connection string'ni oling (**Pooled** emas, oddiy ham bo'ladi). U shunga o'xshaydi:
   ```
   postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
3. Backend uchun `postgresql://` ni **`postgresql+asyncpg://`** ga o'zgartiring:
   ```
   postgresql+asyncpg://user:pass@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
   `sslmode`/`channel_binding` paramlari avtomatik hal qilinadi (kod normalizatsiya qiladi).

## 2. Render — backend (bepul web service)

1. https://render.com → **New → Blueprint** → GitHub reponi ulang → `render.yaml` topiladi.
2. Yaratishdan oldin quyidagi env larni kiriting (`sync: false` bo'lganlari):
   - `DATABASE_URL` = yuqoridagi `postgresql+asyncpg://…` (Neon).
   - `CORS_ORIGINS` = hozircha bo'sh qoldiring yoki `https://example.com` (Vercel URL'ini 3-qadamdan keyin yangilaysiz).
   - `JWT_SECRET_KEY`, `ENCRYPTION_KEY` — avtomatik generatsiya (tegmang).
3. Deploy tugagach Render URL'ini oling: `https://wms-backend-XXXX.onrender.com`.
   Tekshiring: `…/health` → `{"status":"ok"}`, `…/health/ready` → DB + workerlar `ok`.
4. Startda avtomatik: migratsiyalar → demo seed (**admin@wms.uz / admin123**) → server.

> Bepul Render 15 daqiqa harakatsizlikdan keyin uxlaydi; birinchi so'rov ~30s sekin
> (cold start). Demo uchun yetarli.

## 3. Vercel — frontend

1. `vercel.json` dagi `REPLACE-WITH-RENDER-URL` ni **2-qadamdagi Render URL** bilan almashtiring:
   ```json
   { "source": "/api/:path*", "destination": "https://wms-backend-XXXX.onrender.com/api/:path*" }
   ```
   Commit + push qiling.
2. https://vercel.com → **Add New → Project** → reponi import qiling.
   `vercel.json` build buyrug'ini o'zi topadi (root katalog = repo ildizi, o'zgartirmang).
3. Deploy tugagach Vercel URL'ini oling: `https://wms-xxx.vercel.app`.
4. Render'da `CORS_ORIGINS` ni shu Vercel URL'iga yangilang (SSE/xavfsizlik uchun) → Render qayta deploy.

## 4. Tekshirish

1. `https://wms-xxx.vercel.app` → login: **admin@wms.uz / admin123**.
2. Sklad → 3D → yurish/qidiruv ishlashini ko'ring.
3. O'ng yuqorida **"Jonli"** indikatori yashil bo'lishi kerak (SSE ishlayapti).

---

## Xavfsizlik eslatmalari (public repo)

- `.env` hech qachon commit qilinmaydi (`.gitignore` himoyalaydi) — sirlar faqat
  Render/Vercel dashboard env larida.
- Demo admin paroli (`admin123`) — faqat ko'rgazma uchun. Haqiqiy foydalanishda
  Sozlamalar orqali o'zgartiring yoki `scripts/seed_admin.py` dagi parolni yangilang.
- `firmware/` ичидаги ESP32 WiFi paroli / API kaliti — bu public repoda ochiq.
  Real qurilma sirlarini keyinroq alohida (env/secret) ga ko'chiring.

## Keyingi (ixtiyoriy)

- Custom domen (Vercel bepul), Sentry (`SENTRY_DSN`), Neon avtomatik backup.
- Render'ni "always-on" qilish uchun pullik plan yoki tashqi ping (cron-job.org).
