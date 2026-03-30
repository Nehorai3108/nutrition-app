"""
FoodDatabase — Agent 3 (Food Database)
=======================================
OWNED BY: Agent 3
SCOPE: Food item storage, multilingual search, text→food_id matching.

Responsibilities:
- Canonical food dataset with nutritional data (per 100g)
- Hebrew + English name support via name_translations
- Aliases and synonyms for robust text matching
- Text normalization + matching engine (input: free text → output: food_id)

Out of scope (do NOT add here):
- Macro / calorie calculations       → Agent 2 (Nutrition Engine)
- Meal planning or food selection    → Agent 5 (Meal Planning Engine)
- Inventory management               → Agent 4 (Inventory Manager)
- Any AI-based logic                 → Agent 6 (AI Layer)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional
from uuid import UUID, uuid5

from app.models.food_item import FoodItem, FoodCategory


# ── Stable UUID namespace for all canonical food items ────────────────────────
# Fixed namespace — do NOT change. Guarantees IDs remain stable across restarts.
_FOOD_NS = UUID("a1b2c3d4-f000-4000-9000-000000000000")


def _food_uuid(canonical_name: str) -> UUID:
    """Deterministic UUID from a food's canonical English name. Immutable."""
    return uuid5(_FOOD_NS, f"food:{canonical_name.lower()}")


# ── Internal entry ────────────────────────────────────────────────────────────

class _FoodEntry:
    """
    Internal record bundling a FoodItem with its search metadata.
    Not exposed publicly — consumers receive FoodItem or dict.
    """
    __slots__ = ("item", "aliases", "translations")

    def __init__(
        self,
        item: FoodItem,
        aliases: List[str],
        translations: Dict[str, str],
    ) -> None:
        self.item = item
        self.aliases = aliases            # extra search terms (EN + HE variations)
        self.translations = translations  # BCP-47 lang code → display name


# ── Text normalizer ───────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """
    Normalize free text for matching:
    - Unicode NFC
    - Lowercase
    - Strip leading/trailing whitespace
    - Remove punctuation (keep Unicode letters, digits, whitespace)
    - Collapse internal whitespace
    """
    text = unicodedata.normalize("NFC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Food Database ─────────────────────────────────────────────────────────────

class FoodDatabase:
    """
    Central food item registry for Agent 3.

    Public interface
    ────────────────
    match(text)          → Optional[UUID]      free text → best food_id
    search(text)         → List[FoodItem]      partial match, all results
    get_by_id(id)        → Optional[FoodItem]  fetch by UUID
    get_all()            → List[FoodItem]      all items
    to_dict_full(id)     → Optional[dict]      schema-compliant dict
                                               (includes name_translations
                                               and aliases per food_item.json)
    """

    def __init__(self) -> None:
        self._entries: Dict[UUID, _FoodEntry] = {}
        # Inverted index: normalized_term → food_id
        self._index: Dict[str, UUID] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────────

    def match(self, text: str) -> Optional[UUID]:
        """
        Map free text to a food_id using a three-stage lookup:
          1. Exact normalized match
          2. Prefix match (query is prefix of term OR term is prefix of query)
          3. Substring containment

        Returns the best food_id, or None if no match found.

        Examples:
            "עוף"           → Chicken Breast UUID
            "chicken"       → Chicken Breast UUID
            "rice"          → White Rice UUID
            "אורז מלא"      → Brown Rice UUID
        """
        norm = _normalize(text)
        if not norm:
            return None

        # Stage 1 — exact
        if norm in self._index:
            return self._index[norm]

        # Stage 2 — prefix (prefer term closest in length to query)
        prefix_hits = [
            (term, fid)
            for term, fid in self._index.items()
            if term.startswith(norm) or norm.startswith(term)
        ]
        if prefix_hits:
            prefix_hits.sort(key=lambda x: abs(len(x[0]) - len(norm)))
            return prefix_hits[0][1]

        # Stage 3 — substring containment
        sub_hits = [
            (term, fid)
            for term, fid in self._index.items()
            if norm in term or term in norm
        ]
        if sub_hits:
            sub_hits.sort(key=lambda x: abs(len(x[0]) - len(norm)))
            return sub_hits[0][1]

        return None

    def search(self, text: str) -> List[FoodItem]:
        """
        Return all food items whose index terms contain the query as a substring.
        Useful for autocomplete / listing suggestions.
        """
        norm = _normalize(text)
        if not norm:
            return []
        seen: set = set()
        results: List[FoodItem] = []
        for term, fid in self._index.items():
            if norm in term and fid not in seen:
                seen.add(fid)
                results.append(self._entries[fid].item)
        return results

    def get_by_id(self, food_id: UUID) -> Optional[FoodItem]:
        """Return FoodItem for the given UUID, or None if not found."""
        entry = self._entries.get(food_id)
        return entry.item if entry else None

    def get_all(self) -> List[FoodItem]:
        """Return all food items in the database."""
        return [e.item for e in self._entries.values()]

    def to_dict_full(self, food_id: UUID) -> Optional[dict]:
        """
        Return a schema-compliant dict (per contracts/schemas/food_item.json)
        including the name_translations and aliases fields that the FoodItem
        dataclass does not natively carry.
        """
        entry = self._entries.get(food_id)
        if not entry:
            return None
        d = entry.item.to_dict()
        d["name_translations"] = entry.translations if entry.translations else None
        d["aliases"] = entry.aliases
        return d

    # ── Internal helpers ──────────────────────────────────────────────────

    def _register(self, entry: _FoodEntry) -> None:
        """Insert an entry and index all its searchable terms."""
        fid = entry.item.id
        self._entries[fid] = entry

        terms: List[str] = [entry.item.name]
        terms.extend(entry.aliases)
        terms.extend(entry.translations.values())

        for term in terms:
            norm = _normalize(term)
            if norm and norm not in self._index:
                self._index[norm] = fid

    def _make(
        self,
        name: str,
        cal: float,
        prot: float,
        carbs: float,
        fat: float,
        category: FoodCategory,
        fiber: Optional[float] = None,
        serving: Optional[float] = None,
        aliases: Optional[List[str]] = None,
        he: Optional[str] = None,
    ) -> _FoodEntry:
        """Build a _FoodEntry from flat parameters."""
        item = FoodItem(
            id=_food_uuid(name),
            name=name,
            calories_per_100g=cal,
            protein_per_100g=prot,
            carbs_per_100g=carbs,
            fat_per_100g=fat,
            category=category,
            fiber_per_100g=fiber,
            default_serving_g=serving,
            is_custom=False,
        )
        translations: Dict[str, str] = {}
        if he:
            translations["he"] = he
        return _FoodEntry(
            item=item,
            aliases=aliases or [],
            translations=translations,
        )

    # ── Dataset ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        """
        Populate the canonical food dataset.
        All macro values are per 100g (raw/cooked as noted in name).
        Sources: USDA FoodData Central + Israeli nutrition tables.
        """
        P = FoodCategory.PROTEIN
        C = FoodCategory.CARBOHYDRATE
        V = FoodCategory.VEGETABLE
        F = FoodCategory.FRUIT
        D = FoodCategory.DAIRY
        O = FoodCategory.FAT_OIL
        S = FoodCategory.SNACK
        N = FoodCategory.CONDIMENT

        entries = [

            # ── Proteins ─────────────────────────────────────────────────

            self._make("Chicken Breast", 165, 31.0, 0.0, 3.6, P,
                       serving=150, he="חזה עוף",
                       aliases=["chicken", "grilled chicken", "boiled chicken",
                                "chicken fillet", "עוף", "חזה", "חזה עוף"]),

            self._make("Turkey Breast", 157, 29.9, 0.0, 3.2, P,
                       serving=150, he="חזה הודו",
                       aliases=["turkey", "turkey fillet", "הודו", "חזה הודו"]),

            self._make("Ground Beef (lean)", 215, 26.1, 0.0, 12.0, P,
                       serving=150, he="בשר טחון רזה",
                       aliases=["ground beef", "minced beef", "beef",
                                "בשר", "טחון", "בשר טחון"]),

            self._make("Salmon (raw)", 208, 20.4, 0.0, 13.4, P,
                       serving=150, he="סלמון",
                       aliases=["salmon", "salmon fillet", "salmon fish",
                                "דג סלמון", "סלמון"]),

            self._make("Tuna (canned in water)", 116, 25.5, 0.0, 1.0, P,
                       serving=85, he="טונה",
                       aliases=["tuna", "canned tuna", "tuna fish", "טונה"]),

            self._make("Whole Egg", 155, 13.0, 1.1, 11.0, P,
                       serving=55, he="ביצה",
                       aliases=["egg", "eggs", "boiled egg", "fried egg",
                                "scrambled egg", "ביצה", "ביצים"]),

            self._make("Egg White", 52, 10.9, 0.7, 0.2, P,
                       serving=50, he="חלבון ביצה",
                       aliases=["egg whites", "egg white", "חלבון", "חלבון ביצה"]),

            self._make("Lentils (cooked)", 116, 9.0, 20.1, 0.4, P,
                       fiber=7.9, serving=200, he="עדשים",
                       aliases=["lentils", "red lentils", "green lentils",
                                "עדשים", "עדשים אדומות", "עדשים ירוקות"]),

            self._make("Chickpeas (cooked)", 164, 8.9, 27.4, 2.6, P,
                       fiber=7.6, serving=200, he="גרגרי חומוס",
                       aliases=["chickpeas", "garbanzo", "garbanzo beans",
                                "גרגרי חומוס", "חומוס מבושל"]),

            self._make("Tofu (firm)", 144, 17.3, 2.8, 8.7, P,
                       serving=150, he="טופו",
                       aliases=["tofu", "firm tofu", "soy tofu", "טופו"]),

            self._make("Canned Sardines (in oil)", 208, 24.6, 0.0, 11.5, P,
                       serving=85, he="סרדינים בשמן",
                       aliases=["sardines", "sardine", "canned sardines",
                                "סרדינים", "סרדין"]),

            # ── Carbohydrates ─────────────────────────────────────────────

            self._make("White Rice (cooked)", 130, 2.7, 28.2, 0.3, C,
                       serving=200, he="אורז לבן",
                       aliases=["rice", "white rice", "cooked rice",
                                "אורז", "אורז לבן"]),

            self._make("Brown Rice (cooked)", 123, 2.7, 25.6, 1.0, C,
                       fiber=1.8, serving=200, he="אורז מלא",
                       aliases=["brown rice", "whole grain rice",
                                "אורז מלא", "אורז חום"]),

            self._make("Oats (dry)", 389, 16.9, 66.3, 6.9, C,
                       fiber=10.6, serving=80, he="שיבולת שועל",
                       aliases=["oats", "oatmeal", "rolled oats", "porridge",
                                "שיבולת שועל", "שיבולת", "קוואקר"]),

            self._make("Pasta (cooked)", 131, 5.0, 25.0, 1.1, C,
                       serving=200, he="פסטה",
                       aliases=["pasta", "spaghetti", "penne", "macaroni",
                                "noodles", "פסטה"]),

            self._make("Whole Wheat Bread", 247, 13.0, 41.3, 3.4, C,
                       fiber=6.0, serving=40, he="לחם מלא",
                       aliases=["whole wheat bread", "wholemeal", "whole grain bread",
                                "לחם מלא", "לחם"]),

            self._make("White Bread", 265, 9.0, 50.0, 3.2, C,
                       serving=40, he="לחם לבן",
                       aliases=["bread", "white bread", "white loaf",
                                "לחם לבן", "לחם רגיל"]),

            self._make("Sweet Potato (cooked)", 90, 2.0, 20.7, 0.1, C,
                       fiber=3.3, serving=200, he="בטטה",
                       aliases=["sweet potato", "yam", "בטטה"]),

            self._make("Potato (boiled)", 87, 1.9, 20.1, 0.1, C,
                       fiber=1.8, serving=200, he="תפוח אדמה",
                       aliases=["potato", "boiled potato", "mashed potato",
                                "תפוח אדמה", 'תפ"א']),

            self._make("Quinoa (cooked)", 120, 4.4, 21.3, 1.9, C,
                       fiber=2.8, serving=180, he="קינואה",
                       aliases=["quinoa", "קינואה"]),

            self._make("Corn (cooked)", 96, 3.4, 21.3, 1.5, C,
                       fiber=2.4, serving=150, he="תירס",
                       aliases=["corn", "maize", "sweet corn", "corn kernels",
                                "תירס"]),

            self._make("Pita Bread", 275, 9.1, 55.7, 1.2, C,
                       serving=60, he="פיתה",
                       aliases=["pita", "pitta", "pita bread", "פיתה"]),

            # ── Vegetables ───────────────────────────────────────────────

            self._make("Broccoli", 34, 2.8, 6.6, 0.4, V,
                       fiber=2.6, serving=150, he="ברוקולי",
                       aliases=["broccoli", "ברוקולי"]),

            self._make("Spinach", 23, 2.9, 3.6, 0.4, V,
                       fiber=2.2, serving=100, he="תרד",
                       aliases=["spinach", "baby spinach", "תרד"]),

            self._make("Cucumber", 15, 0.7, 3.6, 0.1, V,
                       fiber=0.5, serving=150, he="מלפפון",
                       aliases=["cucumber", "מלפפון"]),

            self._make("Tomato", 18, 0.9, 3.9, 0.2, V,
                       fiber=1.2, serving=120, he="עגבנייה",
                       aliases=["tomato", "tomatoes", "cherry tomato",
                                "עגבנייה", "עגבניות"]),

            self._make("Carrot", 41, 0.9, 9.6, 0.2, V,
                       fiber=2.8, serving=100, he="גזר",
                       aliases=["carrot", "carrots", "גזר"]),

            self._make("Bell Pepper", 31, 1.0, 6.0, 0.3, V,
                       fiber=2.1, serving=120, he="פלפל",
                       aliases=["bell pepper", "pepper", "red pepper",
                                "green pepper", "yellow pepper",
                                "פלפל", "פלפל אדום", "פלפל ירוק", "פלפל צהוב"]),

            self._make("Lettuce", 15, 1.4, 2.9, 0.2, V,
                       fiber=1.3, serving=80, he="חסה",
                       aliases=["lettuce", "romaine", "iceberg lettuce", "חסה"]),

            self._make("Zucchini", 17, 1.2, 3.1, 0.3, V,
                       fiber=1.0, serving=150, he="קישוא",
                       aliases=["zucchini", "courgette", "קישוא"]),

            self._make("Onion", 40, 1.1, 9.3, 0.1, V,
                       fiber=1.7, serving=80, he="בצל",
                       aliases=["onion", "red onion", "white onion",
                                "בצל", "בצל לבן", "בצל סגול"]),

            self._make("Mushrooms", 22, 3.1, 3.3, 0.3, V,
                       fiber=1.0, serving=100, he="פטריות",
                       aliases=["mushroom", "mushrooms", "button mushroom",
                                "פטריות", "פטריה"]),

            self._make("Cauliflower", 25, 1.9, 5.0, 0.3, V,
                       fiber=2.0, serving=150, he="כרובית",
                       aliases=["cauliflower", "כרובית"]),

            self._make("Cabbage", 25, 1.3, 5.8, 0.1, V,
                       fiber=2.5, serving=150, he="כרוב",
                       aliases=["cabbage", "green cabbage", "כרוב"]),

            self._make("Eggplant", 25, 1.0, 5.9, 0.2, V,
                       fiber=3.0, serving=150, he="חציל",
                       aliases=["eggplant", "aubergine", "חציל"]),

            self._make("Garlic", 149, 6.4, 33.1, 0.5, V,
                       fiber=2.1, serving=5, he="שום",
                       aliases=["garlic", "garlic clove", "שום"]),

            # ── Fruits ───────────────────────────────────────────────────

            self._make("Apple", 52, 0.3, 13.8, 0.2, F,
                       fiber=2.4, serving=180, he="תפוח",
                       aliases=["apple", "red apple", "green apple",
                                "תפוח", "תפוח עץ"]),

            self._make("Banana", 89, 1.1, 22.8, 0.3, F,
                       fiber=2.6, serving=120, he="בננה",
                       aliases=["banana", "בננה"]),

            self._make("Orange", 47, 0.9, 11.8, 0.1, F,
                       fiber=2.4, serving=150, he="תפוז",
                       aliases=["orange", "mandarin", "clementine",
                                "תפוז", "מנדרינה"]),

            self._make("Watermelon", 30, 0.6, 7.6, 0.2, F,
                       fiber=0.4, serving=300, he="אבטיח",
                       aliases=["watermelon", "אבטיח"]),

            self._make("Grapes", 69, 0.7, 18.1, 0.2, F,
                       fiber=0.9, serving=150, he="ענבים",
                       aliases=["grapes", "grape", "red grapes",
                                "ענבים", "ענב"]),

            self._make("Strawberry", 32, 0.7, 7.7, 0.3, F,
                       fiber=2.0, serving=150, he="תות שדה",
                       aliases=["strawberry", "strawberries",
                                "תות", "תות שדה"]),

            self._make("Mango", 60, 0.8, 15.0, 0.4, F,
                       fiber=1.6, serving=200, he="מנגו",
                       aliases=["mango", "מנגו"]),

            self._make("Pear", 57, 0.4, 15.2, 0.1, F,
                       fiber=3.1, serving=170, he="אגס",
                       aliases=["pear", "אגס"]),

            # ── Dairy ────────────────────────────────────────────────────

            self._make("Milk (1% fat)", 42, 3.4, 5.0, 1.0, D,
                       serving=250, he="חלב 1%",
                       aliases=["milk", "low fat milk", "1% milk", "חלב"]),

            self._make("Yogurt (plain, 1.5%)", 63, 3.5, 4.7, 1.5, D,
                       serving=200, he="יוגורט",
                       aliases=["yogurt", "plain yogurt", "natural yogurt",
                                "יוגורט", "יוגורט רגיל"]),

            self._make("Greek Yogurt (0%)", 59, 10.2, 3.6, 0.4, D,
                       serving=200, he="יוגורט יווני",
                       aliases=["greek yogurt", "strained yogurt",
                                "יוגורט יווני", "יוגורט 0%"]),

            self._make("Cottage Cheese (5%)", 103, 11.1, 3.0, 5.0, D,
                       serving=200, he="קוטג'",
                       aliases=["cottage cheese", "cottage",
                                "קוטג", "קוטג'"]),

            self._make("Yellow Cheese (28%)", 357, 25.0, 0.5, 28.0, D,
                       serving=30, he="גבינה צהובה",
                       aliases=["yellow cheese", "cheddar", "hard cheese",
                                "גבינה", "גבינה צהובה"]),

            self._make("White Cheese (5%)", 96, 12.0, 3.0, 4.0, D,
                       serving=30, he="גבינה לבנה 5%",
                       aliases=["white cheese", "feta", "bulgarian cheese",
                                "גבינה לבנה", "גבינת פטה", "בולגרית"]),

            self._make("Cream Cheese", 342, 5.9, 4.1, 34.0, D,
                       serving=30, he="גבינת שמנת",
                       aliases=["cream cheese", "philadelphia",
                                "גבינת שמנת", "שמנת גבינה"]),

            # ── Fats & Oils ───────────────────────────────────────────────

            self._make("Olive Oil", 884, 0.0, 0.0, 100.0, O,
                       serving=14, he="שמן זית",
                       aliases=["olive oil", "oil", "שמן זית", "שמן"]),

            self._make("Avocado", 160, 2.0, 9.0, 15.0, O,
                       fiber=6.7, serving=150, he="אבוקדו",
                       aliases=["avocado", "אבוקדו"]),

            self._make("Peanut Butter", 588, 25.1, 20.0, 50.4, O,
                       fiber=6.0, serving=32, he="חמאת בוטנים",
                       aliases=["peanut butter", "pb",
                                "חמאת בוטנים", "בוטנים"]),

            self._make("Butter", 717, 0.9, 0.1, 81.1, O,
                       serving=10, he="חמאה",
                       aliases=["butter", "חמאה"]),

            # ── Snacks ───────────────────────────────────────────────────

            self._make("Almonds", 579, 21.2, 21.6, 49.9, S,
                       fiber=12.5, serving=30, he="שקדים",
                       aliases=["almonds", "almond", "שקדים"]),

            self._make("Walnuts", 654, 15.2, 13.7, 65.2, S,
                       fiber=6.7, serving=30, he="אגוזי מלך",
                       aliases=["walnuts", "walnut",
                                "אגוז", "אגוזים", "אגוזי מלך"]),

            self._make("Sunflower Seeds", 584, 20.8, 20.0, 51.5, S,
                       fiber=8.6, serving=30, he="גרעיני חמניות",
                       aliases=["sunflower seeds", "seeds",
                                "גרעינים", "גרעיני חמניות"]),

            self._make("Rice Cakes (plain)", 387, 8.0, 81.6, 3.5, S,
                       serving=9, he="עוגות אורז",
                       aliases=["rice cake", "rice cakes",
                                "עוגות אורז", "עוגת אורז"]),

            self._make("Dark Chocolate (70%)", 598, 7.8, 45.9, 42.6, S,
                       fiber=10.9, serving=20, he="שוקולד מריר",
                       aliases=["dark chocolate", "chocolate",
                                "שוקולד מריר", "שוקולד"]),

            # ── Condiments ────────────────────────────────────────────────

            self._make("Hummus (spread)", 177, 8.0, 14.3, 9.6, N,
                       fiber=6.0, serving=60, he="חומוס",
                       aliases=["hummus", "houmous", "חומוס"]),

            self._make("Tahini", 595, 17.0, 26.0, 53.0, N,
                       fiber=9.3, serving=20, he="טחינה",
                       aliases=["tahini", "sesame paste", "tahina",
                                "טחינה", "טחינה גולמית"]),

            self._make("Ketchup", 112, 1.3, 27.0, 0.1, N,
                       serving=17, he="קטשופ",
                       aliases=["ketchup", "tomato ketchup", "קטשופ"]),

            self._make("Mayonnaise", 680, 1.0, 0.6, 75.0, N,
                       serving=15, he="מיונז",
                       aliases=["mayo", "mayonnaise", "מיונז"]),

            self._make("Soy Sauce", 53, 8.1, 4.9, 0.6, N,
                       serving=15, he="רוטב סויה",
                       aliases=["soy sauce", "soya sauce",
                                "רוטב סויה", "סויה"]),

        ]

        for entry in entries:
            self._register(entry)


# ── Module-level singleton ────────────────────────────────────────────────────

_db_instance: Optional[FoodDatabase] = None


def get_food_db() -> FoodDatabase:
    """
    Return the module-level FoodDatabase singleton.
    Lazily initialized on first call.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = FoodDatabase()
    return _db_instance
