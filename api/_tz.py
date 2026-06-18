"""
זמן מקומי (ישראל) לשרת ה-API.

השרת מתארח ב-Render עם שעון UTC, אז datetime.now()/date.today() החזירו
זמן שגוי (3 שעות אחורה). כאן מרכזים את הזמן המקומי כדי שחותמות הזמן של
יומן אוכל / מים / אימונים ישקפו את שעון ישראל. בלתי תלוי במשתנה TZ.
"""
from datetime import datetime, date
from zoneinfo import ZoneInfo

IL_TZ = ZoneInfo("Asia/Jerusalem")


def now_il() -> datetime:
    """datetime נוכחי בשעון ישראל (timezone-aware)."""
    return datetime.now(IL_TZ)


def now_il_iso() -> str:
    """חותמת זמן ISO בשעון ישראל, ללא tzinfo (תואם לפורמט הקיים)."""
    return now_il().replace(tzinfo=None).isoformat()


def today_il() -> date:
    """התאריך של היום בשעון ישראל."""
    return now_il().date()
