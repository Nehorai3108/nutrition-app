"""
Workflow Definition — Formal definition of the pipeline stages, transitions, and decision gates.
Owner: Agent 1 (Domain & Contracts)
"""

from dataclasses import dataclass, field
from typing import Dict, List
from nutrition_app.models.enums import WorkflowStage, DecisionType


@dataclass
class StageDefinition:
    stage: WorkflowStage
    agent_owner: str
    description: str
    input_contracts: List[str]
    output_contracts: List[str]
    can_retry: bool = True
    max_retries: int = 2
    decision_gates: List[DecisionType] = field(default_factory=list)


# ─── Pipeline Definition ────────────────────────────────────────────

PIPELINE_STAGES: List[StageDefinition] = [
    StageDefinition(
        stage=WorkflowStage.CREATE_USER_PROFILE,
        agent_owner="agent_1_contracts",
        description="Create or load user profile",
        input_contracts=["UserProfile input data"],
        output_contracts=["UserProfile"],
    ),
    StageDefinition(
        stage=WorkflowStage.CALCULATE_TARGETS,
        agent_owner="agent_2_nutrition",
        description="Calculate BMR, TDEE, target calories, and macros",
        input_contracts=["UserProfile"],
        output_contracts=["NutritionTargets"],
    ),
    StageDefinition(
        stage=WorkflowStage.RESOLVE_FOODS,
        agent_owner="agent_3_food",
        description="Match food names to catalog items",
        input_contracts=["List[str] food names"],
        output_contracts=["FoodMatchResult"],
        decision_gates=[
            DecisionType.FOOD_NOT_RECOGNIZED,
            DecisionType.MISSING_NUTRITION_DATA,
        ],
    ),
    StageDefinition(
        stage=WorkflowStage.CHECK_INVENTORY,
        agent_owner="agent_4_inventory",
        description="Check current inventory availability",
        input_contracts=["user_id", "FoodMatchResult"],
        output_contracts=["InventoryState"],
        decision_gates=[
            DecisionType.INSUFFICIENT_INVENTORY,
        ],
    ),
    StageDefinition(
        stage=WorkflowStage.GENERATE_MEAL_PLAN,
        agent_owner="agent_5_planner",
        description="Generate daily meal plan from targets, foods, and inventory",
        input_contracts=["NutritionTargets", "FoodMatchResult", "InventoryState"],
        output_contracts=["MealPlan"],
        decision_gates=[
            DecisionType.TARGET_DEVIATION,
            DecisionType.OUTPUT_CONFLICT,
        ],
    ),
    StageDefinition(
        stage=WorkflowStage.PRESENT_DECISION,
        agent_owner="agent_6_ai",
        description="Present plan to user with AI-generated summary",
        input_contracts=["MealPlan", "NutritionTargets"],
        output_contracts=["str (summary text)"],
    ),
    StageDefinition(
        stage=WorkflowStage.CONFIRM,
        agent_owner="orchestrator",
        description="Await user confirmation of the plan",
        input_contracts=["MealPlan presentation"],
        output_contracts=["confirmation boolean"],
        can_retry=False,
    ),
    StageDefinition(
        stage=WorkflowStage.DEDUCT_INVENTORY,
        agent_owner="agent_4_inventory",
        description="Deduct used inventory items after confirmation",
        input_contracts=["MealPlan (confirmed)", "InventoryState"],
        output_contracts=["InventoryChangeSet"],
        decision_gates=[
            DecisionType.RISKY_WRITE,
        ],
    ),
    StageDefinition(
        stage=WorkflowStage.PERSIST_RUN_ARTIFACTS,
        agent_owner="agent_7_data_performance",
        description="Persist all run artifacts, snapshots, and logs",
        input_contracts=["RunState", "all stage outputs"],
        output_contracts=["persisted artifact records"],
    ),
    StageDefinition(
        stage=WorkflowStage.DIRECTOR_ANALYSIS,
        agent_owner="agent_8_director",
        description="Scan system state, identify gaps, produce prioritized task list",
        input_contracts=["MealPlan", "FoodCatalog state"],
        output_contracts=["DirectorReport", "pending_tasks.json"],
    ),
    StageDefinition(
        stage=WorkflowStage.CRITIC_REVIEW,
        agent_owner="agent_9_critic",
        description="Review completed tasks, approve or reject, re-queue failures",
        input_contracts=["completed_tasks.json", "MealPlan", "FoodCatalog state"],
        output_contracts=["verdicts.json"],
    ),
]

STAGE_ORDER = [s.stage for s in PIPELINE_STAGES]

STAGE_MAP: Dict[WorkflowStage, StageDefinition] = {s.stage: s for s in PIPELINE_STAGES}
