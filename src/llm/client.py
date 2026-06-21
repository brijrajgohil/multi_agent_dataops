from __future__ import annotations

import json
import re
from typing import Any

from src.config import get_settings


class LlamaClient:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.llama_model
        self.base_url = base_url or settings.llama_base_url
        self.timeout_seconds = timeout_seconds or settings.llama_timeout_seconds

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")

        try:
            import ollama
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "ollama is not installed. Run `python -m pip install -r requirements.txt`."
            ) from exc

        client = ollama.Client(host=self.base_url, timeout=self.timeout_seconds)
        try:
            response = client.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                options={"temperature": 0},
            )
        except Exception as exc:
            raise RuntimeError(
                "Local Llama runtime is unavailable. Start Ollama with `ollama serve` "
                f"and ensure model `{self.model}` is pulled."
            ) from exc

        text = response.get("response", "")
        return parse_json_response(text)


class MockLlamaClient:
    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = responses or []
        self.prompts: list[str] = []

    def generate_json(self, prompt: str) -> dict[str, Any]:
        if not prompt.strip():
            raise ValueError("prompt cannot be empty")

        self.prompts.append(prompt)
        if self.responses:
            return self.responses.pop(0)
        return {"ok": True}


def parse_json_response(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        raise ValueError("Llama returned an empty response")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
        if match is None:
            raise ValueError("Llama response did not contain a JSON object") from None
        payload = json.loads(match.group(0))

    if not isinstance(payload, dict):
        raise ValueError("Llama response must be a JSON object")
    return payload
