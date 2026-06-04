#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build data/recipe_images.json with maximum variety.
For each recipe:
  1. TheMealDB exact search (full name)
  2. TheMealDB first-two-words search
  3. TheMealDB single best keyword
  4. Curated manual override for common Israeli dishes
  5. Category fallback from a LARGE pool of verified images
"""

import json, os, time, urllib.request, urllib.parse, random

BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(BASE, "storage_agents", "recipes", "recipes.json")
OUT     = os.path.join(BASE, "data", "recipe_images.json")


# ── TheMealDB search ──────────────────────────────────────────────────────────
def mealdb(q: str) -> str:
    if not q or len(q) < 2:
        return ""
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={urllib.parse.quote(q)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            meals = json.loads(r.read()).get("meals") or []
        return meals[0]["strMealThumb"] if meals else ""
    except Exception:
        return ""


# ── Large pool of verified TheMealDB images per category ─────────────────────
# We verified these by fetching TheMealDB filter.php?c=Category and getting
# multiple meals per category.  Each key maps to a LIST so we can vary within
# the same category and avoid seeing the same photo on every card.

POOL = {
    "shakshuka": [
        "https://www.themealdb.com/images/media/meals/g373701551450225.jpg",
    ],
    "schnitzel": [
        "https://www.themealdb.com/images/media/meals/1529444830.jpg",
    ],
    "chicken_grill": [
        "https://www.themealdb.com/images/media/meals/xcsqtp1487349408.jpg",
        "https://www.themealdb.com/images/media/meals/sstssx1468261714.jpg",
        "https://www.themealdb.com/images/media/meals/tyywsw1665661330.jpg",
    ],
    "chicken_rice": [
        "https://www.themealdb.com/images/media/meals/vdwloy1713225718.jpg",
        "https://www.themealdb.com/images/media/meals/vwrpps1503068729.jpg",
    ],
    "chicken_soup": [
        "https://www.themealdb.com/images/media/meals/bzxle11700785391.jpg",
    ],
    "beef_steak": [
        "https://www.themealdb.com/images/media/meals/8rfd4q1764112993.jpg",
        "https://www.themealdb.com/images/media/meals/sytuqu1511553755.jpg",
    ],
    "beef_stew": [
        "https://www.themealdb.com/images/media/meals/vrspxv1511722107.jpg",
        "https://www.themealdb.com/images/media/meals/uuuspp1511297945.jpg",
    ],
    "meatballs": [
        "https://www.themealdb.com/images/media/meals/xxrxux1503070723.jpg",
        "https://www.themealdb.com/images/media/meals/sywwex1511564244.jpg",
    ],
    "burger": [
        "https://www.themealdb.com/images/media/meals/urzj1d1587670726.jpg",
    ],
    "kebab": [
        "https://www.themealdb.com/images/media/meals/k420tj1585565244.jpg",
    ],
    "lamb": [
        "https://www.themealdb.com/images/media/meals/04axct1763793018.jpg",
    ],
    "salmon": [
        "https://www.themealdb.com/images/media/meals/1548772327.jpg",
        "https://www.themealdb.com/images/media/meals/c18desc1556736532.jpg",
    ],
    "fish_baked": [
        "https://www.themealdb.com/images/media/meals/jc6oub1763196663.jpg",
        "https://www.themealdb.com/images/media/meals/xxyupu1511296417.jpg",
    ],
    "tuna": [
        "https://www.themealdb.com/images/media/meals/1520081754.jpg",
    ],
    "omelette": [
        "https://www.themealdb.com/images/media/meals/wyxwsp1486979827.jpg",
        "https://www.themealdb.com/images/media/meals/utxqpt1511604047.jpg",
    ],
    "egg_dish": [
        "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    ],
    "pasta": [
        "https://www.themealdb.com/images/media/meals/usywpp1511189717.jpg",
        "https://www.themealdb.com/images/media/meals/llcbn01574260722.jpg",
        "https://www.themealdb.com/images/media/meals/wvqpwt1468339226.jpg",
        "https://www.themealdb.com/images/media/meals/ustsqw1468250014.jpg",
    ],
    "pizza": [
        "https://www.themealdb.com/images/media/meals/x0lk931587671540.jpg",
    ],
    "rice": [
        "https://www.themealdb.com/images/media/meals/vdwloy1713225718.jpg",
    ],
    "couscous": [
        "https://www.themealdb.com/images/media/meals/yqwtvu1468237251.jpg",
    ],
    "quinoa": [
        "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
    ],
    "bulgur_grain": [
        "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
        "https://www.themealdb.com/images/media/meals/txsupu1511453189.jpg",
    ],
    "lentil": [
        "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
        "https://www.themealdb.com/images/media/meals/rqtxvr1511722993.jpg",
    ],
    "hummus": [
        "https://www.themealdb.com/images/media/meals/ls9lfh1728736328.jpg",
    ],
    "bean_stew": [
        "https://www.themealdb.com/images/media/meals/uwxqwy1483389553.jpg",
        "https://www.themealdb.com/images/media/meals/rqtxvr1511722993.jpg",
    ],
    "salad_green": [
        "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
        "https://www.themealdb.com/images/media/meals/n3xxd91598732796.jpg",
    ],
    "salad_grain": [
        "https://www.themealdb.com/images/media/meals/xqusqy1511638311.jpg",
        "https://www.themealdb.com/images/media/meals/txsupu1511453189.jpg",
    ],
    "salad_greek": [
        "https://www.themealdb.com/images/media/meals/v8q61i1511948235.jpg",
    ],
    "soup": [
        "https://www.themealdb.com/images/media/meals/bzxle11700785391.jpg",
        "https://www.themealdb.com/images/media/meals/rqtxvr1511722993.jpg",
        "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    ],
    "veggie_roast": [
        "https://www.themealdb.com/images/media/meals/3m8yae1763257951.jpg",
        "https://www.themealdb.com/images/media/meals/ipmstu1568909735.jpg",
    ],
    "stuffed_veg": [
        "https://www.themealdb.com/images/media/meals/xxrxux1503070723.jpg",
        "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    ],
    "dairy_bowl": [
        "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    ],
    "yogurt_bowl": [
        "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    ],
    "wrap_pita": [
        "https://www.themealdb.com/images/media/meals/k420tj1585565244.jpg",
    ],
    "bread_toast": [
        "https://www.themealdb.com/images/media/meals/vxuyrx1511302687.jpg",
        "https://www.themealdb.com/images/media/meals/sywwex1511564244.jpg",
    ],
    "pancakes": [
        "https://www.themealdb.com/images/media/meals/rwuyqx1511383174.jpg",
    ],
    "granola_oat": [
        "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    ],
    "smoothie": [
        "https://www.themealdb.com/images/media/meals/jvjnoh1780086318.jpg",
    ],
    "dessert": [
        "https://www.themealdb.com/images/media/meals/wkhg581762773124.jpg",
        "https://www.themealdb.com/images/media/meals/rysee11511388853.jpg",
        "https://www.themealdb.com/images/media/meals/1548772327.jpg",
    ],
    "snack": [
        "https://www.themealdb.com/images/media/meals/vxuyrx1511302687.jpg",
    ],
}

# Pool iterators (round-robin so same category → different images)
_pool_idx: dict[str, int] = {}

def from_pool(cat: str) -> str:
    imgs = POOL.get(cat, POOL["snack"])
    idx  = _pool_idx.get(cat, 0) % len(imgs)
    _pool_idx[cat] = idx + 1
    return imgs[idx]


# ── Manual overrides: recipe_id → exact URL ───────────────────────────────────
# For Israeli dishes TheMealDB doesn't know at all, we pick the visually
# closest TheMealDB meal image manually.
MANUAL: dict[str, str] = {
    # Sabich / Israeli street food → wrap/pita image
    "recipe_007": from_pool("wrap_pita"),
    "recipe_243": from_pool("wrap_pita"),
    # Labaneh plate → dairy bowl
    "recipe_005": from_pool("dairy_bowl"),
    "recipe_202": from_pool("dairy_bowl"),
    "recipe_229": from_pool("dairy_bowl"),
    "recipe_234": from_pool("dairy_bowl"),
    "recipe_240": from_pool("dairy_bowl"),
    # Cottage cheese dishes → dairy bowl (NOT the vegetarian stir-fry image)
    "recipe_028": from_pool("dairy_bowl"),
    "recipe_197": from_pool("dairy_bowl"),
    # Warm hummus → hummus
    "recipe_155": from_pool("hummus"),
    "recipe_200": from_pool("hummus"),
    # Kubbeh / kubeh → meatballs/stuffed
    "recipe_062": from_pool("meatballs"),
    "recipe_233": from_pool("meatballs"),
    # Sausages → meatballs/beef
    "recipe_170": from_pool("beef_stew"),
    # Moussaka → beef stew/veggie roast
    "recipe_094": from_pool("veggie_roast"),
    "recipe_117": from_pool("veggie_roast"),
    # Eggplant moussaka
    "recipe_163": from_pool("veggie_roast"),
    # Baba ganoush / eggplant salad → veggie
    "recipe_077": from_pool("veggie_roast"),
    "recipe_061": from_pool("salad_green"),
    # Ptitim (Israeli couscous) → couscous/rice
    "recipe_040": from_pool("couscous"),
    # Malawach / Jachnun / Lahoh → pancakes (flatbread)
    "recipe_059": from_pool("pancakes"),
    "recipe_060": from_pool("pancakes"),
    "recipe_081": from_pool("pancakes"),
    "recipe_249": from_pool("pancakes"),
    # Israeli breakfast plate → egg dish
    "recipe_114": from_pool("egg_dish"),
    # Cheese omelette / frittata
    "recipe_025": from_pool("omelette"),
    "recipe_075": from_pool("omelette"),
    "recipe_091": from_pool("omelette"),
    "recipe_115": from_pool("omelette"),
    # Pashitda → omelette-like
    # Avocado toast → bread/toast
    "recipe_035": from_pool("bread_toast"),
    "recipe_053": from_pool("bread_toast"),
    "recipe_113": from_pool("bread_toast"),
    "recipe_224": from_pool("bread_toast"),
    # Bourekas → bread/toast
    "recipe_063": from_pool("bread_toast"),
    "recipe_107": from_pool("bread_toast"),
    # Challah → bread
    "recipe_108": from_pool("bread_toast"),
    # Almond Croissant → bread
    "recipe_109": from_pool("bread_toast"),
    # Bruschetta → bread
    "recipe_179": from_pool("bread_toast"),
    # Protein smoothie / shakes → smoothie
    "recipe_095": from_pool("smoothie"),
    "recipe_110": from_pool("smoothie"),
    "recipe_111": from_pool("smoothie"),
    "recipe_182": from_pool("smoothie"),
    "recipe_183": from_pool("smoothie"),
    "recipe_196": from_pool("smoothie"),
    "recipe_215": from_pool("smoothie"),
    "recipe_253": from_pool("smoothie"),
    "recipe_260": from_pool("smoothie"),
    "recipe_074": from_pool("smoothie"),
    # Energy balls / protein balls / date balls → dessert/snack
    "recipe_070": from_pool("dessert"),
    "recipe_099": from_pool("dessert"),
    "recipe_176": from_pool("dessert"),
    "recipe_177": from_pool("dessert"),
    "recipe_187": from_pool("dessert"),
    # Halva, tahini cookie, mousse → dessert
    "recipe_191": from_pool("dessert"),
    "recipe_192": from_pool("dessert"),
    "recipe_190": from_pool("dessert"),
    # Kale chips / popcorn / crackers → snack
    "recipe_194": from_pool("snack"),
    "recipe_195": from_pool("snack"),
    "recipe_203": from_pool("snack"),
    # Okra stew → soup/stew
    "recipe_092": from_pool("soup"),
    "recipe_242": from_pool("soup"),
    # Bamya → soup/stew
    # Poke bowl → salad-ish
    "recipe_149": from_pool("salad_greek"),
    # Mansaf (lamb + rice) → lamb
    "recipe_150": from_pool("lamb"),
    # Jambalaya → rice
    "recipe_147": from_pool("rice"),
    # Falafel → wrap/pita
    "recipe_132": from_pool("wrap_pita"),
    # Tabbouleh → bulgur grain
    "recipe_034": from_pool("bulgur_grain"),
    "recipe_073": from_pool("bulgur_grain"),
    # Ful medames → bean stew
    "recipe_066": from_pool("bean_stew"),
    "recipe_130": from_pool("bean_stew"),
    # Split pea → bean stew
    "recipe_262": from_pool("bean_stew"),
    # Black-eyed pea → bean stew
    "recipe_251": from_pool("bean_stew"),
    "recipe_255": from_pool("salad_grain"),
    # Buckwheat → grain salad
    "recipe_052": from_pool("bulgur_grain"),
    # Freekeh → bulgur grain
    "recipe_246": from_pool("bulgur_grain"),
    "recipe_232": from_pool("bulgur_grain"),
    # Protein pancakes → pancakes
    "recipe_088": from_pool("pancakes"),
    "recipe_101": from_pool("pancakes"),
    "recipe_102": from_pool("pancakes"),
    # Sweet crepe → pancakes
    "recipe_189": from_pool("pancakes"),
    # Granola bar → granola
    "recipe_049": from_pool("granola_oat"),
    "recipe_067": from_pool("granola_oat"),
    "recipe_178": from_pool("granola_oat"),
    "recipe_186": from_pool("granola_oat"),
    # Prickly pear bowl → fruit salad
    "recipe_250": from_pool("salad_green"),
    # Sahlab → smoothie/drink
    "recipe_230": from_pool("smoothie"),
    # Halloumi salad → greek salad
    "recipe_144": from_pool("salad_greek"),
    # Caesar salad → greek salad
    "recipe_145": from_pool("salad_greek"),
    # Carrot muffins / chocolate muffins → dessert
    "recipe_080": from_pool("dessert"),
    "recipe_185": from_pool("dessert"),
    "recipe_209": from_pool("dessert"),
    # Apple cake
    "recipe_086": from_pool("dessert"),
    # Banana ice cream → dessert
    "recipe_184": from_pool("dessert"),
    # Chocolate torte → dessert
    "recipe_093": from_pool("dessert"),
    # Oat cookies → dessert
    "recipe_186": from_pool("dessert"),
}


# ── Category classifier (fallback when TheMealDB fails) ──────────────────────
def classify(name: str) -> str:
    n = name.lower()
    if "shakshuka" in n:             return "shakshuka"
    if "schnitzel" in n:             return "schnitzel"
    if "shawarma" in n or "kebab" in n or "shishlik" in n: return "kebab"
    if "sabich" in n or "falafel" in n: return "wrap_pita"
    if "salmon" in n:                return "salmon"
    if "tuna" in n:                  return "tuna"
    if any(w in n for w in ["tilapia","sea bream","sea bass","mackerel","cod","barramundi",
                             "fish cake","moroccan fish"]): return "fish_baked"
    if "fish" in n:                  return "fish_baked"
    if any(w in n for w in ["omelette","frittata","pashitda","quiche","egg white"]): return "omelette"
    if "egg" in n:                   return "egg_dish"
    if any(w in n for w in ["chicken soup","yemenite chicken","jerusalem chicken"]): return "chicken_soup"
    if any(w in n for w in ["pad thai","stir-fried noodle","noodle"]): return "pasta"
    if any(w in n for w in ["chicken wrap","chicken tortilla","chicken meatball",
                             "chicken with rice","grilled chicken","paprika chicken",
                             "chicken with freekeh","freekeh with chicken"]): return "chicken_rice"
    if any(w in n for w in ["roasted chicken","oven-baked chicken","chicken thigh",
                             "lemon olive chicken"]): return "chicken_grill"
    if "chicken" in n:               return "chicken_grill"
    if "burger" in n or "hamburger" in n: return "burger"
    if "steak" in n:                 return "beef_steak"
    if any(w in n for w in ["beef stew","beef meatball","cholent","chamin"]): return "beef_stew"
    if any(w in n for w in ["meatball","kofta","kubbeh","kubeh","mafrum",
                             "stuffed cabbage","sausage"]): return "meatballs"
    if "lamb" in n or "mansaf" in n: return "lamb"
    if any(w in n for w in ["turkey schnitzel","turkey breast"]): return "schnitzel"
    if "turkey" in n:                return "meatballs"
    if "pizza" in n:                 return "pizza"
    if any(w in n for w in ["pasta","penne","linguine","lasagna","spaghetti","alfredo","pesto pasta"]): return "pasta"
    if "couscous" in n:              return "couscous"
    if "quinoa" in n:                return "quinoa"
    if any(w in n for w in ["bulgur","tabbouleh","tabouleh","freekeh","buckwheat",
                             "pomegranate bulgur"]): return "bulgur_grain"
    if any(w in n for w in ["mujadara","mujaddara","lentil rice","lentils & rice"]): return "lentil"
    if "rice" in n:                  return "rice"
    if "hummus" in n:                return "hummus"
    if "falafel" in n:               return "wrap_pita"
    if any(w in n for w in ["lentil","ful medames","split pea","black-eyed","chickpea soup",
                             "bean stew","bean toast","okra","bamya"]): return "bean_stew"
    if any(w in n for w in ["greek salad","caesar salad","halloumi salad"]): return "salad_greek"
    if any(w in n for w in ["grain salad","quinoa salad","bulgur salad","lentil salad",
                             "five grain","freekeh salad","black lentil salad",
                             "pomegranate bulgur","pea salad","black-eyed pea salad"]): return "salad_grain"
    if any(w in n for w in ["salad","tabbouleh","fattoush","eggplant salad",
                             "carrot salad","poke bowl","fruit salad","avocado salad",
                             "avocado mango","kohlrabi","beet salad"]): return "salad_green"
    if any(w in n for w in ["wrap","sandwich","toast","bruschetta","bagel",
                             "challah","bourekas","croissant","crepe","rye bread",
                             "pumpernickel","pita with","sabich in lafa"]): return "bread_toast"
    if any(w in n for w in ["flatbread","malawach","lahoh","jachnun"]): return "pancakes"
    if any(w in n for w in ["cottage cheese","labaneh","labneh","laban",
                             "tzfatit","bulgarian cheese","cheese bowl",
                             "yogurt bowl","persimmon yogurt"]): return "dairy_bowl"
    if "yogurt" in n:                return "yogurt_bowl"
    if any(w in n for w in ["granola","oatmeal","oat cookie","oatmeal cookie"]): return "granola_oat"
    if any(w in n for w in ["pancake","waffle"]): return "pancakes"
    if any(w in n for w in ["stuffed pepper","stuffed bell","stuffed zucchini",
                             "stuffed grape","stuffed mushroom","stuffed cabbage",
                             "stuffed vegetable","stuffed challah"]): return "stuffed_veg"
    if any(w in n for w in ["roasted","oven-roasted","tempura","stir-fry","stir fry",
                             "moussaka","baba ganoush","ratatouille","risotto",
                             "cauliflower","eggplant"]): return "veggie_roast"
    if any(w in n for w in ["vegetable","veggie","tofu"]): return "veggie_roast"
    if any(w in n for w in ["soup","stew","chamin","cholent"]): return "soup"
    if any(w in n for w in ["smoothie","shake","sahlab","milkshake"]): return "smoothie"
    if any(w in n for w in ["cake","cookie","muffin","chocolate ball","halva",
                             "torte","mousse","ice cream","date ball","energy ball",
                             "protein ball","popcorn","chips"]): return "dessert"
    if any(w in n for w in ["fruit","apple","banana","berry","acai"]): return "salad_green"
    if any(w in n for w in ["nuts","almond","walnut","pecan","crackers"]): return "snack"
    return "salad_green"


def best_search_terms(name_en: str) -> list[str]:
    """Return search terms to try, from most to least specific."""
    words = name_en.split()
    terms = [name_en]
    # First two meaningful words
    if len(words) >= 2:
        terms.append(" ".join(words[:2]))
    # First word only (if meaningful)
    if words and words[0].lower() not in ("the","a","an","with","in","and","baked","oven","grilled","roasted","homemade"):
        terms.append(words[0])
    # Key nouns
    for w in words:
        if w.lower() not in ("with","in","and","the","a","an","baked","grilled","roasted",
                              "oven-baked","warm","cold","hot","fresh","classic","israeli",
                              "homemade","mixed","creamy","spiced","stuffed","perfect"):
            if w not in terms:
                terms.append(w)
    return terms


def main():
    with open(RECIPES, encoding="utf-8") as f:
        data = json.load(f)
    recipes = data if isinstance(data, list) else data.get("recipes", [])

    results: dict[str, str] = {}
    stats = {"mealdb": 0, "manual": 0, "pool": 0}

    for r in recipes:
        rid     = r.get("recipe_id", "")
        name_en = r.get("name_en", "")
        name_he = r.get("name_he", "")

        # 1. Manual override
        if rid in MANUAL:
            results[rid] = MANUAL[rid]
            stats["manual"] += 1
            print(f"  📌 {rid} | {name_en[:40]:<40} | manual")
            continue

        # 2. TheMealDB search (try several terms)
        found = ""
        for term in best_search_terms(name_en):
            found = mealdb(term)
            if found:
                break
            time.sleep(0.15)

        if found:
            results[rid] = found
            stats["mealdb"] += 1
            print(f"  ✅ {rid} | {name_en[:40]:<40} | TheMealDB")
        else:
            # 3. Category pool fallback
            cat = classify(name_en)
            results[rid] = from_pool(cat)
            stats["pool"] += 1
            print(f"  🗂️  {rid} | {name_en[:40]:<40} | pool:{cat}")

        time.sleep(0.15)

    # Count unique images
    unique = len(set(results.values()))
    print(f"\n{'='*60}")
    print(f"Total:    {len(results)}")
    print(f"TheMealDB:{stats['mealdb']}  Manual:{stats['manual']}  Pool:{stats['pool']}")
    print(f"Unique images: {unique}  (was ~15 before)")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved → {OUT}")


if __name__ == "__main__":
    main()
