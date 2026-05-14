"""Hebrew label dictionaries shared across pages.

Pure data — no imports from app code so this can be loaded anywhere.
The keys mirror the enum *values* used by ``nutrition_app.models.enums``
so callers can index by either the enum or its ``.value`` string.
"""

MEAL_LABELS = {
    "breakfast":       "ארוחת בוקר",
    "morning_snack":   "חטיף בוקר",
    "lunch":           "ארוחת צהריים",
    "afternoon_snack": "חטיף אחה\"צ",
    "dinner":          "ארוחת ערב",
    "evening_snack":   "חטיף ערב",
}

# UPPERCASE variants used by recipe filters
MEAL_LABELS_UPPER = {k.upper(): v for k, v in MEAL_LABELS.items()}

# Maps each meal slot to a semantic icon name from ui.icons
MEAL_ICON = {
    "breakfast":       "breakfast",
    "morning_snack":   "snack",
    "lunch":           "lunch",
    "afternoon_snack": "snack",
    "dinner":          "dinner",
    "evening_snack":   "snack",
}

KASHRUT_LABELS = {
    "meat":  "בשרי",
    "dairy": "חלבי",
    "parve": "פרווה",
}

KASHRUT_ICON = {
    "meat":  "protein",
    "dairy": "fat",
    "parve": "carbs",
}

ACTIVITY_LABELS = {
    "sedentary":         "יושבני (כמעט ללא פעילות)",
    "lightly_active":    "פעילות קלה (1-3 ימים/שבוע)",
    "moderately_active": "פעילות בינונית (3-5 ימים/שבוע)",
    "very_active":       "פעילות גבוהה (6-7 ימים/שבוע)",
    "extra_active":      "פעילות אינטנסיבית / עבודה פיזית",
}

GOAL_LABELS = {
    "lose_weight": "ירידה במשקל",
    "maintain":    "שמירה על משקל",
    "gain_weight": "עלייה במשקל",
}

GENDER_LABELS = {
    "male":   "זכר",
    "female": "נקבה",
}

WORKOUT_INTENSITY_LABELS = {
    "low":      "נמוכה (הליכה קלה)",
    "moderate": "בינונית (הליכה מהירה)",
    "high":     "גבוהה (ריצה)",
    "extreme":  "עצימה מאוד (HIIT)",
}
