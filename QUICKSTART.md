# ⚡ QUICKSTART GUIDE

Get your AI Outfit Recommender running in 15 minutes!

## 🎯 Goal

Get a working local version with:
- AI prompt understanding (Llama)
- Product search
- Simple outfit generation
- Swipe interface

**Note**: This quickstart uses simple image compositing, not real virtual try-on. For production quality, follow the full SETUP.md guide.

---

## 📦 Step 1: Install Requirements (5 min)

### A. Install Ollama

**Windows:**
```powershell
iex (irm https://ollama.ai/install.ps1)
```

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

### B. Pull Llama Model

```bash
ollama pull llama3.1:8b-q4_0
```

### C. Install Python & Node

- Python 3.11+: https://python.org
- Node.js 18+: https://nodejs.org

---

## 🔧 Step 2: Setup Backend (5 min)

```bash
cd ai-outfit-app/backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and set DATABASE_URL to your Supabase connection
# Or use SQLite for testing: sqlite:///./test.db
```

### Quick Supabase Setup (2 min):
1. Go to https://supabase.com
2. Sign up (FREE)
3. Create project
4. Copy PostgreSQL connection string
5. Paste in .env as DATABASE_URL
6. In Supabase SQL Editor, run: `CREATE EXTENSION vector;`

---

## 🚀 Step 3: Run Backend (1 min)

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
cd backend
uvicorn app.main:app --reload

# You should see:
# ✅ Database connected
# ✅ Llama model ready
# Running on http://localhost:8000
```

Test it: Open http://localhost:8000/docs

---

## 🎨 Step 4: Setup Frontend (2 min)

```bash
cd frontend/

# Install dependencies
npm install

# Create .env
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env

# Start frontend
npm run dev

# Opens at http://localhost:5173
```

---

## 🎉 Step 5: Test It! (2 min)

1. Open http://localhost:5173
2. Enter prompt: "Beach party, colorful and relaxed"
3. Click "Generate Outfits"
4. Wait ~10 seconds
5. **Swipe through outfits!**

---

## ✅ You're Done!

### What's Working:
- ✅ AI understands your prompts
- ✅ Finds matching products
- ✅ Creates outfit combinations
- ✅ Swipe interface
- ✅ Saves liked outfits

### What's NOT Working Yet:
- ❌ Real virtual try-on (uses simple composites)
- ❌ Only has ~20 products from FakeStoreAPI
- ❌ Not deployed to internet

### Next Steps:

**To get REAL virtual try-on:**
Follow the complete SETUP.md guide to:
1. Setup RunPod for GPU
2. Setup Cloudinary for storage
3. Deploy to production

**To add more products:**
```bash
curl -X POST http://localhost:8000/api/v1/products/sync
```

---

## 🔥 Common Issues

### "Ollama not found"
```bash
# Restart Ollama
ollama serve
```

### "Database error"
- Check DATABASE_URL in .env
- Make sure Supabase project is running
- Run: `CREATE EXTENSION vector;` in Supabase

### "No products found"
```bash
# Sync products
curl -X POST http://localhost:8000/api/v1/products/sync
```

### "Port already in use"
```bash
# Kill process on port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux:
lsof -ti:8000 | xargs kill -9
```

---

## 💰 Costs

**Local Development**: ₹0 (Everything FREE!)

**Production with Real Try-On**: ~₹1500/month
- See SETUP.md for details

---

## 🎯 Ready for Production?

Once your local version works, follow the complete guide:
- `docs/SETUP.md` - Complete setup with production deployment
- `docs/DEPLOYMENT.md` - Deployment specifics

---

## 🆘 Need Help?

1. Check terminal errors
2. Review this guide
3. Check http://localhost:8000/docs for API issues
4. Verify all services are running:
   - Ollama: http://localhost:11434
   - Backend: http://localhost:8000
   - Frontend: http://localhost:5173

**You got this! 🚀**
