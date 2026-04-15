#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3_audit_logs.py — צפייה בלוגים ודוחות ביקורת של המערכת
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui.components import inject_global_css, page_header, section_header

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="לוגים וביקורת",
    page_icon="📋",
    layout="wide",
)

# ── Design system ─────────────────────────────────────────────────────────
inject_global_css()

# ── Page header ───────────────────────────────────────────────────────────
page_header(
    "לוגים וביקורת מערכת",
    icon_name="logs",
    subtitle="צפייה בדוחות ביקורת וביומנים של המערכת",
)

# ── Constants ─────────────────────────────────────────────────────────────
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_agents")
AUDIT_DIR = os.path.join(STORAGE_DIR, "audit")
REPORTS_DIR = os.path.join(AUDIT_DIR, "director_reports")

os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Helper functions ──────────────────────────────────────────────────────

def load_json_file(filepath):
    """Load JSON file safely."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {"error": str(e)}

def load_text_file(filepath):
    """Load text file safely."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except IOError as e:
        return f"Error reading file: {e}"

def get_file_timestamp(filepath):
    """Get file modification time."""
    try:
        timestamp = os.path.getmtime(filepath)
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"

# ── Tab: Director Reports ─────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📊 דוחות סוכן מנהל", "📝 ביומנים", "🔍 מדדי מערכת"])

with tab1:
    section_header("דוחות סוכן מנהל", icon_name="chart")

    # List available director reports
    reports = []
    if os.path.exists(REPORTS_DIR):
        reports = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")], reverse=True)

    if not reports:
        st.info("אין דוחות זמינים עדיין.")
    else:
        # Select report to view
        selected_report = st.selectbox(
            "בחר דוח",
            options=reports,
            help="בחר דוח מנהל לצפייה בפרטיו"
        )

        if selected_report:
            report_path = os.path.join(REPORTS_DIR, selected_report)
            report_data = load_json_file(report_path)

            # Display metadata
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**📅 תאריך:** {get_file_timestamp(report_path)}")
            with col2:
                st.markdown(f"**📄 שם קובץ:** {selected_report}")

            st.divider()

            # Display report content
            if "error" in report_data:
                st.error(f"Error loading report: {report_data['error']}")
            else:
                # Show report structure
                if "summary" in report_data:
                    st.markdown("### סיכום")
                    st.markdown(report_data.get("summary", "No summary available"))

                if "identified_gaps" in report_data:
                    st.markdown("### פערים שזוהו")
                    for gap in report_data.get("identified_gaps", []):
                        st.markdown(f"- {gap}")

                if "recommended_tasks" in report_data:
                    st.markdown("### משימות מומלצות")
                    for task in report_data.get("recommended_tasks", []):
                        st.markdown(f"- {task}")

                # Show raw JSON
                with st.expander("📋 צפה בנתונים גולמיים"):
                    st.json(report_data)

        # Report statistics
        st.divider()
        st.markdown("### סטטיסטיקות דוחות")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("מספר דוחות", len(reports))
        with col2:
            if reports:
                latest = reports[0]
                st.metric("דוח אחרון", latest.replace(".json", "").replace("_", " "))
        with col3:
            if reports:
                # Calculate report age
                latest_path = os.path.join(REPORTS_DIR, reports[0])
                timestamp = os.path.getmtime(latest_path)
                age_hours = (datetime.now().timestamp() - timestamp) / 3600
                st.metric("גיל דוח אחרון", f"{age_hours:.1f} שעות")

# ── Tab: Logs ─────────────────────────────────────────────────────────────

with tab2:
    section_header("ביומנים", icon_name="journal")

    log_files = [
        ("ביומן מנהל", os.path.join(AUDIT_DIR, "director_log.txt")),
        ("ביומן דוקד", os.path.join(AUDIT_DIR, "critic_log.txt")),
        ("ביומן כללי", os.path.join(AUDIT_DIR, "audit.log")),
    ]

    selected_log = st.selectbox(
        "בחר ביומן",
        options=[name for name, _ in log_files],
    )

    # Get the file path for selected log
    log_path = next((path for name, path in log_files if name == selected_log), None)

    if log_path and os.path.exists(log_path):
        st.markdown(f"**📅 תאריך עדכון אחרון:** {get_file_timestamp(log_path)}")
        st.markdown(f"**📊 גודל קובץ:** {os.path.getsize(log_path) / 1024:.1f} KB")

        st.divider()

        # Display log content
        log_content = load_text_file(log_path)

        # Show with line wrapping and scrolling
        st.text_area(
            "תוכן הביומן",
            value=log_content,
            height=400,
            disabled=True,
            label_visibility="collapsed"
        )

        # Option to download log
        st.download_button(
            label="📥 הורד ביומן",
            data=log_content,
            file_name=f"{selected_log}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.info(f"ביומן '{selected_log}' לא קיים עדיין.")

# ── Tab: System Metrics ───────────────────────────────────────────────────

with tab3:
    section_header("מדדי מערכת", icon_name="gauge")

    # Load system metrics if available
    metrics_file = os.path.join(AUDIT_DIR, "growth_metrics.json")

    if os.path.exists(metrics_file):
        metrics = load_json_file(metrics_file)

        if "error" not in metrics:
            st.markdown("### מדדי צמיחה")

            # Display key metrics
            if "total_runs" in metrics:
                st.metric("סה״כ הרצות מערכת", metrics.get("total_runs", 0))

            if "success_rate" in metrics:
                st.metric("שיעור הצלחה", f"{metrics.get('success_rate', 0):.1f}%")

            if "avg_execution_time" in metrics:
                st.metric("זמן ביצוע ממוצע", f"{metrics.get('avg_execution_time', 0):.1f}s")

            st.divider()

            # Show all metrics
            with st.expander("📊 צפה בכל המדדים"):
                st.json(metrics)
        else:
            st.error(f"Error loading metrics: {metrics['error']}")
    else:
        st.info("קובץ המדדים לא קיים עדיין.")

# ── Summary section ───────────────────────────────────────────────────────

st.divider()
st.markdown("### ملخص الدليل العام")
st.info("""
- **דוחות מנהל** — ניתוח של פערים במערכת ומשימות מומלצות
- **ביומנים** — רישום פעילות מעבודת המנהל והדוקד
- **מדדי מערכת** — סטטיסטיקות ביצועים כללית
""")
