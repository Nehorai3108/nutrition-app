#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Add missing Israeli/common foods to foods_extended.json"""

import json, os, uuid

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(BASE, "nutrition_app", "data", "foods_extended.json")

NEW_FOODS = [
    # ── שניצלים ───────────────────────────────────────────────────────────────
    {"name_he":"שניצל תירס","name_en":"Corn Schnitzel","category":"protein",
     "calories_kcal":220,"protein_g":5.0,"carbs_g":22.0,"fat_g":12.0,"fiber_g":2.0,
     "default_unit":"unit","default_serving_g":80,"aliases_he":["שניצל תירס מטוגן","קציצת תירס"],"aliases_en":["corn schnitzel"],"source":"json"},
    {"name_he":"שניצל כרובית","name_en":"Cauliflower Schnitzel","category":"vegetable",
     "calories_kcal":180,"protein_g":5.5,"carbs_g":18.0,"fat_g":9.0,"fiber_g":3.0,
     "default_unit":"unit","default_serving_g":100,"aliases_he":["שניצל כרוביות"],"aliases_en":["cauliflower schnitzel"],"source":"json"},
    {"name_he":"שניצל הודו","name_en":"Turkey Schnitzel","category":"protein",
     "calories_kcal":195,"protein_g":24.0,"carbs_g":10.0,"fat_g":7.0,
     "default_unit":"unit","default_serving_g":130,"aliases_he":["שניצל טורקי"],"aliases_en":["turkey schnitzel"],"source":"json"},
    {"name_he":"שניצל בקר","name_en":"Beef Schnitzel","category":"protein",
     "calories_kcal":250,"protein_g":22.0,"carbs_g":12.0,"fat_g":13.0,
     "default_unit":"unit","default_serving_g":130,"aliases_he":[],"aliases_en":["beef schnitzel"],"source":"json"},

    # ── נאגטס ─────────────────────────────────────────────────────────────────
    {"name_he":"נאגטס עוף","name_en":"Chicken Nuggets","category":"protein",
     "calories_kcal":260,"protein_g":16.0,"carbs_g":16.0,"fat_g":14.0,
     "default_unit":"unit","default_serving_g":20,"aliases_he":["נאגטס","קראנצ'י עוף"],"aliases_en":["nuggets","chicken nuggets"],"source":"json"},

    # ── לביבות ────────────────────────────────────────────────────────────────
    {"name_he":"לביבות תפוחי אדמה","name_en":"Potato Latkes","category":"grain",
     "calories_kcal":200,"protein_g":3.5,"carbs_g":22.0,"fat_g":10.0,"fiber_g":2.0,
     "default_unit":"unit","default_serving_g":80,"aliases_he":["לביבה","לביבות","לאטקע"],"aliases_en":["latkes","potato pancakes","potato latkes"],"source":"json"},
    {"name_he":"לביבות גבינה","name_en":"Cheese Pancakes","category":"dairy",
     "calories_kcal":210,"protein_g":9.0,"carbs_g":20.0,"fat_g":10.0,
     "default_unit":"unit","default_serving_g":70,"aliases_he":["לביבות קוטג"],"aliases_en":["cheese latkes","cottage pancakes"],"source":"json"},

    # ── מרקים ─────────────────────────────────────────────────────────────────
    {"name_he":"מרק עוף","name_en":"Chicken Soup","category":"protein",
     "calories_kcal":45,"protein_g":4.5,"carbs_g":3.0,"fat_g":1.5,
     "default_unit":"cup","default_serving_g":250,"aliases_he":["מרק עוף צח","ציר עוף","מרק"],"aliases_en":["chicken broth","chicken soup"],"source":"json"},
    {"name_he":"מרק עגבניות","name_en":"Tomato Soup","category":"vegetable",
     "calories_kcal":65,"protein_g":2.0,"carbs_g":10.0,"fat_g":2.0,
     "default_unit":"cup","default_serving_g":250,"aliases_he":[],"aliases_en":["tomato soup"],"source":"json"},
    {"name_he":"מרק ירקות","name_en":"Vegetable Soup","category":"vegetable",
     "calories_kcal":55,"protein_g":2.5,"carbs_g":9.0,"fat_g":1.0,"fiber_g":2.5,
     "default_unit":"cup","default_serving_g":250,"aliases_he":[],"aliases_en":["vegetable soup"],"source":"json"},
    {"name_he":"מרק עדשים","name_en":"Lentil Soup","category":"legume",
     "calories_kcal":115,"protein_g":7.5,"carbs_g":17.0,"fat_g":2.0,"fiber_g":4.0,
     "default_unit":"cup","default_serving_g":250,"aliases_he":[],"aliases_en":["lentil soup"],"source":"json"},
    {"name_he":"מרק אפונה","name_en":"Pea Soup","category":"legume",
     "calories_kcal":110,"protein_g":6.5,"carbs_g":16.0,"fat_g":2.0,"fiber_g":4.0,
     "default_unit":"cup","default_serving_g":250,"aliases_he":[],"aliases_en":["pea soup"],"source":"json"},

    # ── מנות ישראליות ──────────────────────────────────────────────────────────
    {"name_he":"שקשוקה","name_en":"Shakshuka","category":"protein",
     "calories_kcal":165,"protein_g":10.0,"carbs_g":10.0,"fat_g":9.5,
     "default_unit":"gram","default_serving_g":300,"aliases_he":["שקשוקה עם ביצים"],"aliases_en":["shakshuka"],"source":"json"},
    {"name_he":"מג'דרה","name_en":"Mujaddara","category":"grain",
     "calories_kcal":150,"protein_g":6.0,"carbs_g":25.0,"fat_g":3.5,"fiber_g":4.5,
     "default_unit":"gram","default_serving_g":200,"aliases_he":["מג'דרה","מגדרה","עדשים עם אורז"],"aliases_en":["mujaddara","mujadara"],"source":"json"},
    {"name_he":"חמין","name_en":"Cholent","category":"protein",
     "calories_kcal":280,"protein_g":16.0,"carbs_g":25.0,"fat_g":10.0,"fiber_g":6.0,
     "default_unit":"gram","default_serving_g":300,"aliases_he":["צ'ולנט","שולנט"],"aliases_en":["cholent","chamin"],"source":"json"},
    {"name_he":"קובה","name_en":"Kubbeh","category":"protein",
     "calories_kcal":185,"protein_g":9.0,"carbs_g":20.0,"fat_g":7.5,
     "default_unit":"unit","default_serving_g":80,"aliases_he":["כובה","קובה סולת"],"aliases_en":["kubbeh","kibbeh"],"source":"json"},
    {"name_he":"סביח","name_en":"Sabich","category":"grain",
     "calories_kcal":420,"protein_g":14.0,"carbs_g":45.0,"fat_g":20.0,"fiber_g":5.0,
     "default_unit":"unit","default_serving_g":280,"aliases_he":["סביח בפיתה"],"aliases_en":["sabich"],"source":"json"},
    {"name_he":"ממולאים","name_en":"Stuffed Vegetables","category":"protein",
     "calories_kcal":160,"protein_g":8.0,"carbs_g":18.0,"fat_g":5.5,
     "default_unit":"unit","default_serving_g":150,"aliases_he":["ירק ממולא","עגבניה ממולאת","פלפל ממולא"],"aliases_en":["stuffed peppers","stuffed vegetables"],"source":"json"},
    {"name_he":"כרוב ממולא","name_en":"Stuffed Cabbage","category":"protein",
     "calories_kcal":155,"protein_g":9.0,"carbs_g":14.0,"fat_g":6.0,
     "default_unit":"unit","default_serving_g":130,"aliases_he":["גולובצי","כרוב ממולא בשר"],"aliases_en":["stuffed cabbage","golabki"],"source":"json"},

    # ── בשרים ────────────────────────────────────────────────────────────────
    {"name_he":"כנפיים עוף","name_en":"Chicken Wings","category":"protein",
     "calories_kcal":220,"protein_g":18.0,"carbs_g":0.0,"fat_g":15.0,
     "default_unit":"unit","default_serving_g":50,"aliases_he":["כנף עוף","כנפיים"],"aliases_en":["wings","chicken wings"],"source":"json"},
    {"name_he":"שיפוד עוף","name_en":"Chicken Skewer","category":"protein",
     "calories_kcal":175,"protein_g":22.0,"carbs_g":2.0,"fat_g":8.0,
     "default_unit":"unit","default_serving_g":120,"aliases_he":["שיפוד","שיפודים"],"aliases_en":["chicken skewer","shishlik"],"source":"json"},
    {"name_he":"פרגית","name_en":"Chicken Thigh","category":"protein",
     "calories_kcal":210,"protein_g":20.0,"carbs_g":0.0,"fat_g":14.0,
     "default_unit":"unit","default_serving_g":150,"aliases_he":["ירך עוף","פרגיות"],"aliases_en":["chicken thigh","dark meat chicken"],"source":"json"},
    {"name_he":"אנטריקוט","name_en":"Entrecote","category":"protein",
     "calories_kcal":280,"protein_g":28.0,"carbs_g":0.0,"fat_g":18.0,
     "default_unit":"gram","default_serving_g":200,"aliases_he":["אנטרקוט","סטייק אנטריקוט"],"aliases_en":["entrecote","ribeye"],"source":"json"},
    {"name_he":"כבד עוף מטוגן","name_en":"Fried Chicken Liver","category":"protein",
     "calories_kcal":195,"protein_g":22.0,"carbs_g":4.0,"fat_g":9.0,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["כבד מטוגן"],"aliases_en":["fried chicken liver"],"source":"json"},

    # ── דגים ─────────────────────────────────────────────────────────────────
    {"name_he":"דג בתנור","name_en":"Baked Fish","category":"protein",
     "calories_kcal":130,"protein_g":22.0,"carbs_g":0.0,"fat_g":4.5,
     "default_unit":"gram","default_serving_g":150,"aliases_he":["פילה דג בתנור","דג אפוי"],"aliases_en":["baked fish","fish fillet"],"source":"json"},
    {"name_he":"דג מטוגן","name_en":"Fried Fish","category":"protein",
     "calories_kcal":220,"protein_g":20.0,"carbs_g":8.0,"fat_g":11.0,
     "default_unit":"gram","default_serving_g":150,"aliases_he":["דג בציפוי"],"aliases_en":["fried fish"],"source":"json"},
    {"name_he":"טונה עם מיונז","name_en":"Tuna with Mayo","category":"protein",
     "calories_kcal":185,"protein_g":14.0,"carbs_g":1.0,"fat_g":14.0,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["סלט טונה"],"aliases_en":["tuna salad","tuna mayo"],"source":"json"},
    {"name_he":"גפילטע פיש","name_en":"Gefilte Fish","category":"protein",
     "calories_kcal":95,"protein_g":11.5,"carbs_g":4.5,"fat_g":3.0,
     "default_unit":"unit","default_serving_g":100,"aliases_he":["דג ממולא","גפילטע"],"aliases_en":["gefilte fish"],"source":"json"},

    # ── לחמים ומאפים ──────────────────────────────────────────────────────────
    {"name_he":"בגל ירושלמי","name_en":"Jerusalem Bagel","category":"grain",
     "calories_kcal":280,"protein_g":9.0,"carbs_g":52.0,"fat_g":4.0,
     "default_unit":"unit","default_serving_g":100,"aliases_he":["בייגל","בגל עם שומשום"],"aliases_en":["jerusalem bagel","sesame bagel"],"source":"json"},
    {"name_he":"לחמניה","name_en":"Bread Roll","category":"grain",
     "calories_kcal":145,"protein_g":5.0,"carbs_g":27.0,"fat_g":2.0,
     "default_unit":"unit","default_serving_g":55,"aliases_he":["לחמנייה"],"aliases_en":["bread roll","bun"],"source":"json"},
    {"name_he":"פוקצ'ה","name_en":"Focaccia","category":"grain",
     "calories_kcal":250,"protein_g":7.0,"carbs_g":38.0,"fat_g":8.0,
     "default_unit":"gram","default_serving_g":100,"aliases_he":[],"aliases_en":["focaccia"],"source":"json"},
    {"name_he":"צ'יאבטה","name_en":"Ciabatta","category":"grain",
     "calories_kcal":265,"protein_g":9.0,"carbs_g":50.0,"fat_g":3.5,
     "default_unit":"gram","default_serving_g":80,"aliases_he":["צ'יאבאטה"],"aliases_en":["ciabatta"],"source":"json"},
    {"name_he":"מלאווח","name_en":"Malaawach","category":"grain",
     "calories_kcal":380,"protein_g":8.0,"carbs_g":42.0,"fat_g":19.0,
     "default_unit":"unit","default_serving_g":120,"aliases_he":["מלווח","מלאוח"],"aliases_en":["malaawach","malawach"],"source":"json"},
    {"name_he":"ג'חנון","name_en":"Jachnun","category":"grain",
     "calories_kcal":350,"protein_g":7.5,"carbs_g":40.0,"fat_g":18.0,
     "default_unit":"unit","default_serving_g":120,"aliases_he":["ג'חנן"],"aliases_en":["jachnun"],"source":"json"},
    {"name_he":"פרוסת לחם אחידה","name_en":"White Bread Slice","category":"grain",
     "calories_kcal":80,"protein_g":2.5,"carbs_g":15.0,"fat_g":1.0,
     "default_unit":"slice","default_serving_g":30,"aliases_he":["לחם אחיד","לחם לבן פרוסה"],"aliases_en":["white bread slice"],"source":"json"},

    # ── בורקס ─────────────────────────────────────────────────────────────────
    {"name_he":"בורקס תפוח אדמה","name_en":"Potato Bourekas","category":"grain",
     "calories_kcal":265,"protein_g":5.5,"carbs_g":32.0,"fat_g":13.0,
     "default_unit":"unit","default_serving_g":80,"aliases_he":["בורקס עם תפוח אדמה"],"aliases_en":["potato bourekas"],"source":"json"},
    {"name_he":"בורקס פטריות","name_en":"Mushroom Bourekas","category":"grain",
     "calories_kcal":245,"protein_g":5.0,"carbs_g":28.0,"fat_g":12.5,
     "default_unit":"unit","default_serving_g":80,"aliases_he":[],"aliases_en":["mushroom bourekas"],"source":"json"},
    {"name_he":"בורקס תרד","name_en":"Spinach Bourekas","category":"grain",
     "calories_kcal":235,"protein_g":6.0,"carbs_g":26.0,"fat_g":11.5,
     "default_unit":"unit","default_serving_g":80,"aliases_he":["בורקס עלים"],"aliases_en":["spinach bourekas"],"source":"json"},

    # ── ביצים ─────────────────────────────────────────────────────────────────
    {"name_he":"ביצה קשה","name_en":"Hard Boiled Egg","category":"protein",
     "calories_kcal":78,"protein_g":6.3,"carbs_g":0.6,"fat_g":5.3,
     "default_unit":"unit","default_serving_g":50,"aliases_he":["ביצה מקושקשת","ביצה עין"],"aliases_en":["hard boiled egg","boiled egg"],"source":"json"},
    {"name_he":"חביתה","name_en":"Omelette","category":"protein",
     "calories_kcal":155,"protein_g":12.0,"carbs_g":1.0,"fat_g":11.0,
     "default_unit":"unit","default_serving_g":100,"aliases_he":["אומלט","חביתה עם ירקות"],"aliases_en":["omelette","omelet"],"source":"json"},

    # ── פסטה ──────────────────────────────────────────────────────────────────
    {"name_he":"פסטה ברוטב עגבניות","name_en":"Pasta with Tomato Sauce","category":"grain",
     "calories_kcal":165,"protein_g":5.5,"carbs_g":30.0,"fat_g":3.5,
     "default_unit":"gram","default_serving_g":250,"aliases_he":["פסטה ברוטב","פסטה עם רוטב"],"aliases_en":["pasta tomato","spaghetti bolognese"],"source":"json"},
    {"name_he":"פסטה ברוטב שמנת","name_en":"Pasta with Cream Sauce","category":"grain",
     "calories_kcal":285,"protein_g":8.0,"carbs_g":35.0,"fat_g":12.0,
     "default_unit":"gram","default_serving_g":250,"aliases_he":["פסטה אלפרדו","פסטה שמנת"],"aliases_en":["pasta cream","alfredo"],"source":"json"},
    {"name_he":"פסטה בולונז","name_en":"Pasta Bolognese","category":"grain",
     "calories_kcal":210,"protein_g":12.0,"carbs_g":28.0,"fat_g":6.0,
     "default_unit":"gram","default_serving_g":300,"aliases_he":["בולונז","ספגטי בולונז"],"aliases_en":["bolognese","spaghetti bolognese"],"source":"json"},
    {"name_he":"פיצה","name_en":"Pizza","category":"grain",
     "calories_kcal":265,"protein_g":11.0,"carbs_g":33.0,"fat_g":9.5,
     "default_unit":"slice","default_serving_g":100,"aliases_he":["פיצה גבינה","פיצה מרגריטה"],"aliases_en":["pizza","pizza slice"],"source":"json"},

    # ── סלטים ────────────────────────────────────────────────────────────────
    {"name_he":"סלט ישראלי","name_en":"Israeli Salad","category":"vegetable",
     "calories_kcal":45,"protein_g":1.5,"carbs_g":7.0,"fat_g":2.0,"fiber_g":2.0,
     "default_unit":"gram","default_serving_g":150,"aliases_he":["סלט ירושלמי","סלט ערבי"],"aliases_en":["israeli salad","arabic salad"],"source":"json"},
    {"name_he":"חצילים מרוקאים","name_en":"Moroccan Eggplant","category":"vegetable",
     "calories_kcal":85,"protein_g":1.5,"carbs_g":8.0,"fat_g":5.5,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["חציל מרוקאי","שקשוקת חצילים"],"aliases_en":["moroccan eggplant","eggplant salad"],"source":"json"},
    {"name_he":"חצילים שרופים","name_en":"Burnt Eggplant Salad","category":"vegetable",
     "calories_kcal":60,"protein_g":1.5,"carbs_g":7.0,"fat_g":3.0,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["סלט חצילים","בבא גנוש"],"aliases_en":["baba ganoush","eggplant dip"],"source":"json"},
    {"name_he":"סלט כרוב","name_en":"Coleslaw","category":"vegetable",
     "calories_kcal":70,"protein_g":1.5,"carbs_g":9.0,"fat_g":3.0,"fiber_g":2.5,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["כרוב קצוץ","קולסלאו"],"aliases_en":["coleslaw","cabbage salad"],"source":"json"},
    {"name_he":"סלט קיסר","name_en":"Caesar Salad","category":"vegetable",
     "calories_kcal":150,"protein_g":5.0,"carbs_g":8.0,"fat_g":11.0,
     "default_unit":"gram","default_serving_g":200,"aliases_he":[],"aliases_en":["caesar salad"],"source":"json"},
    {"name_he":"טאבולה","name_en":"Tabbouleh","category":"grain",
     "calories_kcal":130,"protein_g":3.5,"carbs_g":18.0,"fat_g":5.5,"fiber_g":3.0,
     "default_unit":"gram","default_serving_g":150,"aliases_he":["טבולה"],"aliases_en":["tabbouleh","tabouleh"],"source":"json"},

    # ── חטיפים ────────────────────────────────────────────────────────────────
    {"name_he":"במבה","name_en":"Bamba","category":"snack",
     "calories_kcal":540,"protein_g":11.0,"carbs_g":52.0,"fat_g":33.0,
     "default_unit":"gram","default_serving_g":30,"aliases_he":[],"aliases_en":["bamba","peanut puffs"],"source":"json"},
    {"name_he":"ביסלי","name_en":"Bisli","category":"snack",
     "calories_kcal":445,"protein_g":10.0,"carbs_g":72.0,"fat_g":14.0,
     "default_unit":"gram","default_serving_g":30,"aliases_he":[],"aliases_en":["bisli"],"source":"json"},
    {"name_he":"קרקרים","name_en":"Crackers","category":"grain",
     "calories_kcal":420,"protein_g":9.0,"carbs_g":68.0,"fat_g":12.0,
     "default_unit":"unit","default_serving_g":10,"aliases_he":["קרקר","ביסקוויטים"],"aliases_en":["crackers","biscuit"],"source":"json"},
    {"name_he":"חטיף אנרגיה","name_en":"Energy Bar","category":"snack",
     "calories_kcal":380,"protein_g":10.0,"carbs_g":55.0,"fat_g":12.0,
     "default_unit":"unit","default_serving_g":40,"aliases_he":["בר אנרגיה","גרנולה בר"],"aliases_en":["energy bar","granola bar"],"source":"json"},
    {"name_he":"פופקורן","name_en":"Popcorn","category":"snack",
     "calories_kcal":375,"protein_g":11.0,"carbs_g":74.0,"fat_g":4.5,
     "default_unit":"gram","default_serving_g":30,"aliases_he":[],"aliases_en":["popcorn"],"source":"json"},
    {"name_he":"חטיף שוקולד","name_en":"Chocolate Bar","category":"snack",
     "calories_kcal":535,"protein_g":6.0,"carbs_g":59.0,"fat_g":30.0,
     "default_unit":"unit","default_serving_g":50,"aliases_he":["שוקולד חלב","טבלת שוקולד"],"aliases_en":["chocolate bar","milk chocolate"],"source":"json"},

    # ── מתוקים ────────────────────────────────────────────────────────────────
    {"name_he":"קרמבו","name_en":"Krembo","category":"snack",
     "calories_kcal":105,"protein_g":1.5,"carbs_g":18.0,"fat_g":3.5,
     "default_unit":"unit","default_serving_g":28,"aliases_he":[],"aliases_en":["krembo"],"source":"json"},
    {"name_he":"עוגת גבינה","name_en":"Cheesecake","category":"snack",
     "calories_kcal":320,"protein_g":7.0,"carbs_g":28.0,"fat_g":20.0,
     "default_unit":"slice","default_serving_g":100,"aliases_he":["קייק גבינה"],"aliases_en":["cheesecake"],"source":"json"},
    {"name_he":"עוגת שוקולד","name_en":"Chocolate Cake","category":"snack",
     "calories_kcal":380,"protein_g":5.0,"carbs_g":48.0,"fat_g":19.0,
     "default_unit":"slice","default_serving_g":80,"aliases_he":[],"aliases_en":["chocolate cake"],"source":"json"},
    {"name_he":"עוגיות","name_en":"Cookies","category":"snack",
     "calories_kcal":450,"protein_g":6.0,"carbs_g":65.0,"fat_g":18.0,
     "default_unit":"unit","default_serving_g":15,"aliases_he":["עוגייה","ביסקוויט"],"aliases_en":["cookies","biscuits"],"source":"json"},
    {"name_he":"גלידה","name_en":"Ice Cream","category":"snack",
     "calories_kcal":200,"protein_g":3.5,"carbs_g":24.0,"fat_g":10.0,
     "default_unit":"scoop","default_serving_g":80,"aliases_he":["גלידת וניל","גביע גלידה"],"aliases_en":["ice cream","gelato"],"source":"json"},
    {"name_he":"חלבה","name_en":"Halva","category":"snack",
     "calories_kcal":469,"protein_g":12.0,"carbs_g":40.0,"fat_g":29.0,
     "default_unit":"gram","default_serving_g":30,"aliases_he":[],"aliases_en":["halva","halvah"],"source":"json"},
    {"name_he":"מקרון","name_en":"Macaron","category":"snack",
     "calories_kcal":380,"protein_g":6.0,"carbs_g":50.0,"fat_g":17.0,
     "default_unit":"unit","default_serving_g":20,"aliases_he":[],"aliases_en":["macaron","macaroon"],"source":"json"},

    # ── משקאות ────────────────────────────────────────────────────────────────
    {"name_he":"קפה הפוך","name_en":"Latte","category":"dairy",
     "calories_kcal":95,"protein_g":5.0,"carbs_g":10.0,"fat_g":4.0,
     "default_unit":"cup","default_serving_g":250,"aliases_he":["לאטה","קפה עם חלב"],"aliases_en":["latte","cafe latte"],"source":"json"},
    {"name_he":"קפה שחור","name_en":"Black Coffee","category":"other",
     "calories_kcal":2,"protein_g":0.3,"carbs_g":0.0,"fat_g":0.0,
     "default_unit":"cup","default_serving_g":240,"aliases_he":["אספרסו","קפה בוץ"],"aliases_en":["black coffee","espresso","americano"],"source":"json"},
    {"name_he":"מיץ תפוחים","name_en":"Apple Juice","category":"fruit",
     "calories_kcal":46,"protein_g":0.1,"carbs_g":11.3,"fat_g":0.1,
     "default_unit":"cup","default_serving_g":240,"aliases_he":[],"aliases_en":["apple juice"],"source":"json"},
    {"name_he":"שייק פירות","name_en":"Fruit Smoothie","category":"fruit",
     "calories_kcal":140,"protein_g":2.5,"carbs_g":30.0,"fat_g":1.0,
     "default_unit":"cup","default_serving_g":300,"aliases_he":["שייק","סמוזי פירות"],"aliases_en":["smoothie","fruit shake"],"source":"json"},
    {"name_he":"שייק חלבון","name_en":"Protein Shake","category":"protein",
     "calories_kcal":180,"protein_g":28.0,"carbs_g":10.0,"fat_g":3.0,
     "default_unit":"cup","default_serving_g":300,"aliases_he":["שייק חלבון","פרוטאין שייק"],"aliases_en":["protein shake","whey shake"],"source":"json"},
    {"name_he":"לימונדה","name_en":"Lemonade","category":"other",
     "calories_kcal":40,"protein_g":0.1,"carbs_g":10.5,"fat_g":0.0,
     "default_unit":"cup","default_serving_g":250,"aliases_he":[],"aliases_en":["lemonade"],"source":"json"},

    # ── מוצרי חלב ─────────────────────────────────────────────────────────────
    {"name_he":"גבינה בולגרית","name_en":"Bulgarian Cheese","category":"dairy",
     "calories_kcal":260,"protein_g":16.0,"carbs_g":1.5,"fat_g":21.0,
     "default_unit":"gram","default_serving_g":30,"aliases_he":["גבינה מלוחה"],"aliases_en":["bulgarian cheese","feta cheese","salty cheese"],"source":"json"},
    {"name_he":"לבן","name_en":"Laban","category":"dairy",
     "calories_kcal":55,"protein_g":3.5,"carbs_g":5.5,"fat_g":2.0,
     "default_unit":"cup","default_serving_g":250,"aliases_he":["לבן 1%","לבן 3%"],"aliases_en":["laban","buttermilk"],"source":"json"},
    {"name_he":"שמנת חמוצה","name_en":"Sour Cream","category":"dairy",
     "calories_kcal":190,"protein_g":3.0,"carbs_g":4.0,"fat_g":18.0,
     "default_unit":"tablespoon","default_serving_g":30,"aliases_he":["קרם פרש"],"aliases_en":["sour cream","creme fraiche"],"source":"json"},

    # ── קטניות ───────────────────────────────────────────────────────────────
    {"name_he":"פול","name_en":"Fava Beans","category":"legume",
     "calories_kcal":88,"protein_g":7.6,"carbs_g":13.0,"fat_g":0.4,"fiber_g":5.4,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["פול מבושל"],"aliases_en":["fava beans","broad beans","ful medames"],"source":"json"},
    {"name_he":"פולים ירוקים","name_en":"Edamame","category":"legume",
     "calories_kcal":121,"protein_g":11.9,"carbs_g":8.9,"fat_g":5.2,"fiber_g":5.2,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["אדמאמה"],"aliases_en":["edamame","green soybeans"],"source":"json"},
    {"name_he":"שעועית לבנה","name_en":"White Beans","category":"legume",
     "calories_kcal":139,"protein_g":9.7,"carbs_g":25.0,"fat_g":0.5,"fiber_g":6.3,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["פאסוליה"],"aliases_en":["white beans","cannellini"],"source":"json"},

    # ── ירקות נוספים ──────────────────────────────────────────────────────────
    {"name_he":"פטריות","name_en":"Mushrooms","category":"vegetable",
     "calories_kcal":22,"protein_g":3.1,"carbs_g":3.3,"fat_g":0.3,"fiber_g":1.0,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["פטרייה","פטריות שמפיניון","פטריות פורטובלו"],"aliases_en":["mushrooms","champignon"],"source":"json"},
    {"name_he":"ברוקולי מבושל","name_en":"Cooked Broccoli","category":"vegetable",
     "calories_kcal":35,"protein_g":2.4,"carbs_g":6.6,"fat_g":0.4,"fiber_g":2.6,
     "default_unit":"gram","default_serving_g":150,"aliases_he":[],"aliases_en":["cooked broccoli","steamed broccoli"],"source":"json"},
    {"name_he":"סלרי","name_en":"Celery","category":"vegetable",
     "calories_kcal":16,"protein_g":0.7,"carbs_g":3.0,"fat_g":0.2,"fiber_g":1.6,
     "default_unit":"gram","default_serving_g":100,"aliases_he":["סלרי","כרפס"],"aliases_en":["celery"],"source":"json"},
    {"name_he":"חסה","name_en":"Lettuce","category":"vegetable",
     "calories_kcal":15,"protein_g":1.4,"carbs_g":2.9,"fat_g":0.2,"fiber_g":1.3,
     "default_unit":"gram","default_serving_g":50,"aliases_he":["חסה ירוקה","חסה אייסברג"],"aliases_en":["lettuce","iceberg","romaine"],"source":"json"},
]

def main():
    with open(OUT, encoding='utf-8') as f:
        foods = json.load(f)

    existing_names = {f.get('name_he','').strip() for f in foods}
    added = 0

    for food in NEW_FOODS:
        if food['name_he'] in existing_names:
            print(f"  SKIP (exists): {food['name_he']}")
            continue

        # Generate food_id
        food['food_id'] = f"json_{food['name_en'].lower().replace(' ','_')[:30]}"
        # Ensure required fields
        food.setdefault('fiber_g', 0.0)
        food.setdefault('sugar_g', 0.0)
        food.setdefault('sodium_mg', 0.0)
        food.setdefault('aliases_he', [])
        food.setdefault('aliases_en', [])
        food.setdefault('is_custom', False)

        foods.append(food)
        existing_names.add(food['name_he'])
        added += 1
        print(f"  ✅ Added: {food['name_he']}")

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(foods, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(foods)} foods ({added} new)")

if __name__ == '__main__':
    main()
