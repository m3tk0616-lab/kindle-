"""Parse Claude / ChatGPT chat history to extract automation settings."""

import json
import os
import re

import anthropic


_SYSTEM_PROMPT = """\
You are a configuration extractor for a Kindle screenshot automation tool.
The user will paste a chat conversation (from Claude, ChatGPT, or similar).
Extract any automation settings mentioned in the conversation and return them
as a JSON object with these optional fields:

{
  "mode": "android" | "desktop",
  "interval": <seconds as float>,
  "total_pages": <integer, 0 = unlimited>,
  "save_dir": "<directory path string>",
  "device_serial": "<ADB serial string or empty>",
  "notes": "<any other relevant info as a short string>"
}

If a field is not mentioned, omit it.
Respond with ONLY the JSON object, no explanation."""


class PromptParser:
    async def extract_settings(self, chat_text: str, api_key: str = "") -> dict:
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            # Fallback: simple regex extraction without API
            return self._regex_fallback(chat_text)

        if not chat_text.strip():
            return self._regex_fallback(chat_text)

        client = anthropic.AsyncAnthropic(api_key=key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": chat_text}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    def _regex_fallback(self, text: str) -> dict:
        """Best-effort extraction without API."""
        settings: dict = {}
        text_lower = text.lower()

        if "android" in text_lower or "adb" in text_lower:
            settings["mode"] = "android"
        elif "desktop" in text_lower or "pc" in text_lower or "windows" in text_lower:
            settings["mode"] = "desktop"

        m = re.search(r"(\d+(?:\.\d+)?)\s*秒|(\d+(?:\.\d+)?)\s*sec(?:ond)?s?", text_lower)
        if m:
            settings["interval"] = float(m.group(1) or m.group(2))

        m = re.search(r"(\d+)\s*(?:ページ|pages?)", text_lower)
        if m:
            settings["total_pages"] = int(m.group(1))

        settings["notes"] = "API key not set — extracted via regex fallback"
        return settings
