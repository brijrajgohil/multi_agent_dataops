from __future__ import annotations

from pydantic import BaseModel, Field


class GuardrailResult(BaseModel):
    ok: bool
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


def pass_guardrail(warnings: list[str] | None = None) -> GuardrailResult:
    return GuardrailResult(ok=True, warnings=warnings or [])


def fail_guardrail(reason: str) -> GuardrailResult:
    return GuardrailResult(ok=False, reason=reason)
