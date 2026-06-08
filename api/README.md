# BiteFit API

FastAPI backend for the BiteFit React Native app.

## Run locally
```bash
pip install -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

## Endpoints
- POST /auth/login
- POST /auth/signup
- GET  /profile/
- PUT  /profile/
- GET  /profile/targets
- GET  /food-log/{date}
- POST /food-log/
- GET  /food-log/{date}/summary
- GET  /recipes/?q=...
- GET  /recipes/{id}
- GET  /daily-menu/plan
- GET  /daily-menu/suggestions/{meal_type}
- POST /chat/
- POST /camera/identify
- GET  /water/{date}
- POST /water/
- GET  /barcode/{barcode}
