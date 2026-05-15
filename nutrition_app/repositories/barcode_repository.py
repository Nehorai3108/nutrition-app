"""
barcode_repository.py — Community barcode database (Supabase)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from nutrition_app.db.supabase_client import get_supabase


@dataclass
class BarcodeEntry:
    barcode: str
    name_he: str
    calories: float
    protein: float
    carbs: float
    fat: float
    name_en: str = ""
    brand: str = ""
    image_url: str = ""
    fiber: float = 0.0
    serving_g: float = 100.0
    source: str = "community"
    added_by: str = ""
    verified: bool = False
    times_used: int = 0


class BarcodeRepository:

    def get(self, barcode: str) -> Optional[BarcodeEntry]:
        """מחזיר מוצר לפי ברקוד, או None אם לא קיים."""
        try:
            sb = get_supabase()
            resp = sb.table("barcode_db").select("*").eq("barcode", barcode).limit(1).execute()
            if resp.data:
                row = resp.data[0]
                # עדכן times_used
                try:
                    sb.table("barcode_db").update(
                        {"times_used": (row.get("times_used") or 0) + 1}
                    ).eq("barcode", barcode).execute()
                except Exception:
                    pass
                return BarcodeEntry(
                    barcode=row["barcode"],
                    name_he=row["name_he"],
                    name_en=row.get("name_en") or "",
                    brand=row.get("brand") or "",
                    image_url=row.get("image_url") or "",
                    calories=float(row.get("calories") or 0),
                    protein=float(row.get("protein") or 0),
                    carbs=float(row.get("carbs") or 0),
                    fat=float(row.get("fat") or 0),
                    fiber=float(row.get("fiber") or 0),
                    serving_g=float(row.get("serving_g") or 100),
                    source=row.get("source") or "community",
                    added_by=row.get("added_by") or "",
                    verified=bool(row.get("verified")),
                    times_used=int(row.get("times_used") or 0),
                )
        except Exception:
            pass
        return None

    def save(self, entry: BarcodeEntry) -> bool:
        """שומר מוצר חדש. מחזיר True אם הצליח."""
        try:
            sb = get_supabase()
            sb.table("barcode_db").upsert({
                "barcode":   entry.barcode,
                "name_he":   entry.name_he,
                "name_en":   entry.name_en,
                "brand":     entry.brand,
                "image_url": entry.image_url,
                "calories":  entry.calories,
                "protein":   entry.protein,
                "carbs":     entry.carbs,
                "fat":       entry.fat,
                "fiber":     entry.fiber,
                "serving_g": entry.serving_g,
                "source":    entry.source,
                "added_by":  entry.added_by,
            }, on_conflict="barcode").execute()
            return True
        except Exception:
            return False

    def search_by_name(self, name: str, limit: int = 5) -> list[BarcodeEntry]:
        """חיפוש לפי שם — שימושי לאוטו-קומפליט."""
        try:
            sb = get_supabase()
            resp = (
                sb.table("barcode_db")
                .select("*")
                .ilike("name_he", f"%{name}%")
                .limit(limit)
                .execute()
            )
            results = []
            for row in (resp.data or []):
                results.append(BarcodeEntry(
                    barcode=row["barcode"],
                    name_he=row["name_he"],
                    name_en=row.get("name_en") or "",
                    brand=row.get("brand") or "",
                    image_url=row.get("image_url") or "",
                    calories=float(row.get("calories") or 0),
                    protein=float(row.get("protein") or 0),
                    carbs=float(row.get("carbs") or 0),
                    fat=float(row.get("fat") or 0),
                    fiber=float(row.get("fiber") or 0),
                    serving_g=float(row.get("serving_g") or 100),
                    source=row.get("source") or "community",
                    added_by=row.get("added_by") or "",
                    verified=bool(row.get("verified")),
                    times_used=int(row.get("times_used") or 0),
                ))
            return results
        except Exception:
            return []
