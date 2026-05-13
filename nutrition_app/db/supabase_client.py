"""
supabase_client.py — Singleton Supabase client for BiteFit.
Cached with st.cache_resource so it's created once per Streamlit session.
"""
from __future__ import annotations

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    url  = st.secrets["SUPABASE_URL"]
    key  = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


def is_supabase_configured() -> bool:
    """Auth is disabled — app runs in single-user local mode."""
    return False
