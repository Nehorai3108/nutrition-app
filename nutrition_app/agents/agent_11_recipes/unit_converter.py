#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
המרת יחידות מתכון — מגרמים ליחידות ביתיות להצגה
"""

from __future__ import annotations

import math
from typing import Dict, Optional

# ── Household unit conversion table ─────────────────────────────────────────
# Maps English food name (lowercase) to Hebrew household unit info.
# grams_per_unit = weight of one household unit in grams.
# category: for fallback logic (liquid, spice, grain, etc.)

HOUSEHOLD_UNITS: Dict[str, dict] = {
    # ── Eggs & dairy ────────────────────────────────────────────────────────
    "egg":            {"unit_he": "ביצה",          "unit_he_plural": "ביצים",          "grams_per_unit": 50,  "category": "countable"},
    "cheese":         {"unit_he": "פרוסת גבינה",   "unit_he_plural": "פרוסות גבינה",   "grams_per_unit": 28,  "category": "countable"},
    "yellow cheese":  {"unit_he": "פרוסת גבינה צהובה", "unit_he_plural": "פרוסות גבינה צהובה", "grams_per_unit": 28, "category": "countable"},
    "white cheese":   {"unit_he": "כף גבינה לבנה", "unit_he_plural": "כפות גבינה לבנה", "grams_per_unit": 15, "category": "spoon"},
    "cottage cheese": {"unit_he": "כף קוטג׳",      "unit_he_plural": "כפות קוטג׳",     "grams_per_unit": 15,  "category": "spoon"},
    "cream cheese":   {"unit_he": "כף גבינת שמנת", "unit_he_plural": "כפות גבינת שמנת","grams_per_unit": 15,  "category": "spoon"},
    "yogurt":         {"unit_he": "כוס יוגורט",    "unit_he_plural": "כוסות יוגורט",   "grams_per_unit": 150, "category": "cup"},
    "greek yogurt":   {"unit_he": "כוס יוגורט יווני","unit_he_plural": "כוסות יוגורט יווני","grams_per_unit": 150,"category": "cup"},
    "milk":           {"unit_he": "כוס חלב",       "unit_he_plural": "כוסות חלב",      "grams_per_unit": 240, "category": "liquid"},
    "butter":         {"unit_he": "כף חמאה",       "unit_he_plural": "כפות חמאה",      "grams_per_unit": 14,  "category": "spoon"},
    "labneh":         {"unit_he": "כף לבנה",       "unit_he_plural": "כפות לבנה",      "grams_per_unit": 15,  "category": "spoon"},
    "sour cream":     {"unit_he": "כף שמנת חמוצה", "unit_he_plural": "כפות שמנת חמוצה","grams_per_unit": 15,  "category": "spoon"},
    "heavy cream":    {"unit_he": "כף שמנת מתוקה", "unit_he_plural": "כפות שמנת מתוקה","grams_per_unit": 15,  "category": "spoon"},
    "feta cheese":    {"unit_he": "פרוסת פטה",     "unit_he_plural": "פרוסות פטה",     "grams_per_unit": 28,  "category": "countable"},
    "mozzarella":     {"unit_he": "פרוסת מוצרלה",  "unit_he_plural": "פרוסות מוצרלה",  "grams_per_unit": 28,  "category": "countable"},
    "parmesan":       {"unit_he": "כף פרמזן",      "unit_he_plural": "כפות פרמזן",     "grams_per_unit": 10,  "category": "spoon"},

    # ── Vegetables ──────────────────────────────────────────────────────────
    "tomato":         {"unit_he": "עגבנייה",       "unit_he_plural": "עגבניות",        "grams_per_unit": 150, "category": "countable"},
    "cherry tomato":  {"unit_he": "עגבנייה שרי",   "unit_he_plural": "עגבניות שרי",    "grams_per_unit": 15,  "category": "countable"},
    "cucumber":       {"unit_he": "מלפפון",        "unit_he_plural": "מלפפונים",       "grams_per_unit": 120, "category": "countable"},
    "onion":          {"unit_he": "בצל",           "unit_he_plural": "בצלים",          "grams_per_unit": 110, "category": "countable"},
    "red onion":      {"unit_he": "בצל סגול",      "unit_he_plural": "בצלים סגולים",   "grams_per_unit": 110, "category": "countable"},
    "green onion":    {"unit_he": "בצל ירוק",      "unit_he_plural": "בצלים ירוקים",   "grams_per_unit": 15,  "category": "countable"},
    "scallion":       {"unit_he": "בצל ירוק",      "unit_he_plural": "בצלים ירוקים",   "grams_per_unit": 15,  "category": "countable"},
    "pepper":         {"unit_he": "פלפל",          "unit_he_plural": "פלפלים",         "grams_per_unit": 150, "category": "countable"},
    "bell pepper":    {"unit_he": "פלפל",          "unit_he_plural": "פלפלים",         "grams_per_unit": 150, "category": "countable"},
    "red pepper":     {"unit_he": "פלפל אדום",     "unit_he_plural": "פלפלים אדומים",  "grams_per_unit": 150, "category": "countable"},
    "carrot":         {"unit_he": "גזר",           "unit_he_plural": "גזרים",          "grams_per_unit": 70,  "category": "countable"},
    "potato":         {"unit_he": "תפוח אדמה",    "unit_he_plural": "תפוחי אדמה",    "grams_per_unit": 150, "category": "countable"},
    "sweet potato":   {"unit_he": "בטטה",          "unit_he_plural": "בטטות",          "grams_per_unit": 200, "category": "countable"},
    "eggplant":       {"unit_he": "חציל",          "unit_he_plural": "חצילים",         "grams_per_unit": 300, "category": "countable"},
    "zucchini":       {"unit_he": "קישוא",         "unit_he_plural": "קישואים",        "grams_per_unit": 200, "category": "countable"},
    "lettuce":        {"unit_he": "עלה חסה",       "unit_he_plural": "עלי חסה",        "grams_per_unit": 10,  "category": "countable"},
    "spinach":        {"unit_he": "כוס תרד",       "unit_he_plural": "כוסות תרד",      "grams_per_unit": 30,  "category": "cup"},
    "broccoli":       {"unit_he": "פרח ברוקולי",   "unit_he_plural": "פרחי ברוקולי",   "grams_per_unit": 30,  "category": "countable"},
    "cauliflower":    {"unit_he": "פרח כרובית",    "unit_he_plural": "פרחי כרובית",    "grams_per_unit": 30,  "category": "countable"},
    "cabbage":        {"unit_he": "כוס כרוב קצוץ", "unit_he_plural": "כוסות כרוב קצוץ","grams_per_unit": 70,  "category": "cup"},
    "mushroom":       {"unit_he": "פטרייה",        "unit_he_plural": "פטריות",         "grams_per_unit": 18,  "category": "countable"},
    "corn":           {"unit_he": "קלח תירס",      "unit_he_plural": "קלחי תירס",      "grams_per_unit": 150, "category": "countable"},
    "garlic":         {"unit_he": "שן שום",        "unit_he_plural": "שיני שום",       "grams_per_unit": 4,   "category": "countable"},
    "ginger":         {"unit_he": "כפית ג׳ינג׳ר מגורד","unit_he_plural":"כפיות ג׳ינג׳ר מגורד","grams_per_unit": 5, "category": "spoon"},
    "celery":         {"unit_he": "קנה סלרי",      "unit_he_plural": "קני סלרי",       "grams_per_unit": 40,  "category": "countable"},
    "beet":           {"unit_he": "סלק",           "unit_he_plural": "סלקים",          "grams_per_unit": 130, "category": "countable"},
    "radish":         {"unit_he": "צנונית",        "unit_he_plural": "צנוניות",        "grams_per_unit": 10,  "category": "countable"},
    "parsley":        {"unit_he": "כף פטרוזיליה",  "unit_he_plural": "כפות פטרוזיליה", "grams_per_unit": 4,   "category": "spoon"},
    "cilantro":       {"unit_he": "כף כוסברה",     "unit_he_plural": "כפות כוסברה",    "grams_per_unit": 4,   "category": "spoon"},
    "dill":           {"unit_he": "כף שמיר",       "unit_he_plural": "כפות שמיר",      "grams_per_unit": 4,   "category": "spoon"},
    "mint":           {"unit_he": "כף נענע",       "unit_he_plural": "כפות נענע",      "grams_per_unit": 4,   "category": "spoon"},
    "basil":          {"unit_he": "כף בזיליקום",   "unit_he_plural": "כפות בזיליקום",  "grams_per_unit": 4,   "category": "spoon"},
    "artichoke":      {"unit_he": "ארטישוק",       "unit_he_plural": "ארטישוקים",      "grams_per_unit": 120, "category": "countable"},
    "fennel":         {"unit_he": "שומר",          "unit_he_plural": "שומרים",         "grams_per_unit": 200, "category": "countable"},
    "leek":           {"unit_he": "כרישה",         "unit_he_plural": "כרישות",         "grams_per_unit": 90,  "category": "countable"},
    "okra":           {"unit_he": "במיה",          "unit_he_plural": "במיות",          "grams_per_unit": 10,  "category": "countable"},
    "peas":           {"unit_he": "כוס אפונה",     "unit_he_plural": "כוסות אפונה",    "grams_per_unit": 145, "category": "cup"},
    "green beans":    {"unit_he": "כוס שעועית ירוקה","unit_he_plural":"כוסות שעועית ירוקה","grams_per_unit": 110,"category": "cup"},
    "asparagus":      {"unit_he": "אספרגוס",       "unit_he_plural": "אספרגוסים",      "grams_per_unit": 16,  "category": "countable"},
    "kohlrabi":       {"unit_he": "קולורבי",       "unit_he_plural": "קולורבים",       "grams_per_unit": 150, "category": "countable"},
    "turnip":         {"unit_he": "לפת",           "unit_he_plural": "לפתות",          "grams_per_unit": 120, "category": "countable"},

    # ── Fruits ──────────────────────────────────────────────────────────────
    "banana":         {"unit_he": "בננה",          "unit_he_plural": "בננות",          "grams_per_unit": 120, "category": "countable"},
    "apple":          {"unit_he": "תפוח",          "unit_he_plural": "תפוחים",         "grams_per_unit": 180, "category": "countable"},
    "orange":         {"unit_he": "תפוז",          "unit_he_plural": "תפוזים",         "grams_per_unit": 130, "category": "countable"},
    "lemon":          {"unit_he": "לימון",         "unit_he_plural": "לימונים",        "grams_per_unit": 60,  "category": "countable"},
    "avocado":        {"unit_he": "אבוקדו",        "unit_he_plural": "אבוקדו",         "grams_per_unit": 150, "category": "countable"},
    "dates":          {"unit_he": "תמרה",          "unit_he_plural": "תמרים",          "grams_per_unit": 8,   "category": "countable"},
    "date":           {"unit_he": "תמרה",          "unit_he_plural": "תמרים",          "grams_per_unit": 8,   "category": "countable"},
    "strawberry":     {"unit_he": "תות",           "unit_he_plural": "תותים",          "grams_per_unit": 12,  "category": "countable"},
    "mango":          {"unit_he": "מנגו",          "unit_he_plural": "מנגו",           "grams_per_unit": 200, "category": "countable"},
    "watermelon":     {"unit_he": "פרוסת אבטיח",   "unit_he_plural": "פרוסות אבטיח",   "grams_per_unit": 280, "category": "countable"},
    "grapes":         {"unit_he": "כוס ענבים",     "unit_he_plural": "כוסות ענבים",    "grams_per_unit": 150, "category": "cup"},
    "melon":          {"unit_he": "פרוסת מלון",    "unit_he_plural": "פרוסות מלון",    "grams_per_unit": 200, "category": "countable"},
    "peach":          {"unit_he": "אפרסק",         "unit_he_plural": "אפרסקים",        "grams_per_unit": 150, "category": "countable"},
    "plum":           {"unit_he": "שזיף",          "unit_he_plural": "שזיפים",         "grams_per_unit": 70,  "category": "countable"},
    "pear":           {"unit_he": "אגס",           "unit_he_plural": "אגסים",          "grams_per_unit": 170, "category": "countable"},
    "pomegranate":    {"unit_he": "רימון",         "unit_he_plural": "רימונים",        "grams_per_unit": 180, "category": "countable"},
    "fig":            {"unit_he": "תאנה",          "unit_he_plural": "תאנים",          "grams_per_unit": 50,  "category": "countable"},
    "clementine":     {"unit_he": "קלמנטינה",      "unit_he_plural": "קלמנטינות",      "grams_per_unit": 75,  "category": "countable"},
    "grapefruit":     {"unit_he": "אשכולית",       "unit_he_plural": "אשכוליות",       "grams_per_unit": 230, "category": "countable"},
    "kiwi":           {"unit_he": "קיווי",         "unit_he_plural": "קיוויים",        "grams_per_unit": 75,  "category": "countable"},
    "dried cranberries": {"unit_he": "כף חמוציות", "unit_he_plural": "כפות חמוציות",   "grams_per_unit": 10,  "category": "spoon"},
    "raisins":        {"unit_he": "כף צימוקים",    "unit_he_plural": "כפות צימוקים",   "grams_per_unit": 10,  "category": "spoon"},

    # ── Proteins ────────────────────────────────────────────────────────────
    "chicken breast":  {"unit_he": "חזה עוף",       "unit_he_plural": "חזות עוף",       "grams_per_unit": 200, "category": "countable"},
    "chicken thigh":   {"unit_he": "ירך עוף",       "unit_he_plural": "ירכי עוף",       "grams_per_unit": 130, "category": "countable"},
    "chicken wing":    {"unit_he": "כנף עוף",       "unit_he_plural": "כנפי עוף",       "grams_per_unit": 80,  "category": "countable"},
    "chicken drumstick":{"unit_he": "שוק עוף",      "unit_he_plural": "שוקי עוף",       "grams_per_unit": 110, "category": "countable"},
    "ground beef":     {"unit_he": "כף בשר טחון",   "unit_he_plural": "כפות בשר טחון",  "grams_per_unit": 15,  "category": "spoon"},
    "ground turkey":   {"unit_he": "כף הודו טחון",  "unit_he_plural": "כפות הודו טחון", "grams_per_unit": 15,  "category": "spoon"},
    "turkey":          {"unit_he": "פרוסת הודו",    "unit_he_plural": "פרוסות הודו",    "grams_per_unit": 30,  "category": "countable"},
    "turkey breast":   {"unit_he": "חזה הודו",      "unit_he_plural": "חזות הודו",      "grams_per_unit": 200, "category": "countable"},
    "salmon":          {"unit_he": "פילה סלמון",    "unit_he_plural": "פילה סלמון",     "grams_per_unit": 170, "category": "countable"},
    "tuna":            {"unit_he": "פחית טונה",     "unit_he_plural": "פחיות טונה",     "grams_per_unit": 100, "category": "countable"},
    "tuna steak":      {"unit_he": "סטייק טונה",    "unit_he_plural": "סטייקי טונה",    "grams_per_unit": 170, "category": "countable"},
    "tofu":            {"unit_he": "קוביית טופו",   "unit_he_plural": "קוביות טופו",    "grams_per_unit": 100, "category": "countable"},
    "fish fillet":     {"unit_he": "פילה דג",       "unit_he_plural": "פילה דגים",      "grams_per_unit": 170, "category": "countable"},
    "tilapia":         {"unit_he": "פילה טילאפיה",  "unit_he_plural": "פילה טילאפיה",   "grams_per_unit": 170, "category": "countable"},
    "sea bass":        {"unit_he": "פילה דניס",     "unit_he_plural": "פילה דניס",      "grams_per_unit": 170, "category": "countable"},
    "shrimp":          {"unit_he": "שרימפס",        "unit_he_plural": "שרימפסים",       "grams_per_unit": 10,  "category": "countable"},
    "beef steak":      {"unit_he": "סטייק בקר",     "unit_he_plural": "סטייקי בקר",     "grams_per_unit": 200, "category": "countable"},
    "schnitzel":       {"unit_he": "שניצל",         "unit_he_plural": "שניצלים",        "grams_per_unit": 150, "category": "countable"},

    # ── Grains & breads ─────────────────────────────────────────────────────
    "bread":           {"unit_he": "פרוסת לחם",     "unit_he_plural": "פרוסות לחם",     "grams_per_unit": 30,  "category": "countable"},
    "whole wheat bread":{"unit_he": "פרוסת לחם מלא","unit_he_plural": "פרוסות לחם מלא", "grams_per_unit": 30,  "category": "countable"},
    "pita":            {"unit_he": "פיתה",          "unit_he_plural": "פיתות",          "grams_per_unit": 60,  "category": "countable"},
    "rice":            {"unit_he": "כוס אורז",      "unit_he_plural": "כוסות אורז",     "grams_per_unit": 185, "category": "cup"},
    "pasta":           {"unit_he": "כוס פסטה",      "unit_he_plural": "כוסות פסטה",     "grams_per_unit": 140, "category": "cup"},
    "couscous":        {"unit_he": "כוס קוסקוס",    "unit_he_plural": "כוסות קוסקוס",   "grams_per_unit": 160, "category": "cup"},
    "bulgur":          {"unit_he": "כוס בורגול",    "unit_he_plural": "כוסות בורגול",   "grams_per_unit": 140, "category": "cup"},
    "quinoa":          {"unit_he": "כוס קינואה",    "unit_he_plural": "כוסות קינואה",   "grams_per_unit": 170, "category": "cup"},
    "oats":            {"unit_he": "כוס שיבולת שועל","unit_he_plural": "כוסות שיבולת שועל","grams_per_unit": 80, "category": "cup"},
    "tortilla":        {"unit_he": "טורטייה",       "unit_he_plural": "טורטיות",        "grams_per_unit": 45,  "category": "countable"},
    "challah":         {"unit_he": "פרוסת חלה",     "unit_he_plural": "פרוסות חלה",     "grams_per_unit": 40,  "category": "countable"},
    "flour":           {"unit_he": "כוס קמח",       "unit_he_plural": "כוסות קמח",      "grams_per_unit": 120, "category": "cup"},
    "breadcrumbs":     {"unit_he": "כף פירורי לחם", "unit_he_plural": "כפות פירורי לחם","grams_per_unit": 7,   "category": "spoon"},
    "granola":         {"unit_he": "כוס גרנולה",    "unit_he_plural": "כוסות גרנולה",   "grams_per_unit": 120, "category": "cup"},
    "cornflakes":      {"unit_he": "כוס קורנפלקס",  "unit_he_plural": "כוסות קורנפלקס", "grams_per_unit": 30,  "category": "cup"},
    "crackers":        {"unit_he": "קרקר",          "unit_he_plural": "קרקרים",         "grams_per_unit": 7,   "category": "countable"},
    "rice cakes":      {"unit_he": "פריכיית אורז",  "unit_he_plural": "פריכיות אורז",   "grams_per_unit": 9,   "category": "countable"},
    "noodles":         {"unit_he": "כוס אטריות",    "unit_he_plural": "כוסות אטריות",   "grams_per_unit": 140, "category": "cup"},
    "laffa":           {"unit_he": "לאפה",          "unit_he_plural": "לאפות",          "grams_per_unit": 100, "category": "countable"},

    # ── Liquids & oils ──────────────────────────────────────────────────────
    "olive oil":       {"unit_he": "כף שמן זית",    "unit_he_plural": "כפות שמן זית",   "grams_per_unit": 10,  "category": "oil"},
    "oil":             {"unit_he": "כף שמן",        "unit_he_plural": "כפות שמן",       "grams_per_unit": 10,  "category": "oil"},
    "canola oil":      {"unit_he": "כף שמן קנולה",  "unit_he_plural": "כפות שמן קנולה", "grams_per_unit": 10,  "category": "oil"},
    "coconut oil":     {"unit_he": "כף שמן קוקוס",  "unit_he_plural": "כפות שמן קוקוס", "grams_per_unit": 10,  "category": "oil"},
    "sesame oil":      {"unit_he": "כפית שמן שומשום","unit_he_plural":"כפיות שמן שומשום","grams_per_unit": 5,   "category": "oil"},
    "tahini":          {"unit_he": "כף טחינה",      "unit_he_plural": "כפות טחינה",     "grams_per_unit": 15,  "category": "spoon"},
    "honey":           {"unit_he": "כף דבש",        "unit_he_plural": "כפות דבש",       "grams_per_unit": 21,  "category": "spoon"},
    "maple syrup":     {"unit_he": "כף מייפל",      "unit_he_plural": "כפות מייפל",     "grams_per_unit": 20,  "category": "spoon"},
    "soy sauce":       {"unit_he": "כף רוטב סויה",  "unit_he_plural": "כפות רוטב סויה", "grams_per_unit": 16,  "category": "spoon"},
    "vinegar":         {"unit_he": "כף חומץ",       "unit_he_plural": "כפות חומץ",      "grams_per_unit": 15,  "category": "spoon"},
    "lemon juice":     {"unit_he": "כף מיץ לימון",  "unit_he_plural": "כפות מיץ לימון", "grams_per_unit": 15,  "category": "spoon"},
    "water":           {"unit_he": "כוס מים",       "unit_he_plural": "כוסות מים",      "grams_per_unit": 240, "category": "liquid"},
    "tomato paste":    {"unit_he": "כף רסק עגבניות","unit_he_plural": "כפות רסק עגבניות","grams_per_unit": 16, "category": "spoon"},
    "tomato sauce":    {"unit_he": "כוס רוטב עגבניות","unit_he_plural":"כוסות רוטב עגבניות","grams_per_unit":240,"category": "liquid"},
    "ketchup":         {"unit_he": "כף קטשופ",      "unit_he_plural": "כפות קטשופ",     "grams_per_unit": 17,  "category": "spoon"},
    "mustard":         {"unit_he": "כפית חרדל",     "unit_he_plural": "כפיות חרדל",     "grams_per_unit": 5,   "category": "spoon"},
    "mayonnaise":      {"unit_he": "כף מיונז",      "unit_he_plural": "כפות מיונז",     "grams_per_unit": 14,  "category": "spoon"},
    "balsamic vinegar":{"unit_he": "כף חומץ בלסמי", "unit_he_plural": "כפות חומץ בלסמי","grams_per_unit": 16,  "category": "spoon"},
    "coconut milk":    {"unit_he": "כוס חלב קוקוס", "unit_he_plural": "כוסות חלב קוקוס","grams_per_unit": 240, "category": "liquid"},
    "orange juice":    {"unit_he": "כוס מיץ תפוזים","unit_he_plural": "כוסות מיץ תפוזים","grams_per_unit":240, "category": "liquid"},
    "stock":           {"unit_he": "כוס מרק",       "unit_he_plural": "כוסות מרק",      "grams_per_unit": 240, "category": "liquid"},
    "chicken stock":   {"unit_he": "כוס ציר עוף",   "unit_he_plural": "כוסות ציר עוף",  "grams_per_unit": 240, "category": "liquid"},
    "vegetable stock": {"unit_he": "כוס ציר ירקות", "unit_he_plural": "כוסות ציר ירקות","grams_per_unit": 240, "category": "liquid"},

    # ── Legumes ─────────────────────────────────────────────────────────────
    "chickpeas":       {"unit_he": "כוס חומוס",     "unit_he_plural": "כוסות חומוס",    "grams_per_unit": 160, "category": "cup"},
    "lentils":         {"unit_he": "כוס עדשים",     "unit_he_plural": "כוסות עדשים",    "grams_per_unit": 190, "category": "cup"},
    "beans":           {"unit_he": "כוס שעועית",    "unit_he_plural": "כוסות שעועית",   "grams_per_unit": 170, "category": "cup"},
    "black beans":     {"unit_he": "כוס שעועית שחורה","unit_he_plural":"כוסות שעועית שחורה","grams_per_unit":170,"category": "cup"},
    "white beans":     {"unit_he": "כוס שעועית לבנה","unit_he_plural":"כוסות שעועית לבנה","grams_per_unit":170, "category": "cup"},
    "hummus":          {"unit_he": "כף חומוס",      "unit_he_plural": "כפות חומוס",     "grams_per_unit": 15,  "category": "spoon"},
    "edamame":         {"unit_he": "כוס אדממה",     "unit_he_plural": "כוסות אדממה",    "grams_per_unit": 155, "category": "cup"},

    # ── Nuts & seeds ────────────────────────────────────────────────────────
    "almonds":         {"unit_he": "כף שקדים",      "unit_he_plural": "כפות שקדים",     "grams_per_unit": 10,  "category": "spoon"},
    "walnuts":         {"unit_he": "כף אגוזי מלך",  "unit_he_plural": "כפות אגוזי מלך", "grams_per_unit": 10,  "category": "spoon"},
    "peanuts":         {"unit_he": "כף בוטנים",     "unit_he_plural": "כפות בוטנים",    "grams_per_unit": 10,  "category": "spoon"},
    "cashews":         {"unit_he": "כף קשיו",       "unit_he_plural": "כפות קשיו",      "grams_per_unit": 10,  "category": "spoon"},
    "pecans":          {"unit_he": "כף פקאן",       "unit_he_plural": "כפות פקאן",      "grams_per_unit": 10,  "category": "spoon"},
    "pine nuts":       {"unit_he": "כף צנוברים",    "unit_he_plural": "כפות צנוברים",   "grams_per_unit": 10,  "category": "spoon"},
    "sunflower seeds": {"unit_he": "כף גרעיני חמנייה","unit_he_plural":"כפות גרעיני חמנייה","grams_per_unit":10,"category": "spoon"},
    "pumpkin seeds":   {"unit_he": "כף גרעיני דלעת","unit_he_plural": "כפות גרעיני דלעת","grams_per_unit": 10, "category": "spoon"},
    "sesame seeds":    {"unit_he": "כפית שומשום",   "unit_he_plural": "כפיות שומשום",   "grams_per_unit": 5,   "category": "spoon"},
    "chia seeds":      {"unit_he": "כפית צ׳יה",     "unit_he_plural": "כפיות צ׳יה",     "grams_per_unit": 5,   "category": "spoon"},
    "flax seeds":      {"unit_he": "כפית זרעי פשתן","unit_he_plural": "כפיות זרעי פשתן","grams_per_unit": 5,   "category": "spoon"},
    "peanut butter":   {"unit_he": "כף חמאת בוטנים","unit_he_plural": "כפות חמאת בוטנים","grams_per_unit": 16, "category": "spoon"},
    "almond butter":   {"unit_he": "כף חמאת שקדים", "unit_he_plural": "כפות חמאת שקדים","grams_per_unit": 16,  "category": "spoon"},
    "halva":           {"unit_he": "פרוסת חלווה",   "unit_he_plural": "פרוסות חלווה",   "grams_per_unit": 30,  "category": "countable"},

    # ── Spices & condiments ─────────────────────────────────────────────────
    "salt":            {"unit_he": "כפית מלח",      "unit_he_plural": "כפיות מלח",      "grams_per_unit": 6,   "category": "spice"},
    "black pepper":    {"unit_he": "כפית פלפל שחור","unit_he_plural": "כפיות פלפל שחור","grams_per_unit": 3,   "category": "spice"},
    "cumin":           {"unit_he": "כפית כמון",     "unit_he_plural": "כפיות כמון",     "grams_per_unit": 3,   "category": "spice"},
    "paprika":         {"unit_he": "כפית פפריקה",   "unit_he_plural": "כפיות פפריקה",   "grams_per_unit": 3,   "category": "spice"},
    "turmeric":        {"unit_he": "כפית כורכום",   "unit_he_plural": "כפיות כורכום",   "grams_per_unit": 3,   "category": "spice"},
    "za'atar":         {"unit_he": "כפית זעתר",     "unit_he_plural": "כפיות זעתר",     "grams_per_unit": 3,   "category": "spice"},
    "zaatar":          {"unit_he": "כפית זעתר",     "unit_he_plural": "כפיות זעתר",     "grams_per_unit": 3,   "category": "spice"},
    "sugar":           {"unit_he": "כפית סוכר",     "unit_he_plural": "כפיות סוכר",     "grams_per_unit": 4,   "category": "spice"},
    "brown sugar":     {"unit_he": "כפית סוכר חום", "unit_he_plural": "כפיות סוכר חום", "grams_per_unit": 4,   "category": "spice"},
    "cinnamon":        {"unit_he": "כפית קינמון",   "unit_he_plural": "כפיות קינמון",   "grams_per_unit": 3,   "category": "spice"},
    "nutmeg":          {"unit_he": "קמצוץ אגוז מוסקט","unit_he_plural":"קמצוצי אגוז מוסקט","grams_per_unit": 1,"category": "spice"},
    "oregano":         {"unit_he": "כפית אורגנו",   "unit_he_plural": "כפיות אורגנו",   "grams_per_unit": 2,   "category": "spice"},
    "thyme":           {"unit_he": "כפית טימין",    "unit_he_plural": "כפיות טימין",    "grams_per_unit": 2,   "category": "spice"},
    "rosemary":        {"unit_he": "כפית רוזמרין",  "unit_he_plural": "כפיות רוזמרין",  "grams_per_unit": 2,   "category": "spice"},
    "chili flakes":    {"unit_he": "כפית צ׳ילי",    "unit_he_plural": "כפיות צ׳ילי",    "grams_per_unit": 2,   "category": "spice"},
    "garlic powder":   {"unit_he": "כפית אבקת שום", "unit_he_plural": "כפיות אבקת שום", "grams_per_unit": 3,   "category": "spice"},
    "onion powder":    {"unit_he": "כפית אבקת בצל", "unit_he_plural": "כפיות אבקת בצל", "grams_per_unit": 3,   "category": "spice"},
    "sumac":           {"unit_he": "כפית סומק",     "unit_he_plural": "כפיות סומק",     "grams_per_unit": 3,   "category": "spice"},
    "baharat":         {"unit_he": "כפית בהרט",     "unit_he_plural": "כפיות בהרט",     "grams_per_unit": 3,   "category": "spice"},
    "hawaij":          {"unit_he": "כפית חוואיג׳",  "unit_he_plural": "כפיות חוואיג׳",  "grams_per_unit": 3,   "category": "spice"},
    "baking powder":   {"unit_he": "כפית אבקת אפייה","unit_he_plural":"כפיות אבקת אפייה","grams_per_unit": 4,  "category": "spice"},
    "baking soda":     {"unit_he": "כפית סודה לשתייה","unit_he_plural":"כפיות סודה לשתייה","grams_per_unit": 5, "category": "spice"},
    "vanilla extract": {"unit_he": "כפית תמצית וניל","unit_he_plural":"כפיות תמצית וניל","grams_per_unit": 5,  "category": "spice"},
    "cocoa powder":    {"unit_he": "כף קקאו",       "unit_he_plural": "כפות קקאו",      "grams_per_unit": 7,   "category": "spoon"},

    # ── Sweets & misc ───────────────────────────────────────────────────────
    "chocolate":       {"unit_he": "קוביית שוקולד", "unit_he_plural": "קוביות שוקולד",  "grams_per_unit": 10,  "category": "countable"},
    "dark chocolate":  {"unit_he": "קוביית שוקולד מריר","unit_he_plural":"קוביות שוקולד מריר","grams_per_unit":10,"category": "countable"},
    "jam":             {"unit_he": "כפית ריבה",     "unit_he_plural": "כפיות ריבה",     "grams_per_unit": 7,   "category": "spoon"},
    "coconut flakes":  {"unit_he": "כף קוקוס מגורד","unit_he_plural": "כפות קוקוס מגורד","grams_per_unit": 7,  "category": "spoon"},
    "protein powder":  {"unit_he": "סקופ אבקת חלבון","unit_he_plural":"סקופים אבקת חלבון","grams_per_unit": 30, "category": "countable"},
    "olives":          {"unit_he": "זית",           "unit_he_plural": "זיתים",          "grams_per_unit": 4,   "category": "countable"},
    "pickles":         {"unit_he": "מלפפון חמוץ",   "unit_he_plural": "מלפפונים חמוצים","grams_per_unit": 35,  "category": "countable"},
    "capers":          {"unit_he": "כפית צלפים",    "unit_he_plural": "כפיות צלפים",    "grams_per_unit": 5,   "category": "spoon"},
    "harissa":         {"unit_he": "כפית חריסה",    "unit_he_plural": "כפיות חריסה",    "grams_per_unit": 5,   "category": "spoon"},
    "silan":           {"unit_he": "כף סילאן",      "unit_he_plural": "כפות סילאן",     "grams_per_unit": 21,  "category": "spoon"},
    "schug":           {"unit_he": "כפית סחוג",     "unit_he_plural": "כפיות סחוג",     "grams_per_unit": 5,   "category": "spoon"},
    "amba":            {"unit_he": "כפית עמבה",     "unit_he_plural": "כפיות עמבה",     "grams_per_unit": 5,   "category": "spoon"},
}


# ── Fraction formatting ─────────────────────────────────────────────────────

# Common fractions mapped to Hebrew display
_FRACTIONS = [
    (0.25,  "רבע"),
    (1/3,   "שליש"),
    (0.5,   "חצי"),
    (2/3,   "שני שליש"),
    (0.75,  "שלושת רבעי"),
]

# Mixed number fractions (whole + fraction)
_MIXED_FRACTIONS = [
    (0.25,  "ורבע"),
    (1/3,   "ושליש"),
    (0.5,   "וחצי"),
    (2/3,   "ושני שליש"),
    (0.75,  "ושלושת רבעי"),
]


def _snap_to_nice(count: float) -> float:
    """Snap count to nearest whole or half (0.5 steps only).

    Examples: 0.3→0.5, 0.8→1, 1.3→1.5, 1.7→2
    Minimum is 0.5.
    """
    if count <= 0:
        return 0.5
    snapped = round(count * 2) / 2
    if snapped == 0:
        snapped = 0.5
    return snapped


def _format_quantity_hebrew(count: float, unit_singular: str, unit_plural: str) -> str:
    """Format a quantity with a human-friendly Hebrew string.

    Always snaps to the nearest ¼/⅓/½/⅔/¾ so the user never sees 0.2 or 0.8.
    """
    count = _snap_to_nice(count)

    if count <= 0:
        return unit_singular

    whole = int(count)
    frac = round(count - whole, 6)

    FRAC_LABELS = {
        0.5: "חצי",
    }
    MIXED_LABELS = {
        0.5: "וחצי",
    }

    if whole == 0:
        return f"חצי {unit_singular}"

    if frac == 0:
        return f"1 {unit_singular}" if whole == 1 else f"{whole} {unit_plural}"

    # whole + half (e.g. "כף וחצי", "2 כפות וחצי")
    if whole == 1:
        return f"{unit_singular} וחצי"
    return f"{whole} {unit_plural} וחצי"


def enrich_recipe_ingredients(recipe: dict) -> dict:
    """Add a `display_he` household-unit string to every ingredient (in-place).

    Idempotent — safe to call repeatedly on the same cached recipe object.
    Returns the recipe for chaining.
    """
    for ing in recipe.get("ingredients", []) or []:
        ing["display_he"] = format_ingredient_display(ing)
    return recipe


def format_ingredient_display(ingredient: dict) -> str:
    """Convert a recipe ingredient from grams to household display string.

    Input example:
        {"food_name": "ביצה", "food_name_en": "egg", "quantity": 200, "unit": "grams"}
    Output:
        "4 ביצים"

    If no conversion is found, falls back to "{quantity}ג {food_name}".
    """
    food_name = ingredient.get("food_name", "")
    food_name_en = (ingredient.get("food_name_en") or "").lower().strip()
    quantity = ingredient.get("quantity", 0)
    unit = (ingredient.get("unit") or "grams").lower().strip()

    # If already not in grams, return as-is
    if unit not in ("grams", "gram", "g", "גרם"):
        return f"{quantity} {unit} {food_name}"

    if not quantity or quantity <= 0:
        return food_name

    # Look up in conversion table. Try exact match first, then fall back to the
    # last word ("white rice" → "rice") and first word ("green pepper" → ...pepper)
    # so common modifiers don't drop us to a grams display.
    entry = HOUSEHOLD_UNITS.get(food_name_en)
    if not entry and " " in food_name_en:
        words = food_name_en.split()
        entry = HOUSEHOLD_UNITS.get(words[-1]) or HOUSEHOLD_UNITS.get(words[0])
    if not entry:
        # Fallback: show grams
        q_display = int(quantity) if quantity == int(quantity) else quantity
        return f"{food_name} ({q_display}ג)"

    grams_per_unit = entry["grams_per_unit"]
    unit_he = entry["unit_he"]
    unit_he_plural = entry["unit_he_plural"]
    category = entry.get("category", "countable")

    # For spices: very small amounts get special treatment
    if category == "spice" and quantity < grams_per_unit * 0.4:
        return f"קמצוץ {food_name}"

    count = quantity / grams_per_unit

    # Countable items (eggs, pitas...) must be WHOLE units — "חצי ביצה" makes no
    # sense. Use NUMBERS to avoid Hebrew gender issues ("1 אבוקדו", not "אבוקדו אחת").
    if category == "countable":
        whole = max(1, round(count))
        return f"1 {unit_he}" if whole == 1 else f"{whole} {unit_he_plural}"

    return _format_quantity_hebrew(count, unit_he, unit_he_plural)
