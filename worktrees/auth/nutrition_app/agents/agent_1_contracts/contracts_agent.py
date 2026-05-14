"""
Agent 1 — Domain & Contracts Owner

Responsibility:
- Define all models, schemas, and contracts
- Maintain ERD
- Ensure consistency between Python models, JSON schemas, workflow contracts, and ERD

This agent owns: contracts/, models/

Forbidden:
- Business logic
- AI
- Performance tuning
- Meal planning
- Inventory logic
"""

import json
import os
from typing import Dict, List


class ContractsAgent:
    """Validates structural consistency across models and schemas."""

    SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contracts", "schemas")

    def load_schema(self, schema_name: str) -> dict:
        path = os.path.join(self.SCHEMA_DIR, schema_name)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_user_profile(self, data: dict) -> List[str]:
        """Validate user profile data against schema. Returns list of errors."""
        errors = []
        required = ["user_id", "name", "gender", "date_of_birth", "height_cm", "weight_kg", "activity_level", "goal"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        if "height_cm" in data and not (50 <= data["height_cm"] <= 300):
            errors.append(f"height_cm out of range: {data['height_cm']}")
        if "weight_kg" in data and not (10 <= data["weight_kg"] <= 500):
            errors.append(f"weight_kg out of range: {data['weight_kg']}")
        return errors

    def validate_food_item(self, data: dict) -> List[str]:
        errors = []
        required = ["food_id", "name_he", "name_en", "category", "nutrition_per_100g"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        if "nutrition_per_100g" in data:
            n = data["nutrition_per_100g"]
            for key in ["calories_kcal", "protein_g", "carbs_g", "fat_g"]:
                if key not in n:
                    errors.append(f"Missing nutrition field: {key}")
                elif n[key] < 0:
                    errors.append(f"Negative nutrition value: {key}={n[key]}")
        return errors

    def validate_nutrition_targets(self, data: dict) -> List[str]:
        errors = []
        required = ["user_id", "bmr_kcal", "tdee_kcal", "target_calories_kcal", "protein_g", "carbs_g", "fat_g"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif isinstance(data[field], (int, float)) and data[field] < 0:
                errors.append(f"Negative value: {field}={data[field]}")
        return errors

    def get_all_schemas(self) -> Dict[str, dict]:
        schemas = {}
        for fname in os.listdir(self.SCHEMA_DIR):
            if fname.endswith(".json"):
                schemas[fname] = self.load_schema(fname)
        return schemas
