"""
Enums — Central enum definitions for the entire system.
Owner: Agent 1 (Domain & Contracts)
"""

from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"           # Little or no exercise
    LIGHTLY_ACTIVE = "lightly_active"  # Light exercise 1-3 days/week
    MODERATELY_ACTIVE = "moderately_active"  # Moderate exercise 3-5 days/week
    VERY_ACTIVE = "very_active"        # Hard exercise 6-7 days/week
    EXTRA_ACTIVE = "extra_active"      # Very hard exercise, physical job


class Goal(str, Enum):
    LOSE_WEIGHT = "lose_weight"
    MAINTAIN = "maintain"
    GAIN_WEIGHT = "gain_weight"


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    MORNING_SNACK = "morning_snack"
    LUNCH = "lunch"
    AFTERNOON_SNACK = "afternoon_snack"
    DINNER = "dinner"
    EVENING_SNACK = "evening_snack"


class UnitType(str, Enum):
    GRAM = "gram"
    ML = "ml"
    UNIT = "unit"          # e.g., 1 egg, 1 apple
    TABLESPOON = "tablespoon"
    TEASPOON = "teaspoon"
    CUP = "cup"
    SLICE = "slice"


class FoodCategory(str, Enum):
    PROTEIN = "protein"
    CARBOHYDRATE = "carbohydrate"
    FAT = "fat"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    DAIRY = "dairy"
    GRAIN = "grain"
    LEGUME = "legume"
    NUT_SEED = "nut_seed"
    CONDIMENT = "condiment"
    BEVERAGE = "beverage"
    OTHER = "other"


class ConfidenceLevel(str, Enum):
    HIGH = "high"        # >= 0.85
    MEDIUM = "medium"    # 0.6 - 0.84
    LOW = "low"          # < 0.6


class InventoryAction(str, Enum):
    ADD = "add"
    UPDATE = "update"
    REMOVE = "remove"
    DEDUCT = "deduct"
    RESERVE = "reserve"
    RELEASE = "release"


class WorkflowStage(str, Enum):
    CREATE_USER_PROFILE = "create_user_profile"
    CALCULATE_TARGETS = "calculate_targets"
    RESOLVE_FOODS = "resolve_foods"
    CHECK_INVENTORY = "check_inventory"
    GENERATE_MEAL_PLAN = "generate_meal_plan"
    PRESENT_DECISION = "present_decision"
    CONFIRM = "confirm"
    DEDUCT_INVENTORY = "deduct_inventory"
    PERSIST_RUN_ARTIFACTS = "persist_run_artifacts"
    DIRECTOR_ANALYSIS = "director_analysis"
    CRITIC_REVIEW = "critic_review"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionType(str, Enum):
    FOOD_NOT_RECOGNIZED = "food_not_recognized"
    MISSING_NUTRITION_DATA = "missing_nutrition_data"
    INSUFFICIENT_INVENTORY = "insufficient_inventory"
    TARGET_DEVIATION = "target_deviation"
    OUTPUT_CONFLICT = "output_conflict"
    CONTRACT_VIOLATION = "contract_violation"
    RISKY_WRITE = "risky_write"


class WorkoutIntensity(str, Enum):
    LOW = "low"            # ~3 MET  (easy walk, light yoga)
    MODERATE = "moderate"  # ~5 MET  (brisk walk, easy cycling)
    HIGH = "high"          # ~7.5 MET (running, hard cycling)
    EXTREME = "extreme"    # ~10 MET (HIIT, sprinting)


class WorkoutType(str, Enum):
    # Cardio / endurance
    RUNNING = "running"
    WALKING = "walking"
    HIKING = "hiking"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    ROWING = "rowing"
    ELLIPTICAL = "elliptical"
    STAIR_CLIMBING = "stair_climbing"
    JUMPING_ROPE = "jumping_rope"
    # Strength / studio
    STRENGTH = "strength"
    CROSSFIT = "crossfit"
    HIIT = "hiit"
    PILATES = "pilates"
    YOGA = "yoga"
    DANCE = "dance"
    # Combat sports
    BOXING = "boxing"
    KICKBOXING = "kickboxing"
    MARTIAL_ARTS = "martial_arts"
    WRESTLING = "wrestling"
    # Ball sports
    SOCCER = "soccer"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    TABLE_TENNIS = "table_tennis"
    BADMINTON = "badminton"
    VOLLEYBALL = "volleyball"
    BASEBALL = "baseball"
    HANDBALL = "handball"
    RUGBY = "rugby"
    HOCKEY = "hockey"
    GOLF = "golf"
    # Outdoor / adventure
    CLIMBING = "climbing"
    SKIING = "skiing"
    SNOWBOARDING = "snowboarding"
    SURFING = "surfing"
    SKATING = "skating"
    # Fallback
    OTHER = "other"


class ArtifactType(str, Enum):
    SOURCE = "source"
    DERIVED = "derived"
    CACHE = "cache"
    LOG = "log"
    DEBUG = "debug"
    SNAPSHOT = "snapshot"


class WorkoutIntensity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class WorkoutType(str, Enum):
    # Cardio
    RUNNING = "running"
    WALKING = "walking"
    HIKING = "hiking"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    ROWING = "rowing"
    ELLIPTICAL = "elliptical"
    STAIR_CLIMBING = "stair_climbing"
    JUMPING_ROPE = "jumping_rope"
    # Strength / Functional
    STRENGTH = "strength"
    CROSSFIT = "crossfit"
    HIIT = "hiit"
    PILATES = "pilates"
    YOGA = "yoga"
    DANCE = "dance"
    # Combat
    BOXING = "boxing"
    KICKBOXING = "kickboxing"
    MARTIAL_ARTS = "martial_arts"
    WRESTLING = "wrestling"
    # Team / Ball sports
    SOCCER = "soccer"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    TABLE_TENNIS = "table_tennis"
    BADMINTON = "badminton"
    VOLLEYBALL = "volleyball"
    BASEBALL = "baseball"
    HANDBALL = "handball"
    RUGBY = "rugby"
    HOCKEY = "hockey"
    GOLF = "golf"
    # Outdoor / Adventure
    CLIMBING = "climbing"
    SKIING = "skiing"
    SNOWBOARDING = "snowboarding"
    SURFING = "surfing"
    SKATING = "skating"
    # Other
    OTHER = "other"
