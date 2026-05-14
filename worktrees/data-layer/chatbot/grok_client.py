"""Thin wrapper around the OpenAI SDK configured for Groq (free Llama models)."""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_client() -> OpenAI:
    api_key = os.environ.get("GROQ_API_KEY", "")
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def chat_completion(client: OpenAI, messages: list, tools: list, stream: bool = True):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools or None,
        stream=stream,
    )
