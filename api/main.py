"""
BiteFit FastAPI Backend
מחליף את Streamlit — מגיש את כל הלוגיקה כ-REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, profile, food_log, recipes, daily_menu, chat, camera, water, barcode

app = FastAPI(title="BiteFit API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/auth",       tags=["auth"])
app.include_router(profile.router,    prefix="/profile",    tags=["profile"])
app.include_router(food_log.router,   prefix="/food-log",   tags=["food-log"])
app.include_router(recipes.router,    prefix="/recipes",    tags=["recipes"])
app.include_router(daily_menu.router, prefix="/daily-menu", tags=["daily-menu"])
app.include_router(chat.router,       prefix="/chat",       tags=["chat"])
app.include_router(camera.router,     prefix="/camera",     tags=["camera"])
app.include_router(water.router,      prefix="/water",      tags=["water"])
app.include_router(barcode.router,    prefix="/barcode",    tags=["barcode"])

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
