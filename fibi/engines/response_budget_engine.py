"""Response time budgets for Fibi."""

from __future__ import annotations

import time

from fibi.engines.types import ResponseBudget

BUDGETS_MS = {
    "greeting": 300,
    "local_reaction": 500,
    "command": 1000,
    "simple_chat": 2000,
    "complex_chat": 7000,
    "model_call": 8000,
}

BUDGET_FALLBACKS = [
    "model brain is asleep.",
    "local mode. explainy brain unavailable.",
    "Ollama is unavailable.",
    "i can do tiny local things right now.",
]


class ResponseBudgetEngine:
    def start(self, category: str) -> tuple[ResponseBudget, float]:
        return ResponseBudget(category, BUDGETS_MS.get(category, 2000)), time.perf_counter()

    @staticmethod
    def update(budget: ResponseBudget, started_at: float) -> ResponseBudget:
        budget.elapsed_ms = (time.perf_counter() - started_at) * 1000
        budget.budget_exceeded = budget.elapsed_ms > budget.budget_ms
        return budget

    @staticmethod
    def exceeded(started_at: float, category: str) -> bool:
        return (time.perf_counter() - started_at) * 1000 > BUDGETS_MS.get(category, 2000)
