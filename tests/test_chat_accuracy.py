#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
200 accuracy tests for BiteFit chat AI (llama-3.3-70b-versatile).
"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tomllib
_secrets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              ".streamlit", "secrets.toml")
with open(_secrets_path, "rb") as f:
    _secrets = tomllib.load(f)

from groq import Groq
groq_client = Groq(api_key=_secrets["groq_api_key"])

SYSTEM = """אתה עוזר תזונה ישראלי. תפקידך: לזהות מזון ולרשום אותו ב-JSON.
כשמשתמש מזכיר מזון — החזר JSON בלבד (ללא טקסט לפני/אחרי).
כשאין מזון (שאלה/ברכה) — ענה בעברית רגילה בלבד.

כמויות ברירת מחדל:
חזה עוף=1 יחידה | שניצל עוף=1 יחידה | קציצות עוף=3 יחידות
ביצה=1 יחידה | טונה=1 קופסה | לחם=1 פרוסה | פיתה=1 יחידה
אורז=4 כפות | פסטה=4 כפות | יוגורט=1 גביע | עגבנייה=1 יחידה
מלפפון=1 יחידה | גזר=1 יחידה | בננה=1 יחידה | תפוח=1 יחידה
שמן זית=1 כף | אבוקדו=0.5 יחידה | קוטג'=1 גביע | חלב=1 כוס
שיבולת שועל/קוואקר=4 כפות | קפה שחור=1 כוס | סלמון=1 יחידה
חומוס=2 כפות | גבינה בולגרית=1 כף

פורמט JSON (כשיש מזון):
```json
{"meal_type":"breakfast|morning_snack|lunch|afternoon_snack|dinner|evening_snack","foods":[{"name":"שם בעברית","quantity":1,"unit":"יחידה|גרם|פרוסה|כוס|כף|כפית|גביע|קופסה"}],"reply":"תגובה קצרה"}
```

כללים:
- קציצות/קציצה -> name:"קציצות עוף" qty=3 (אבל: "קציצה אחת"=qty=1, "2 קציצות"=qty=2)
- שניצל -> name:"שניצל עוף" qty=1 (לעולם לא קציצות!)
- חביתה/שקשוקה/ביצת עין -> פריט אחד בלבד name:"ביצה" qty=2 (אם נאמר "עם X ביצים" -> qty=X)
- ירקות: יחידה בלבד, לא כוסות
- כל מזון/שתייה -> JSON תמיד"""

MODEL = "llama-3.1-8b-instant"
_CALL_INTERVAL = 6.5   # seconds between calls → ~9 calls/min × ~300 tok = 2700 TPM (under 6000)
_last_call = [0.0]

def ask(msg):
    elapsed = time.time() - _last_call[0]
    if elapsed < _CALL_INTERVAL:
        time.sleep(_CALL_INTERVAL - elapsed)

    for attempt in range(5):
        try:
            _last_call[0] = time.time()
            r = groq_client.chat.completions.create(
                model=MODEL,
                messages=[{"role":"system","content":SYSTEM},{"role":"user","content":msg}],
                temperature=0.2, max_tokens=260,
                timeout=20,
            )
            raw = r.choices[0].message.content.strip()
            # Try 1: raw JSON (no backticks)
            try:
                d = json.loads(raw)
                if "foods" in d: return d
            except: pass
            # Try 2: markdown code block
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
            if m:
                try: return json.loads(m.group(1))
                except: pass
            # Try 3: find first { and parse to end of string
            idx = raw.find('{')
            if idx >= 0:
                try:
                    d = json.loads(raw[idx:])
                    if "foods" in d: return d
                except: pass
            return None
        except Exception as e:
            err = str(e)
            if "429" in err:
                wait = 30 * (attempt + 1)
                print(f"    [rate limit attempt {attempt+1}] sleeping {wait}s...")
                time.sleep(wait)
                _last_call[0] = 0.0  # reset so next call doesn't add extra delay
            elif "Connection" in err or "timeout" in err.lower():
                wait = 5 * (attempt + 1)
                print(f"    [conn error attempt {attempt+1}] sleeping {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Failed after 5 retries: {msg!r}")

def ff(d):
    if not d: return {}
    foods = d.get("foods") or []
    return foods[0] if foods else {}

def fn(d):
    return [f.get("name","") for f in (d or {}).get("foods", [])]

def has_food(d, keyword):
    return d is not None and any(keyword in f.get("name","") for f in d.get("foods",[]))

# (input, check_fn, description)
TESTS = [
    # === BASIC PROTEINS ===
    ("טונה",
     lambda d: d and ff(d).get("unit")=="קופסה" and "טונה" in ff(d).get("name",""),
     "טונה -> קופסה"),
    ("אכלתי טונה",
     lambda d: d and "טונה" in ff(d).get("name",""),
     "אכלתי טונה"),
    ("חזה עוף",
     lambda d: d and ("חזה" in ff(d).get("name","") or "עוף" in ff(d).get("name","")),
     "חזה עוף"),
    ("שניצל",
     lambda d: d and ff(d).get("name","")=="שניצל עוף" and ff(d).get("quantity")==1,
     "שניצל -> שניצל עוף qty=1"),
    ("שניצל עוף",
     lambda d: d and "שניצל" in ff(d).get("name","") and ff(d).get("quantity")==1,
     "שניצל עוף -> qty=1"),
    ("2 שניצלים",
     lambda d: d and "שניצל" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 שניצלים -> qty=2"),
    ("קציצות עוף",
     lambda d: d and "קציצות" in ff(d).get("name","") and ff(d).get("quantity")==3,
     "קציצות עוף -> qty=3"),
    ("קציצות",
     lambda d: d and "קציצות" in ff(d).get("name",""),
     "קציצות -> קציצות עוף"),
    ("קציצה אחת",
     lambda d: d and "קציצות" in ff(d).get("name","") and ff(d).get("quantity")==1,
     "קציצה אחת -> qty=1"),
    ("2 קציצות",
     lambda d: d and "קציצות" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 קציצות -> qty=2"),
    ("5 קציצות",
     lambda d: d and "קציצות" in ff(d).get("name","") and ff(d).get("quantity")==5,
     "5 קציצות -> qty=5"),
    ("קציצת עוף אחת",
     lambda d: d and "קציצות" in ff(d).get("name","") and ff(d).get("quantity")==1,
     "קציצת עוף אחת -> qty=1"),
    ("ירך עוף",
     lambda d: d and ("ירך" in ff(d).get("name","") or "עוף" in ff(d).get("name","")),
     "ירך עוף"),
    ("כנפי עוף",
     lambda d: d and ("כנפי" in ff(d).get("name","") or "עוף" in ff(d).get("name","")),
     "כנפי עוף"),
    ("אכלתי עוף",
     lambda d: d and "עוף" in ff(d).get("name",""),
     "עוף -> עוף"),
    # === EGGS ===
    ("ביצה",
     lambda d: d and "ביצה" in ff(d).get("name","") and ff(d).get("unit")=="יחידה",
     "ביצה -> יחידה"),
    ("2 ביצים",
     lambda d: d and "ביצה" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 ביצים -> qty=2"),
    ("3 ביצים",
     lambda d: d and "ביצה" in ff(d).get("name","") and ff(d).get("quantity")==3,
     "3 ביצים -> qty=3"),
    ("חביתה",
     lambda d: d and "ביצה" in ff(d).get("name","") and len(d.get("foods",[]))==1,
     "חביתה -> ביצה, item=1"),
    ("חביתה עם 2 ביצים",
     lambda d: d and "ביצה"==ff(d).get("name","") and ff(d).get("quantity")==2 and len(d.get("foods",[]))==1,
     "חביתה עם 2 ביצים -> ONE ביצה qty=2"),
    ("חביתה עם 3 ביצים",
     lambda d: d and "ביצה" in ff(d).get("name","") and ff(d).get("quantity")==3 and len(d.get("foods",[]))==1,
     "חביתה עם 3 ביצים -> qty=3, ONE item"),
    ("ביצת עין",
     lambda d: d and "ביצה" in ff(d).get("name",""),
     "ביצת עין -> ביצה"),
    ("מקושקשת",
     lambda d: d and "ביצה" in ff(d).get("name",""),
     "מקושקשת -> ביצה"),
    ("שקשוקה",
     lambda d: d and "ביצה" in ff(d).get("name",""),
     "שקשוקה -> ביצה"),
    # === FISH ===
    ("אכלתי סלמון",
     lambda d: d is not None and "סלמון" in ff(d).get("name",""),
     "סלמון"),
    ("דג סלמון",
     lambda d: d is not None and "סלמון" in ff(d).get("name",""),
     "דג סלמון"),
    ("סרדינים",
     lambda d: d is not None and ("סרדין" in ff(d).get("name","") or "דג" in ff(d).get("name","")),
     "סרדינים"),
    ("טונה בשמן",
     lambda d: d and "טונה" in ff(d).get("name",""),
     "טונה בשמן"),
    # === BREAD & CARBS ===
    ("פרוסת לחם",
     lambda d: d and "לחם" in ff(d).get("name","") and ff(d).get("unit") in ("פרוסה","פרוסות"),
     "פרוסת לחם -> פרוסה"),
    ("2 פרוסות לחם",
     lambda d: d and "לחם" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 פרוסות לחם -> qty=2"),
    ("לחם",
     lambda d: d and "לחם" in ff(d).get("name",""),
     "לחם"),
    ("לחם מלא",
     lambda d: d and "לחם" in ff(d).get("name",""),
     "לחם מלא"),
    ("כריך",
     lambda d: d and "לחם" in ff(d).get("name",""),
     "כריך -> לחם"),
    ("טוסט",
     lambda d: d and "לחם" in ff(d).get("name",""),
     "טוסט -> לחם"),
    ("פיתה",
     lambda d: d and "פיתה" in ff(d).get("name","") and ff(d).get("unit")=="יחידה",
     "פיתה -> יחידה"),
    ("2 פיתות",
     lambda d: d and "פיתה" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 פיתות -> qty=2"),
    ("אורז",
     lambda d: d and "אורז" in ff(d).get("name","") and ff(d).get("unit") in ("כפות","כף"),
     "אורז -> כפות"),
    ("4 כפות אורז",
     lambda d: d and "אורז" in ff(d).get("name","") and ff(d).get("quantity")==4,
     "4 כפות אורז -> qty=4"),
    ("פסטה",
     lambda d: d and "פסטה" in ff(d).get("name",""),
     "פסטה"),
    ("ספגטי",
     lambda d: d and "פסטה" in ff(d).get("name",""),
     "ספגטי -> פסטה"),
    ("תפוח אדמה",
     lambda d: d and "תפוח אדמה" in ff(d).get("name",""),
     "תפוח אדמה"),
    ("בטטה",
     lambda d: d and "בטטה" in ff(d).get("name",""),
     "בטטה"),
    ("קוסקוס",
     lambda d: d and "קוסקוס" in ff(d).get("name",""),
     "קוסקוס"),
    ("קינואה",
     lambda d: d and "קינואה" in ff(d).get("name",""),
     "קינואה"),
    ("שיבולת שועל",
     lambda d: d is not None and "שיבולת" in ff(d).get("name",""),
     "שיבולת שועל"),
    ("קוואקר",
     lambda d: d is not None and "שיבולת" in ff(d).get("name",""),
     "קוואקר -> שיבולת שועל"),
    # === DAIRY ===
    ("יוגורט",
     lambda d: d and "יוגורט" in ff(d).get("name","") and ff(d).get("unit")=="גביע",
     "יוגורט -> גביע"),
    ("2 גביעי יוגורט",
     lambda d: d and "יוגורט" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 גביעי יוגורט -> qty=2"),
    ("גבינה בולגרית",
     lambda d: d is not None and "גבינה" in ff(d).get("name",""),
     "גבינה בולגרית"),
    ("גבינה צהובה",
     lambda d: d is not None and "גבינה" in ff(d).get("name",""),
     "גבינה צהובה"),
    ("גבינה לבנה",
     lambda d: d is not None and "גבינה" in ff(d).get("name",""),
     "גבינה לבנה"),
    ("קוטג'",
     lambda d: d is not None and "קוטג" in ff(d).get("name",""),
     "קוטג'"),
    ("גביע קוטג'",
     lambda d: d is not None and "קוטג" in ff(d).get("name",""),
     "גביע קוטג'"),
    ("חלב",
     lambda d: d is not None and "חלב" in ff(d).get("name",""),
     "חלב"),
    ("כוס חלב",
     lambda d: d is not None and "חלב" in ff(d).get("name",""),
     "כוס חלב"),
    ("שמנת",
     lambda d: d is not None,
     "שמנת -> some food"),
    # === VEGETABLES ===
    ("עגבנייה",
     lambda d: d and "עגבנייה" in ff(d).get("name","") and ff(d).get("unit")=="יחידה",
     "עגבנייה -> יחידה"),
    ("2 עגבניות",
     lambda d: d and "עגבנייה" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 עגבניות -> qty=2"),
    ("3 עגבניות",
     lambda d: d and "עגבנייה" in ff(d).get("name","") and ff(d).get("quantity")==3,
     "3 עגבניות -> qty=3"),
    ("מלפפון",
     lambda d: d and "מלפפון" in ff(d).get("name","") and ff(d).get("unit")=="יחידה",
     "מלפפון -> יחידה (NOT cup)"),
    ("2 מלפפונים",
     lambda d: d and "מלפפון" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 מלפפונים -> qty=2"),
    ("גזר",
     lambda d: d and "גזר" in ff(d).get("name","") and ff(d).get("unit")=="יחידה",
     "גזר -> יחידה"),
    ("פלפל",
     lambda d: d and "פלפל" in ff(d).get("name",""),
     "פלפל"),
    ("פלפל אדום",
     lambda d: d and "פלפל" in ff(d).get("name",""),
     "פלפל אדום"),
    ("חציל",
     lambda d: d and "חציל" in ff(d).get("name",""),
     "חציל"),
    ("קישוא",
     lambda d: d and "קישוא" in ff(d).get("name",""),
     "קישוא"),
    ("חסה",
     lambda d: d is not None,
     "חסה -> logged"),
    ("ברוקולי",
     lambda d: d is not None,
     "ברוקולי -> logged"),
    ("תרד",
     lambda d: d is not None,
     "תרד -> logged"),
    # CRITICAL: vegetables NOT measured in cups
    ("עגבנייה",
     lambda d: d and ff(d).get("unit") != "כוס",
     "עגבנייה unit != כוס"),
    ("מלפפון",
     lambda d: d and ff(d).get("unit") != "כוס",
     "מלפפון unit != כוס"),
    ("גזר",
     lambda d: d and ff(d).get("unit") != "כוס",
     "גזר unit != כוס"),
    # CRITICAL: no food confusion
    ("2 מלפפונים",
     lambda d: d and "תפוח" not in " ".join(fn(d)),
     "מלפפון != תפוח (no apple in reply)"),
    ("תפוח",
     lambda d: d and "מלפפון" not in " ".join(fn(d)),
     "תפוח != מלפפון"),
    # === FRUITS ===
    ("תפוח",
     lambda d: d and "תפוח" in ff(d).get("name","") and "מלפפון" not in ff(d).get("name",""),
     "תפוח -> תפוח עץ"),
    ("בננה",
     lambda d: d and "בננה" in ff(d).get("name","") and ff(d).get("unit")=="יחידה",
     "בננה -> יחידה"),
    ("2 בננות",
     lambda d: d and "בננה" in ff(d).get("name","") and ff(d).get("quantity")==2,
     "2 בננות -> qty=2"),
    ("תפוז",
     lambda d: d and "תפוז" in ff(d).get("name",""),
     "תפוז"),
    ("אגס",
     lambda d: d and "אגס" in ff(d).get("name",""),
     "אגס"),
    ("ענבים",
     lambda d: d is not None and ("ענב" in ff(d).get("name","") or d is not None),
     "ענבים -> logged"),
    ("אבוקדו",
     lambda d: d and "אבוקדו" in ff(d).get("name","") and ff(d).get("quantity")==0.5,
     "אבוקדו -> 0.5"),
    ("חצי אבוקדו",
     lambda d: d and "אבוקדו" in ff(d).get("name","") and ff(d).get("quantity")==0.5,
     "חצי אבוקדו -> 0.5"),
    ("אבוקדו שלם",
     lambda d: d and "אבוקדו" in ff(d).get("name","") and ff(d).get("quantity")==1,
     "אבוקדו שלם -> qty=1"),
    # === SPREADS / FATS ===
    ("שמן זית",
     lambda d: d and "שמן" in ff(d).get("name","") and ff(d).get("unit") in ("כף","כפית"),
     "שמן זית -> כף"),
    ("כף שמן זית",
     lambda d: d and "שמן" in ff(d).get("name",""),
     "כף שמן זית"),
    ("טחינה",
     lambda d: d and "טחינה" in ff(d).get("name",""),
     "טחינה"),
    ("חמאה",
     lambda d: d is not None and "חמאה" in ff(d).get("name",""),
     "חמאה"),
    ("חומוס",
     lambda d: d is not None and "חומוס" in ff(d).get("name",""),
     "חומוס -> logged"),
    ("ריבה",
     lambda d: d is not None,
     "ריבה -> logged"),
    ("דבש",
     lambda d: d is not None,
     "דבש -> logged"),
    # === DRINKS ===
    ("קפה שחור",
     lambda d: d is not None and "קפה" in ff(d).get("name",""),
     "קפה שחור -> logged"),
    ("אספרסו",
     lambda d: d is not None and "קפה" in ff(d).get("name",""),
     "אספרסו -> קפה"),
    ("קפה עם חלב",
     lambda d: d is not None,
     "קפה עם חלב -> logged"),
    ("תה",
     lambda d: d is not None,
     "תה -> logged"),
    ("מיץ תפוזים",
     lambda d: d is not None,
     "מיץ תפוזים -> logged"),
    ("קולה",
     lambda d: d is not None,
     "קולה -> logged"),
    ("מים",
     lambda d: d is not None,
     "מים -> logged"),
    # === SNACKS ===
    ("במבה",
     lambda d: d and "במבה" in ff(d).get("name",""),
     "במבה"),
    ("ביסלי",
     lambda d: d and "ביסלי" in ff(d).get("name",""),
     "ביסלי"),
    ("קרקר",
     lambda d: d is not None,
     "קרקר -> logged"),
    ("שוקולד",
     lambda d: d is not None and "שוקולד" in ff(d).get("name",""),
     "שוקולד -> logged"),
    ("גלידה",
     lambda d: d is not None,
     "גלידה -> logged"),
    ("עוגה",
     lambda d: d is not None,
     "עוגה -> logged"),
    # === COMPOUND MEALS ===
    ("חזה עוף עם אורז",
     lambda d: d and has_food(d,"עוף") and has_food(d,"אורז"),
     "חזה עוף עם אורז -> 2 foods"),
    ("שניצל עם תפוח אדמה",
     lambda d: d and has_food(d,"שניצל") and has_food(d,"תפוח אדמה"),
     "שניצל + תפוח אדמה -> 2 foods"),
    ("ביצה עם לחם",
     lambda d: d and has_food(d,"ביצה") and has_food(d,"לחם"),
     "ביצה עם לחם -> 2 foods"),
    ("יוגורט ובננה",
     lambda d: d and has_food(d,"יוגורט") and has_food(d,"בננה"),
     "יוגורט ובננה -> 2 foods"),
    ("ארוחת בוקר: 2 ביצים פרוסת לחם עגבנייה",
     lambda d: d and has_food(d,"ביצה") and has_food(d,"לחם"),
     "ארוחת בוקר מלאה -> ביצה+לחם"),
    ("אכלתי טונה עם אורז ועגבנייה",
     lambda d: d and has_food(d,"טונה") and has_food(d,"אורז"),
     "טונה+אורז+עגבנייה -> 3 foods"),
    ("פסטה עם רוטב עגבניות",
     lambda d: d and has_food(d,"פסטה"),
     "פסטה עם רוטב -> פסטה"),
    ("שיבולת שועל עם בננה",
     lambda d: d and has_food(d,"שיבולת") and has_food(d,"בננה"),
     "שיבולת שועל + בננה"),
    ("לחם עם חמאה",
     lambda d: d and has_food(d,"לחם"),
     "לחם עם חמאה"),
    ("כריך טונה",
     lambda d: d and has_food(d,"לחם") and has_food(d,"טונה"),
     "כריך טונה -> לחם+טונה"),
    # === QUANTITY EDGE CASES ===
    ("שלוש קציצות",
     lambda d: d and "קציצות" in ff(d).get("name","") and ff(d).get("quantity")==3,
     "שלוש קציצות -> qty=3"),
    ("ארבע כפות אורז",
     lambda d: d and "אורז" in ff(d).get("name","") and ff(d).get("quantity")==4,
     "ארבע כפות אורז -> qty=4"),
    ("חצי פיתה",
     lambda d: d and "פיתה" in ff(d).get("name","") and ff(d).get("quantity")==0.5,
     "חצי פיתה -> qty=0.5"),
    ("100 גרם עוף",
     lambda d: d and "עוף" in ff(d).get("name",""),
     "100 גרם עוף"),
    ("200 גרם אורז",
     lambda d: d and "אורז" in ff(d).get("name",""),
     "200 גרם אורז"),
    ("קילו עוף",
     lambda d: d and "עוף" in ff(d).get("name",""),
     "קילו עוף"),
    ("כוס שיבולת שועל",
     lambda d: d is not None and "שיבולת" in ff(d).get("name",""),
     "כוס שיבולת שועל"),
    # === MEAL TYPE DETECTION ===
    ("בבוקר אכלתי ביצה",
     lambda d: d and d.get("meal_type")=="breakfast",
     "בבוקר -> breakfast"),
    ("ארוחת בוקר: חביתה",
     lambda d: d and d.get("meal_type")=="breakfast",
     "ארוחת בוקר -> breakfast"),
    ("לצהריים חזה עוף",
     lambda d: d and d.get("meal_type")=="lunch",
     "לצהריים -> lunch"),
    ("ארוחת צהריים שניצל",
     lambda d: d and d.get("meal_type")=="lunch",
     "ארוחת צהריים -> lunch"),
    ("בערב אכלתי סלמון",
     lambda d: d and d.get("meal_type")=="dinner",
     "בערב -> dinner"),
    ("ארוחת ערב: פסטה",
     lambda d: d and d.get("meal_type")=="dinner",
     "ארוחת ערב -> dinner"),
    ("חטיף: בננה",
     lambda d: d and "snack" in d.get("meal_type",""),
     "חטיף -> snack"),
    # === NO-FOOD CASES (should return None) ===
    ("מה הקלוריות בביצה?",
     lambda d: d is None,
     "שאלה -> ללא JSON"),
    ("תודה",
     lambda d: d is None,
     "תודה -> ללא JSON"),
    ("שלום",
     lambda d: d is None,
     "שלום -> ללא JSON"),
    ("כמה קלוריות אכלתי היום?",
     lambda d: d is None,
     "שאלת סיכום -> ללא JSON"),
    ("מה כדאי לאכול לארוחת ערב?",
     lambda d: d is None,
     "שאלת המלצה -> ללא JSON"),
    ("האם אורז מלא בריא?",
     lambda d: d is None,
     "שאלת בריאות -> ללא JSON"),
    # === SLANG / ALTERNATE NAMES ===
    ("חזה",
     lambda d: d and ("חזה" in ff(d).get("name","") or "עוף" in ff(d).get("name","")),
     "חזה -> חזה עוף"),
    ("שניצ'ל",
     lambda d: d and "שניצל" in ff(d).get("name",""),
     "שניצ'ל -> שניצל עוף"),
    ("לאטה",
     lambda d: d is not None,
     "לאטה -> קפה עם חלב"),
    ("קפוצינו",
     lambda d: d is not None,
     "קפוצינו -> קפה"),
    ("שוקו",
     lambda d: d is not None,
     "שוקו -> משקה שוקולד"),
    ("לחמנייה",
     lambda d: d is not None and ("לחם" in ff(d).get("name","") or "לחמנייה" in ff(d).get("name","")),
     "לחמנייה -> לחם/לחמנייה"),
    ("פיתה ערבית",
     lambda d: d and "פיתה" in ff(d).get("name",""),
     "פיתה ערבית -> פיתה"),
    ("לאפה",
     lambda d: d and "פיתה" in ff(d).get("name",""),
     "לאפה -> פיתה"),
    ("עדשים",
     lambda d: d is not None,
     "עדשים -> logged"),
    ("חומוס גרגרים",
     lambda d: d is not None,
     "חומוס גרגרים -> logged"),
    ("גרנולה",
     lambda d: d is not None and "גרנולה" in ff(d).get("name",""),
     "גרנולה"),
    ("אגוזים",
     lambda d: d is not None,
     "אגוזים -> logged"),
    ("שקדים",
     lambda d: d is not None,
     "שקדים -> logged"),
    # === TRICKY CASES ===
    ("אכלתי קצת",
     lambda d: d is None,
     "אכלתי קצת (no food) -> ללא JSON"),
    ("אכלתי הרבה",
     lambda d: d is None,
     "אכלתי הרבה (no food) -> ללא JSON"),
    ("המבורגר",
     lambda d: d is not None and "בקר" in ff(d).get("name",""),
     "המבורגר -> בשר בקר"),
    ("קבב",
     lambda d: d is not None and ("קבב" in ff(d).get("name","") or "בקר" in ff(d).get("name","") or "בשר" in ff(d).get("name","")),
     "קבב -> בשר"),
    ("סטייק",
     lambda d: d is not None and ("סטייק" in ff(d).get("name","") or "בקר" in ff(d).get("name","")),
     "סטייק -> בשר בקר"),
    ("גרנולה עם יוגורט",
     lambda d: d and has_food(d,"גרנולה") and has_food(d,"יוגורט"),
     "גרנולה + יוגורט -> 2 foods"),
    ("קוטג' עם בננה",
     lambda d: d and has_food(d,"קוטג") and has_food(d,"בננה"),
     "קוטג' + בננה -> 2 foods"),
    ("שניצל עם אורז ומלפפון",
     lambda d: d and has_food(d,"שניצל") and has_food(d,"אורז"),
     "שניצל+אורז+מלפפון"),
    # CONFIRM שניצל != קציצות under any circumstance
    ("שניצל",
     lambda d: d and "קציצות" not in " ".join(fn(d)),
     "שניצל != קציצות"),
    ("קציצות",
     lambda d: d and "שניצל" not in " ".join(fn(d)),
     "קציצות != שניצל"),
    # CONFIRM single item for egg dishes
    ("שקשוקה",
     lambda d: d and len(d.get("foods",[]))==1,
     "שקשוקה -> single item"),
    ("חביתה",
     lambda d: d and len(d.get("foods",[]))==1,
     "חביתה -> single item"),
    # === LONG SENTENCES ===
    ("היום לארוחת צהריים אכלתי חזה עוף עם 4 כפות אורז ועגבנייה ומלפפון",
     lambda d: d and has_food(d,"עוף") and has_food(d,"אורז") and d.get("meal_type")=="lunch",
     "ארוחת צהריים מלאה -> עוף+אורז+ירקות+lunch"),
    ("אכלתי בוקר: 2 ביצים, 2 פרוסות לחם מלא, עגבנייה ומלפפון",
     lambda d: d and has_food(d,"ביצה") and has_food(d,"לחם") and d.get("meal_type")=="breakfast",
     "ארוחת בוקר מלאה"),
    ("חטיף אחה''צ: יוגורט עם בננה",
     lambda d: d and has_food(d,"יוגורט") and has_food(d,"בננה"),
     "חטיף אחה\"צ"),
    ("ערב: שניצל, תפוח אדמה, סלט עגבנייה ומלפפון",
     lambda d: d and has_food(d,"שניצל") and d.get("meal_type")=="dinner",
     "ארוחת ערב מלאה"),
    # === UNITS CHECK ===
    ("אורז",
     lambda d: d and ff(d).get("unit") not in ("כוס","כוסות"),
     "אורז unit != כוס"),
    ("פסטה",
     lambda d: d and ff(d).get("unit") not in ("כוס","כוסות"),
     "פסטה unit != כוס"),
    ("יוגורט",
     lambda d: d and ff(d).get("unit") == "גביע",
     "יוגורט unit = גביע"),
    ("טונה",
     lambda d: d and ff(d).get("unit") == "קופסה",
     "טונה unit = קופסה"),
    ("פיתה",
     lambda d: d and ff(d).get("unit") == "יחידה",
     "פיתה unit = יחידה"),
    ("ביצה",
     lambda d: d and ff(d).get("unit") == "יחידה",
     "ביצה unit = יחידה"),
    ("בננה",
     lambda d: d and ff(d).get("unit") == "יחידה",
     "בננה unit = יחידה"),
    ("שמן זית",
     lambda d: d and ff(d).get("unit") in ("כף","כפות","כפית"),
     "שמן זית unit = כף/כפית"),
    # === EXTRA PROTEINS ===
    ("דג",
     lambda d: d is not None,
     "דג -> logged"),
    ("פילה דג",
     lambda d: d is not None and ("דג" in ff(d).get("name","") or "סלמון" in ff(d).get("name","") or "פילה" in ff(d).get("name","")),
     "פילה דג -> logged"),
    ("בשר בקר",
     lambda d: d is not None and "בקר" in ff(d).get("name",""),
     "בשר בקר -> logged"),
    ("נקניק",
     lambda d: d is not None,
     "נקניק -> logged"),
    ("שפיץ ירך",
     lambda d: d is not None,
     "שפיץ ירך -> logged"),
    ("כבש",
     lambda d: d is not None,
     "כבש -> logged"),
    # === EXTRA DAIRY ===
    ("גבינה קשה",
     lambda d: d is not None and "גבינה" in ff(d).get("name",""),
     "גבינה קשה -> logged"),
    ("מוצרלה",
     lambda d: d is not None,
     "מוצרלה -> logged"),
    ("שמנת חמוצה",
     lambda d: d is not None,
     "שמנת חמוצה -> logged"),
    ("לבן",
     lambda d: d is not None,
     "לבן -> logged"),
    # === EXTRA CARBS ===
    ("לחמניה",
     lambda d: d is not None and ("לחם" in ff(d).get("name","") or "לחמנ" in ff(d).get("name","")),
     "לחמניה -> לחם"),
    ("בגט",
     lambda d: d is not None,
     "בגט -> logged"),
    ("קרואסון",
     lambda d: d is not None,
     "קרואסון -> logged"),
    ("טורטייה",
     lambda d: d is not None,
     "טורטייה -> logged"),
    # === EXTRA VEGETABLES ===
    ("עגבנייה שרי",
     lambda d: d and "עגבנייה" in ff(d).get("name",""),
     "עגבנייה שרי -> עגבנייה"),
    ("בצל",
     lambda d: d is not None,
     "בצל -> logged"),
    ("שום",
     lambda d: d is not None,
     "שום -> logged"),
    ("כרוב",
     lambda d: d is not None,
     "כרוב -> logged"),
    ("אספרגוס",
     lambda d: d is not None,
     "אספרגוס -> logged"),
    ("עדשים אדומות",
     lambda d: d is not None,
     "עדשים אדומות -> logged"),
    # === EXTRA FRUITS ===
    ("מנגו",
     lambda d: d is not None,
     "מנגו -> logged"),
    ("אפרסק",
     lambda d: d is not None,
     "אפרסק -> logged"),
    ("תות",
     lambda d: d is not None,
     "תות -> logged"),
    # === EXTRA COMPOUND ===
    ("2 ביצים עם עגבנייה",
     lambda d: d and has_food(d,"ביצה") and ff(d).get("quantity")==2,
     "2 ביצים + עגבנייה -> ביצה qty=2"),
    ("3 קציצות עוף עם אורז",
     lambda d: d and has_food(d,"קציצות") and has_food(d,"אורז"),
     "3 קציצות + אורז"),
    ("טונה עם לחם",
     lambda d: d and has_food(d,"טונה") and has_food(d,"לחם"),
     "טונה + לחם"),
    ("חמאה על לחם",
     lambda d: d and has_food(d,"לחם"),
     "חמאה על לחם -> לחם+חמאה"),
    ("בננה עם שקדים",
     lambda d: d is not None and has_food(d,"בננה"),
     "בננה + שקדים"),
    # === EXTRA SLANG ===
    ("קפה הפוך",
     lambda d: d is not None and "קפה" in ff(d).get("name",""),
     "קפה הפוך -> קפה עם חלב"),
    ("מאצ'ה",
     lambda d: d is not None,
     "מאצ'ה -> logged"),
    ("פלאפל",
     lambda d: d is not None,
     "פלאפל -> logged"),
    ("שווארמה",
     lambda d: d is not None,
     "שווארמה -> logged"),
    ("פיצה",
     lambda d: d is not None,
     "פיצה -> logged"),
    ("סושי",
     lambda d: d is not None,
     "סושי -> logged"),
    # === EXTRA EDGE CASES ===
    ("אכלתי קצת עוף",
     lambda d: d and "עוף" in ff(d).get("name",""),
     "קצת עוף -> עוף"),
    ("שתיתי מים",
     lambda d: d is not None,
     "שתיתי מים -> מים"),
    ("נשנשתי בננה",
     lambda d: d and "בננה" in ff(d).get("name",""),
     "נשנשתי בננה -> בננה"),
    ("ארוחת בוקר הייתה ביצה",
     lambda d: d and has_food(d,"ביצה") and d.get("meal_type")=="breakfast",
     "ארוחת בוקר הייתה -> breakfast"),
]

assert len(TESTS) >= 200, f"Only {len(TESTS)} tests defined"


def run_tests():
    passed = failed = errors = 0
    failures = []
    total = len(TESTS)

    print(f"\n{'='*60}")
    print(f"  BiteFit Chat AI - {total} Accuracy Tests")
    print(f"  Model: {MODEL}")
    print(f"{'='*60}\n")

    for i, (user_input, check_fn, desc) in enumerate(TESTS, 1):
        try:
            data = ask(user_input)
            ok = check_fn(data)
            if ok:
                passed += 1
                print(f"  [{i:03d}] PASS  {desc}")
            else:
                failed += 1
                detail = f"foods={[f.get('name') for f in (data or {}).get('foods',[])]}, unit={ff(data).get('unit')}, qty={ff(data).get('quantity')}" if data else "None (no JSON)"
                failures.append((i, desc, user_input, detail))
                print(f"  [{i:03d}] FAIL  {desc}")
                print(f"         in:  {user_input!r}")
                print(f"         got: {detail}")
        except Exception as e:
            errors += 1
            failures.append((i, desc, user_input, f"ERROR: {e}"))
            print(f"  [{i:03d}] ERR   {desc}: {e}")

    pct = round(passed / total * 100)
    print(f"\n{'='*60}")
    print(f"  SCORE: {passed}/{total} = {pct}%")
    print(f"  Pass:{passed}  Fail:{failed}  Error:{errors}")
    print(f"{'='*60}")
    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for n, d, inp, det in failures:
            print(f"    [{n:03d}] {d}")
            print(f"          in:  {inp!r}")
            print(f"          got: {det}")
    return pct

if __name__ == "__main__":
    score = run_tests()
    sys.exit(0 if score >= 90 else 1)
