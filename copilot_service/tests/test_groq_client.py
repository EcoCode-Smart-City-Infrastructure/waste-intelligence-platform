"""Tests for the Groq client (for-now provider).

Uses a fixture key only — no live Groq call is made, and no real key
is present in this file.
"""

import pytest

from ..config.settings import get_settings
from ..utils.groq_client import GroqClient, GroqError, get_groq_client


def test_groq_client_defaults():
    settings = get_settings()
    client = GroqClient(api_key="test-fixture-key")
    assert client.base_url == settings.groq_base_url
    assert client._get_headers()["Authorization"] == "Bearer test-fixture-key"


def test_groq_client_is_openai_compatible():
    # Groq accepts the same chat-completions payload shape as OpenRouter.
    client = GroqClient(api_key="test-fixture-key")
    assert client.base_url.endswith("/openai/v1")


def test_get_groq_client_singleton():
    assert get_groq_client() is get_groq_client()
