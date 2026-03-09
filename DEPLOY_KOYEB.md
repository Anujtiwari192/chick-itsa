# Deploy Chick-itsa on Koyeb (Free)

## 1) Push latest code to GitHub

```powershell
cd "C:\Users\91922\OneDrive\Desktop\New folder\DevMode\Projects\Chick-itsa"
git add .
git commit -m "Add Koyeb deployment setup"
git push origin main
```

## 2) Create app on Koyeb

1. Open `https://app.koyeb.com/`
2. Click `Create Web Service`
3. Choose `GitHub` as source
4. Select repo `Anujtiwari192/chick-itsa`
5. Branch: `main`
6. Build method: `Dockerfile` (auto-detected from repo root)
7. Instance type: `Free`
8. Expose port: `8000`
9. Set environment variable:
   - `SECRET_KEY` = any long random string
10. Click `Deploy`

## 3) Access app

Koyeb will provide a public URL like:
`https://<service-name>-<org>.koyeb.app`

The database is auto-initialized on startup (`AUTO_INIT_DB=1`), so no paid shell is required.

## 4) Default credentials (change after login)

- Admin: `admin`
- Password: `admin123`
