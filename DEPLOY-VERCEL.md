# Deploy GoalShock to Vercel

## Quick Deploy (Recommended)

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Ready for Vercel deployment"
git push origin master
```

### Step 2: Deploy via Vercel Dashboard
1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Configure project:
   - **Framework Preset**: Vite
   - **Root Directory**: `app`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Click "Deploy"

## Deploy via CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to app folder
cd app

# Deploy
vercel --prod
```

## Important: Update Backend URL

After deploying, update the backend URL in your frontend:

### Option 1: Environment Variable (Recommended)
Create `app/.env.production`:
```env
VITE_API_BASE=https://your-backend-url.com
```

Update `App.tsx`:
```typescript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
```

### Option 2: Direct Update
Edit `app/src/App.tsx` line 7:
```typescript
const API_BASE = 'https://your-backend-url.com';
```

## Deploy Backend

Your backend needs to be deployed separately. Options:

### Railway (Recommended - Free Tier)
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Navigate to backend
cd backend

# Initialize and deploy
railway init
railway up
```

### Render
1. Go to https://render.com
2. New → Web Service
3. Connect GitHub repo
4. Root Directory: `backend`
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Digital Ocean App Platform
1. Go to https://cloud.digitalocean.com/apps
2. Create App → GitHub
3. Select repo and branch
4. Component type: Web Service
5. Source directory: `backend`
6. Build command: `pip install -r requirements.txt`
7. Run command: `uvicorn main:app --host 0.0.0.0 --port 8080`

## Environment Variables on Vercel

Add these in Vercel dashboard → Settings → Environment Variables:

```
VITE_API_BASE=https://your-backend-url.com
```

## Test Deployment

After deploying:
1. Visit your Vercel URL
2. Check browser console (F12)
3. Should see "✅ WebSocket connected" if backend is running
4. Click "Start Bot"
5. Button should switch to "Stop Bot"

## Troubleshooting

### "○ Offline" after deployment
- Backend URL is incorrect
- Update `API_BASE` in App.tsx
- Check backend is running at the URL

### CORS Error
Add your Vercel URL to backend CORS:

`backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://your-vercel-app.vercel.app"  # Add this
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### WebSocket not connecting
- Use WSS (secure WebSocket) for production
- Update WebSocket URL in App.tsx:
```typescript
const ws = new WebSocket('wss://your-backend-url.com/ws');
```

## Production Checklist

Before going live:
- [ ] Backend deployed and running
- [ ] Frontend `API_BASE` updated to backend URL
- [ ] CORS configured with Vercel URL
- [ ] WebSocket URL uses `wss://` (not `ws://`)
- [ ] API keys added to backend `.env`
- [ ] Test bot start/stop functionality
- [ ] Check live trades appear

## Custom Domain (Optional)

### Add to Vercel:
1. Vercel Dashboard → Settings → Domains
2. Add your domain
3. Configure DNS records as shown

### Update CORS:
Add custom domain to backend CORS origins list.

## Cost Estimate

- **Vercel Frontend**: Free (Hobby plan)
- **Railway Backend**: Free tier available
- **Total**: $0/month for development

Production with real trading:
- Vercel Pro: $20/month
- Railway Starter: $5/month
- API-Football Pro: $10/month
- **Total**: ~$35/month

## Support

Issues deploying? Check:
- Build logs in Vercel dashboard
- Browser console for errors
- Backend logs in Railway/Render
