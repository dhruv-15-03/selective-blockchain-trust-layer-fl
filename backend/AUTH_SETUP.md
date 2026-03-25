# Auth Setup (Login / Sign Up)

## 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
# Or: pip install sqlalchemy psycopg2-binary passlib python-jose pydantic[email] python-dotenv
```

## 2. Database (Neon / Aiven / PostgreSQL)

**Option A: Use Neon/Aiven (production)**  
1. Create a PostgreSQL database (Neon, Aiven, Supabase, etc.)  
2. Copy `backend/server/.env.example` to `backend/server/.env`  
3. Add your connection string:
   ```
   DATABASE_URL=postgresql://user:password@host:5432/dbname?sslmode=require
   ```
4. Tables are auto-created on first run.

**Option B: Dev without DB**  
If `DATABASE_URL` is not set, SQLite in-memory is used. Data won't persist across restarts.

## 3. Run backend

```bash
cd backend/server
uvicorn main:app --reload --port 8000
```

## 4. Frontend

Login: http://localhost:5174/login  
Sign Up: http://localhost:5174/signup  

Token is stored in `localStorage` after login.
