# Agent Log — Recipe Scout

## Recipe Scout — 2026-04-23 12:37 UTC

- Candidates added: 4
- Gaps addressed: low_carb, keto, high_protein_low_carb
- Sources:
  - The Clean Eating Couple (https://thecleaneatingcouple.com/greek-chicken-cauliflower-rice-bowls/)
  - All Nutritious (https://allnutritious.com/egg-muffin-cups/)
  - A Saucy Kitchen (https://www.asaucykitchen.com/coconut-turmeric-chicken-thighs/)
  - High Protein Kitchen (https://highproteinkitchen.com/easy-tuna-salad-lettuce-wraps/)

### Gap Analysis Summary (actual DB scan — 270 recipes)
- **low-carb**: 4 recipes (1.5%) — CRITICAL gap
- **keto**: 0 recipes — CRITICAL gap
- **high-protein + low-carb combined**: ~3 recipes (1.1%) — CRITICAL gap
- **high-protein overall**: 25 recipes (9.3%) — medium gap

### Recipes rejected / skipped (already exist in DB)
- שקשוקה (recipe_001) — already exists
- מרק עדשים כתומות — already exists
- פלאפל בפיתה — already exists
- קציצות הודו (recipe_044) — already exists with breadcrumbs; low-carb version deferred to future run

### Notes
- GitHub and most recipe domains were initially blocked by network egress proxy; access restored via git + PAT
- `data/meta/recipe_gaps.json` created from live DB scan (first run; did not previously exist)
- `agent_io/` directory created (did not previously exist)
- All 4 candidates passed quality filters: metric quantities, 6-step instructions, 8-11 ingredients, standard kitchen equipment, reputable sources
- needs_usda_lookup: false for all 4 (macro data confirmed via search snippets from source sites)

## Recipe Scout — 2026-05-03 08:25 UTC — הכנסה ישירה ל-DB (בקשת משתמש)

- Recipes inserted directly to DB: 5
- Method: PRAGMA journal_mode=OFF (bypass Windows mount I/O issue)
- Recipes: שקשוקה, מרק עדשים אדומות, מחבת גרגרי חומוס ים-תיכונית, חציל צלוי עם טחינה, חזה עוף בתנור עם לימון ועשבי תיבול
- Notes: 4 מתוך 5 מסומנים needs_usda_lookup. שקשוקה כוללת מאקרו מאומת (207 קל', 14g חלבון לכל מנה).

