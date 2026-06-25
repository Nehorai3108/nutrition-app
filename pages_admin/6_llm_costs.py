#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
6_llm_costs.py — עלויות וטוקנים של ה-LLM לכל משתמש (לתמחור המוצר).

קורא מטבלת llm_usage (Supabase בענן / SQLite בפיתוח). מציג סך עלות וטוקנים
לפי פיצ'ר וספק, ממוצע לכל משתמש ליום, סדרה יומית, וייצוא CSV.
"""
import os
import sys
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="עלויות LLM", page_icon="💸", layout="wide")

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "storage", "nutrition.db")

_COLS = ["id", "created_at", "user_id", "is_demo", "device_label", "provider",
         "model", "feature", "input_tokens", "output_tokens", "total_tokens",
         "cached_input_tokens", "cost_usd", "latency_ms", "success", "error"]


@st.cache_data(ttl=60)
def load_rows() -> pd.DataFrame:
    """Load all llm_usage rows from Supabase (prod) or SQLite (dev)."""
    rows = []
    if os.environ.get("SUPABASE_URL"):
        try:
            from nutrition_app.db.supabase_client import get_supabase
            data = get_supabase().table("llm_usage").select("*").limit(100000).execute().data
            rows = data or []
        except Exception as e:
            st.warning(f"לא ניתן לקרוא מ-Supabase: {e}")
    if not rows and os.path.exists(_DB_PATH):
        try:
            with closing(sqlite3.connect(_DB_PATH)) as c:
                c.row_factory = sqlite3.Row
                rows = [dict(r) for r in c.execute("SELECT * FROM llm_usage").fetchall()]
        except Exception:
            pass
    df = pd.DataFrame(rows, columns=_COLS) if rows else pd.DataFrame(columns=_COLS)
    if not df.empty:
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
        df["date"] = df["created_at"].dt.date
        for c in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "cost_usd"):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        df["is_demo"] = df["is_demo"].astype(bool)
    return df


st.title("💸 עלויות וטוקנים של ה-LLM")
st.caption("מדידת עלות לכל משתמש — לקביעת תמחור. נתונים מטבלת llm_usage.")

df = load_rows()
if df.empty:
    st.info("אין עדיין נתונים. ודא שהרצת את db/migrations/llm_usage.sql ושנעשו קריאות AI.")
    st.stop()

# ── filters ──────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 1, 1])
min_d = df["date"].min()
max_d = df["date"].max()
with c1:
    date_range = st.date_input("טווח תאריכים", value=(min_d, max_d), min_value=min_d, max_value=max_d)
with c2:
    demo_filter = st.selectbox("משתמשים", ["הכל", "דמו בלבד", "ללא דמו"])
with c3:
    st.metric("שורות", len(df))

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start, end = date_range
    df = df[(df["date"] >= start) & (df["date"] <= end)]
if demo_filter == "דמו בלבד":
    df = df[df["is_demo"]]
elif demo_filter == "ללא דמו":
    df = df[~df["is_demo"]]

if df.empty:
    st.warning("אין נתונים בטווח שנבחר.")
    st.stop()

# ── headline metrics ─────────────────────────────────────────────────────────
n_users = df["user_id"].nunique()
n_days = max(1, df["date"].nunique())
total_cost = df["cost_usd"].sum()
total_tokens = df["total_tokens"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("עלות כוללת", f"${total_cost:,.4f}")
m2.metric("סך טוקנים", f"{int(total_tokens):,}")
m3.metric("משתמשים", n_users)
m4.metric("עלות ממוצעת למשתמש/יום", f"${total_cost / n_users / n_days:,.5f}")

st.divider()

# ── by feature ───────────────────────────────────────────────────────────────
st.subheader("לפי פיצ'ר")
by_feat = (df.groupby("feature")
           .agg(cost_usd=("cost_usd", "sum"), total_tokens=("total_tokens", "sum"),
                calls=("id", "count"))
           .sort_values("cost_usd", ascending=False).reset_index())
st.dataframe(by_feat, use_container_width=True, hide_index=True)
st.bar_chart(by_feat.set_index("feature")["cost_usd"])

# ── by provider / model ──────────────────────────────────────────────────────
st.subheader("לפי ספק / מודל")
by_model = (df.groupby(["provider", "model"])
            .agg(cost_usd=("cost_usd", "sum"), input_tokens=("input_tokens", "sum"),
                 output_tokens=("output_tokens", "sum"), calls=("id", "count"))
            .sort_values("cost_usd", ascending=False).reset_index())
st.dataframe(by_model, use_container_width=True, hide_index=True)

# ── per-user totals + per-day averages ───────────────────────────────────────
st.subheader("לכל משתמש")
def _user_stats(g):
    days = max(1, g["date"].nunique())
    return pd.Series({
        "cost_usd": g["cost_usd"].sum(),
        "total_tokens": int(g["total_tokens"].sum()),
        "calls": len(g),
        "active_days": days,
        "cost_per_day": g["cost_usd"].sum() / days,
        "tokens_per_day": int(g["total_tokens"].sum() / days),
        "is_demo": bool(g["is_demo"].any()),
    })
per_user = df.groupby("user_id").apply(_user_stats).sort_values("cost_usd", ascending=False).reset_index()
st.dataframe(per_user, use_container_width=True, hide_index=True)

# ── daily time series ────────────────────────────────────────────────────────
st.subheader("סדרה יומית")
daily = (df.groupby("date")
         .agg(cost_usd=("cost_usd", "sum"), total_tokens=("total_tokens", "sum"),
              calls=("id", "count"))
         .reset_index())
st.line_chart(daily.set_index("date")[["cost_usd"]])
st.line_chart(daily.set_index("date")[["total_tokens"]])

# ── raw export ───────────────────────────────────────────────────────────────
st.subheader("ייצוא נתונים גולמיים")
csv = df.drop(columns=["date"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ הורד CSV", data=csv,
                   file_name=f"llm_usage_{datetime.now(timezone.utc):%Y%m%d}.csv",
                   mime="text/csv")
