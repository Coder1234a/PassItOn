"""Thin wrapper around the Gemini API.

If there is no API key, or a call fails, every method returns None and the
agents fall back to simple rules. That way the demo never crashes on stage.
"""
import json
import os
import re

try:
    from google import genai
    from google.genai import types
except Exception:  # library not installed
    genai = None
    types = None


def _secret(name):
    """Read a setting from Streamlit secrets first, then environment variables."""
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


def _parse_json(text):
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None


class LLM:
    def __init__(self):
        self.model = _secret("GEMINI_MODEL") or "gemini-2.5-flash"
        self.client = None
        self.last_error = None
        self.calls = 0
        key = _secret("GEMINI_API_KEY")
        if key and genai is not None:
            try:
                self.client = genai.Client(api_key=key)
            except Exception as e:
                self.last_error = f"Could not start Gemini: {e}"[:300]
        elif not key:
            self.last_error = "No GEMINI_API_KEY set, so the app is running in offline (rule-based) mode."
        else:
            self.last_error = "google-genai is not installed."

    @property
    def online(self):
        return self.client is not None

    def _call(self, prompt, image_bytes=None, mime_type="image/jpeg", want_json=True):
        if not self.client:
            return None
        contents = [prompt]
        if image_bytes:
            contents = [types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt]
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json" if want_json else "text/plain",
        )
        try:
            self.calls += 1
            response = self.client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
            self.last_error = None
            return response.text
        except Exception as e:
            self.last_error = f"Gemini call failed: {e}"[:300]
            return None

    def json(self, prompt, image_bytes=None, mime_type="image/jpeg"):
        """Ask for a JSON object. Returns a dict, or None if anything goes wrong."""
        result = _parse_json(self._call(prompt, image_bytes, mime_type, want_json=True))
        return result if isinstance(result, dict) else None

    def text(self, prompt):
        """Ask for plain text. Returns a string, or None."""
        return self._call(prompt, want_json=False)
