"""
Feature flags — module-level constants that document intentional product defaults.
Import and check before building gamification or notification UI.
"""

FF_CALM_MODE_DEFAULT = True   # all gamification is opt-in; streaks/notifications off by default
FF_PROTEIN_FIRST_WIDGET = False  # protein-of-the-day widget above calorie ring (not yet shipped)
FF_GLP1_AWARE_TARGETS = False    # GLP-1 medication protein-floor adjustment (not yet shipped)
