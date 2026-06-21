"""
BiteFit FastAPI Backend
מחליף את Streamlit — מגיש את כל הלוגיקה כ-REST API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from api.routers import auth, profile, food_log, recipes, daily_menu, chat, camera, water, barcode, workout, inventory, meal_balance, adaptation

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
app.include_router(workout.router,    prefix="/workout",    tags=["workout"])
app.include_router(inventory.router,  prefix="/inventory",  tags=["inventory"])
app.include_router(meal_balance.router,  prefix="/meal-balance",  tags=["meal-balance"])
app.include_router(adaptation.router,   prefix="/adaptation",    tags=["adaptation"])

_images_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage_agents", "recipe_images", "approved")
if os.path.exists(_images_path):
    app.mount("/recipe-images", StaticFiles(directory=_images_path), name="recipe-images")

# User-captured food photos (from the camera identify flow).
_photos_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage_agents", "food_photos")
os.makedirs(_photos_path, exist_ok=True)
app.mount("/food-photos", StaticFiles(directory=_photos_path), name="food-photos")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
