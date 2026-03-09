# Deploy Chick-itsa (GitHub + Render)

## 1) Push to GitHub

Run these commands inside the `Chick-itsa` folder:

```powershell
git init
git add .
git commit -m "Prepare Chick-itsa for Render deployment"
git branch -M main
git remote add origin https://github.com/<your-username>/chick-itsa.git
git push -u origin main
```

## 2) Create Render Web Service

1. Open Render dashboard.
2. Click `New` -> `Blueprint`.
3. Select your `chick-itsa` GitHub repo.
4. Render will detect `render.yaml` automatically.
5. Deploy.

## 3) Initialize DB after first deploy

Open the service `Shell` in Render and run:

```bash
flask --app app initdb
```

This creates the admin user and seed data.

## 4) Open public URL

After deploy, use the generated URL (for example `https://chick-itsa.onrender.com`).
