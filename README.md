# ✨ AI Outfit Recommender

AI-powered outfit recommendation app with virtual try-on. Browse fashion from ASOS & Amazon, swipe to find your style, and see how outfits look on you!

## 🎯 Features

- **Multi-Store Browse**: Shop from ASOS and Amazon
- **Mix Stores**: Combine products (ASOS top + Amazon bottom)
- **AI-Powered**: LLM understands your style prompts
- **Virtual Try-On**: See outfits on a model using AI (IDM-VTON)
- **Swipe Interface**: Tinder-style browsing
- **Rate Limited**: Fair usage with per-user limits
- **Google Sign-In**: Firebase authentication

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Python web framework
- **Groq** - LLM for prompt parsing (Llama 3.3 70B)
- **Replicate** - Virtual try-on (IDM-VTON model)
- **Cloudinary** - Image storage
- **Firebase Admin** - Authentication
- **SQLite** - Usage tracking

### Frontend
- **React 18** + Vite
- **Firebase Auth** - Google sign-in
- **Framer Motion** - Animations
- **react-tinder-card** - Swipe interface

### APIs
- **RapidAPI ASOS** - ASOS product search
- **RapidAPI Amazon** - Amazon product search

## 📁 Project Structure

```
outfit-planner/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints
│   │   ├── config.py            # Environment config
│   │   ├── models.py            # Pydantic models
│   │   └── services/
│   │       ├── asos_service.py      # ASOS API
│   │       ├── amazon_service.py    # Amazon API
│   │       ├── llm_service.py       # Groq LLM
│   │       ├── tryon_service.py     # Virtual try-on
│   │       ├── product_service.py   # Outfit combinations
│   │       ├── firebase_auth.py     # Auth verification
│   │       └── usage_tracker.py     # Rate limiting
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app
│   │   ├── App.css              # Styles
│   │   ├── config/firebase.js   # Firebase config
│   │   ├── context/AuthContext.jsx
│   │   ├── services/api.js      # API client
│   │   └── utils/imageExtractor.js
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── docker-compose.prod.yml
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- RapidAPI account (ASOS & Amazon APIs)
- Firebase project (for auth)
- Cloudinary account
- Replicate account
- Groq account

### 1. Clone & Setup Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

### 2. Setup Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env with your Firebase config
```

### 3. Run Development

```bash
# Terminal 1 - Backend
cd backend
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open http://localhost:5173

## 🔑 Environment Variables

### Backend (.env)
```env
# Required
RAPIDAPI_KEY=your_rapidapi_key
GROQ_API_KEY=your_groq_key
CLOUDINARY_CLOUD_NAME=your_cloud
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
REPLICATE_API_TOKEN=your_token

# Firebase (for auth)
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
```

## 📊 Rate Limits

| Limit Type | Value |
|------------|-------|
| Per User - Searches | 1 (lifetime) |
| Per User - Try-ons | 1 (lifetime) |
| Global - Searches | 100 total |
| Global - Try-ons | 50 total |

## 🐳 Docker Deployment

```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up -d
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/outfits/browse-asos` | POST | Search ASOS |
| `/api/v1/outfits/browse-amazon` | POST | Search Amazon |
| `/api/v1/outfits/browse-mixed` | POST | Search both (mixed combos) |
| `/api/v1/outfits/tryon` | POST | Generate virtual try-on |
| `/api/v1/upload/model-image` | POST | Upload user photo |
| `/api/v1/usage` | GET | Get usage stats |
| `/api/v1/admin/stats` | GET | Admin statistics |
| `/health` | GET | Health check |

## 🔒 Security Notes

- Never commit `.env` files
- Firebase service account keys are sensitive
- All API keys should be kept secret
- CORS is configured for specific origins

## 📝 License

MIT License - Feel free to use and modify!

---

Built with ❤️ using AI
