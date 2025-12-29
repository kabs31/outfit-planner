# 🚀 SETUP GUIDE - AI Outfit Recommender

Complete step-by-step guide to set up your AI outfit recommendation app.

---

## 📋 Prerequisites

### Your System:
- ✅ HP OMEN (16GB RAM, 8GB GPU)
- ✅ Windows/Linux
- ✅ Internet connection

### Software Required:
- Python 3.11+ ([Download](https://www.python.org/downloads/))
- Node.js 18+ ([Download](https://nodejs.org/))
- Git ([Download](https://git-scm.com/))
- VS Code or any code editor

---

## 🏗️ PHASE 1: LOCAL DEVELOPMENT (Week 1-2)

### Step 1: Setup Environment

#### A. Install Python Dependencies

```bash
# Navigate to backend folder
cd ai-outfit-app/backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### B. Install Ollama & Llama 3.1

```bash
# Windows/Linux - Download from https://ollama.ai
# Or use this command:

# Windows (PowerShell):
iex (irm https://ollama.ai/install.ps1)

# Linux:
curl https://ollama.ai/install.sh | sh

# Pull Llama 3.1 8B (4-bit quantized for your 8GB GPU)
ollama pull llama3.1:8b-q4_0
```

#### C. Setup Supabase Database (FREE)

1. Go to [supabase.com](https://supabase.com)
2. Create free account
3. Create new project
4. Go to Settings → Database
5. Copy "Connection string" (PostgreSQL)
6. Enable pgvector extension:
   - Go to SQL Editor
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

### Step 2: Configure Backend

#### A. Create .env file

```bash
cd backend/
```

Create `.env` file with this content:

```env
# App Config
DEBUG=True
APP_NAME="AI Outfit Recommender"
APP_VERSION="1.0.0"

# Database (Supabase)
DATABASE_URL=postgresql://your_user:your_password@db.xxx.supabase.co:5432/postgres

# Ollama/Llama (Local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b-q4_0

# RunPod (Leave empty for local development)
RUNPOD_API_KEY=
RUNPOD_ENDPOINT_ID=

# Cloudinary (Leave empty for local development)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Model Image URL (use default)
MODEL_IMAGE_URL=https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=768&fit=crop

# Product API
FAKE_STORE_API=https://fakestoreapi.com
```

#### B. Initialize Database

```bash
cd backend/app
python database.py
```

This will:
- Create all tables
- Enable pgvector
- Create indexes
- Verify connection

#### C. Sync Products

```bash
# Run main app first
cd backend
uvicorn app.main:app --reload

# Then in another terminal, sync products:
curl -X POST http://localhost:8000/api/v1/products/sync
```

#### D. Test Backend

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
cd backend
uvicorn app.main:app --reload

# Should see:
# ✅ Database connected
# ✅ Llama model ready
# Application running on http://localhost:8000
```

Visit http://localhost:8000/docs to see API documentation.

### Step 3: Setup Frontend

#### A. Install Dependencies

```bash
cd frontend/
npm install
```

#### B. Configure Environment

Create `.env` file in `frontend/`:

```env
VITE_API_URL=http://localhost:8000/api/v1
```

#### C. Start Frontend

```bash
npm run dev

# Should see:
# Local: http://localhost:5173
```

### Step 4: Test End-to-End (LOCAL MODE)

1. **Start Ollama**: `ollama serve`
2. **Start Backend**: `cd backend && uvicorn app.main:app --reload`
3. **Start Frontend**: `cd frontend && npm run dev`
4. **Open Browser**: http://localhost:5173
5. **Test Prompt**: "Beach party, colorful and relaxed"

**Note**: In local mode, virtual try-on uses simple image compositing (not real AI). This is for testing only.

---

## 🚀 PHASE 2: PRODUCTION DEPLOYMENT (Week 3-4)

### Step 1: Setup RunPod (GPU for Virtual Try-On)

1. Go to [runpod.io](https://runpod.io)
2. Create account
3. Add $10-20 credits
4. Create Serverless Endpoint:
   - Template: PyTorch 2.0
   - GPU: RTX 4090 or A5000
   - Install IDM-VTON:

```python
# In RunPod endpoint handler
import torch
from diffusers import AutoPipelineForImage2Image

# Load IDM-VTON model
pipe = AutoPipelineForImage2Image.from_pretrained(
    "yisol/IDM-VTON",
    torch_dtype=torch.float16
).to("cuda")

def handler(event):
    # Your try-on code
    pass
```

5. Copy Endpoint ID and API Key

### Step 2: Setup Cloudinary (Image Storage)

1. Go to [cloudinary.com](https://cloudinary.com)
2. Create free account (25GB storage FREE)
3. Copy:
   - Cloud Name
   - API Key
   - API Secret

### Step 3: Deploy Backend (Railway)

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Create new project
4. Add PostgreSQL database
5. Deploy from GitHub or CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
cd backend
railway init

# Add environment variables in Railway dashboard:
# - DATABASE_URL (auto-added)
# - OLLAMA_HOST=http://your-ollama-server
# - RUNPOD_API_KEY=xxx
# - CLOUDINARY_CLOUD_NAME=xxx
# etc.

# Deploy
railway up
```

**Cost**: ~₹500/month

### Step 4: Deploy Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Import your frontend folder
4. Configure:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`
5. Add environment variable:
   - `VITE_API_URL=https://your-backend.railway.app/api/v1`
6. Deploy

**Cost**: FREE! 🎉

### Step 5: Get Domain (Optional)

1. Go to [namecheap.com](https://namecheap.com)
2. Buy domain (~₹800/year)
3. Point to Vercel:
   - Add CNAME record
   - Value: cname.vercel-dns.com
4. Configure in Vercel dashboard

---

## 🎯 VERIFICATION CHECKLIST

### Local Development:
- [ ] Ollama installed and running
- [ ] Llama 3.1 model downloaded
- [ ] Python dependencies installed
- [ ] Database connected
- [ ] Products synced
- [ ] Backend API working (http://localhost:8000/docs)
- [ ] Frontend running (http://localhost:5173)
- [ ] Can generate outfits (simple mode)

### Production:
- [ ] RunPod endpoint created
- [ ] Cloudinary configured
- [ ] Backend deployed to Railway
- [ ] Frontend deployed to Vercel
- [ ] Environment variables set
- [ ] Can generate outfits with REAL virtual try-on
- [ ] Domain connected (optional)

---

## 🔧 TROUBLESHOOTING

### "Ollama not found"
```bash
# Restart Ollama service
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### "Database connection failed"
- Check Supabase connection string
- Verify pgvector extension enabled
- Check firewall/network

### "No products found"
```bash
# Re-sync products
curl -X POST http://localhost:8000/api/v1/products/sync
```

### "GPU out of memory"
- Use 4-bit quantized model: `llama3.1:8b-q4_0`
- Close other GPU applications
- Reduce batch size

### "Frontend can't connect to backend"
- Check VITE_API_URL in frontend/.env
- Verify CORS settings in backend
- Check backend is running

---

## 📊 COST SUMMARY

### Development (Month 1-2): ₹0
- Everything runs locally
- FREE Supabase database
- FREE Cloudinary storage

### Production (Month 1): ~₹1500
- Supabase: FREE
- Cloudinary: FREE
- Railway: ₹500
- Vercel: FREE
- RunPod: ₹500-1000 (for 50-100 images)
- Domain: ₹800 (optional, one-time)

### Production (Month 2+): ~₹700-1000
- No domain cost
- Same monthly costs

---

## 🎉 NEXT STEPS

Once everything is working:

1. **Generate test outfits** - Try different prompts
2. **Monitor costs** - Check Railway, RunPod usage
3. **Gather feedback** - Share with friends
4. **Add features** - User accounts, favorites, etc.
5. **Scale up** - More products, better try-on quality

---

## 🆘 SUPPORT

Issues? Check:
1. This guide
2. API docs: http://localhost:8000/docs
3. Logs: Backend console, Railway logs
4. Database: Supabase dashboard

Still stuck? Review the code comments - everything is documented!

---

## 🎯 Timeline

- **Week 1**: Setup local environment, test basic functionality
- **Week 2**: Perfect the system, add products, test thoroughly
- **Week 3**: Deploy backend and frontend
- **Week 4**: Add RunPod, test real virtual try-on, GO LIVE!

**You can do this!** 🚀
