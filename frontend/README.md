# TrustScore React Frontend

Modern React UI with 3D (Three.js), GSAP, and Framer Motion.

## Run

```bash
# 1. Start backend (from project root)
cd backend/server
uvicorn main:app --reload --port 8000

# 2. Start React dev server
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. API calls are proxied to the backend at 8000.

## Build

```bash
npm run build
# Output in dist/
```

## Tech Stack

- React 19 + Vite
- React Router
- Three.js / React Three Fiber / Drei (3D hero)
- GSAP (landing animations)
- Framer Motion (page transitions, hover)
- Space Grotesk + JetBrains Mono fonts
