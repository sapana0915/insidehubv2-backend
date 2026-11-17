from __future__ import annotations

from dataclasses import dataclass, field

# List prices in USD per 1M tokens. Used for Cost(USD) in the log even on free tiers.
# Update when you change provider. Unknown models are logged with cost 0.0.
MODEL_PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-5-mini": (0.25, 2.00),
}


@dataclass
class TokenUsage:
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    steps: list[tuple[str, int, int]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        total = 0.0
        for model, inp, out in self.steps or [(self.model, self.input_tokens, self.output_tokens)]:
            prices = MODEL_PRICES_PER_MILLION.get(model)
            if not prices:
                continue
            in_price, out_price = prices
            total += (inp / 1_000_000) * in_price + (out / 1_000_000) * out_price
        return total

    @property
    def model_label(self) -> str:
        models = [model for model, _, _ in self.steps] if self.steps else ([self.model] if self.model else [])
        # Keep order, drop duplicates.
        seen: list[str] = []
        for model in models:
            if model and model not in seen:
                seen.append(model)
        return " + ".join(seen) if seen else "unknown"

    def add(self, other: TokenUsage) -> None:
        if other.model or other.input_tokens or other.output_tokens:
            self.steps.append((other.model, other.input_tokens, other.output_tokens))
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        if not self.model:
            self.model = other.model

    def from_response(self, model: str, usage) -> None:
        inp = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        out = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        self.model = model
        self.input_tokens = inp
        self.output_tokens = out
        self.steps = [(model, inp, out)]


def format_ai_log(
    *,
    user_id,
    status: str,
    category_name: str,
    seconds: float,
    usage: TokenUsage | None = None,
    reason: str | None = None,
    action: str = "AI generated",
) -> str:
    usage = usage or TokenUsage()
    lines = [
        f"{user_id}- {status} {category_name} {action}",
        f"\tTime taken: {seconds:.1f} seconds",
    ]
    if reason:
        lines.append(f"\tReason: {reason}")
    lines.append(
        "\tToken usage: "
        f"Model - {usage.model_label} | "
        f"Input - {usage.input_tokens} | "
        f"Output - {usage.output_tokens} | "
        f"Total - {usage.total_tokens} | "
        f"Cost(USD) - {usage.cost_usd:.6f}"
    )
    return "\n".join(lines)
