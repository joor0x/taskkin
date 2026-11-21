import re
from typing import Protocol

from app.moderation.schemas import ModerationResult, TaskModerationInput
from app.tasks.models import TaskCategory

# Allowed categories
ALLOWED_CATEGORIES = {cat.value for cat in TaskCategory}

# Moderation Rules configuration
MODERATION_RULES = {
    "prohibited_keywords": [
        "captcha",
        "bot evasion",
        "bypass cloudflare",
        "anti-bot",
        "create account",
        "verify account",
        "phone verification",
        "receive sms",
        "kyc",
        "identity verification",
        "passport",
        "national id",
        "id card",
        "driver license",
        "driver's license",
        "credentials",
        "password sharing",
        "fake review",
        "fake feedback",
        "social media manipulation",
        "fake likes",
        "fake followers",
        "buy reviews",
        "private property",
        "trespass",
        "surveillance",
        "stalk",
        "illegal",
        "drugs",
        "weapons",
        "escort",
        "adult content",
    ],
    "borderline_keywords": [
        "account",
        "phone",
        "verification",
        "review",
        "social",
        "private",
        "owner",
    ],
}


class ModerationService(Protocol):
    async def evaluate_task(
        self,
        task: TaskModerationInput,
    ) -> ModerationResult: ...


class TaskKinModerationService:
    def __init__(self) -> None:
        self.prohibited_keywords = MODERATION_RULES["prohibited_keywords"]
        self.borderline_keywords = MODERATION_RULES["borderline_keywords"]

    async def evaluate_task(
        self,
        task: TaskModerationInput,
    ) -> ModerationResult:
        matched_rules = []
        explanation_parts = []
        decision = "allow"
        risk_level = "low"

        # 1. Category check
        if task.category not in ALLOWED_CATEGORIES:
            decision = "reject"
            risk_level = "high"
            matched_rules.append("invalid_category")
            explanation_parts.append(f"Category '{task.category}' is not allowed.")

        # Analyze text content (title + description)
        content_to_analyze = f"{task.title} {task.description}".lower()

        # 2. Check for prohibited keywords (leads to automatic reject)
        for kw in self.prohibited_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", content_to_analyze):
                decision = "reject"
                risk_level = "high"
                matched_rules.append(f"prohibited_keyword_{kw.replace(' ', '_')}")
                explanation_parts.append(f"Matched prohibited keyword '{kw}'.")

        # 3. Check for borderline keywords (leads to manual review)
        if decision != "reject":
            for kw in self.borderline_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", content_to_analyze):
                    decision = "manual_review"
                    risk_level = "medium"
                    matched_rules.append(f"borderline_keyword_{kw}")
                    explanation_parts.append(
                        f"Matched borderline keyword '{kw}' requiring manual audit."
                    )

        # 4. Check URLs inside the description
        urls = re.findall(r"https?://[^\s]+", content_to_analyze)
        if urls and decision == "allow":
            decision = "manual_review"
            risk_level = "medium"
            matched_rules.append("contains_urls")
            explanation_parts.append(
                "Task contains external links; flagged for manual review."
            )

        # 5. Check if physical task has no country/city
        if task.location_mode == "physical" and (not task.country or not task.city):
            decision = "reject"
            risk_level = "high"
            matched_rules.append("missing_physical_location")
            explanation_parts.append("Physical tasks must specify country and city.")

        explanation = (
            " ".join(explanation_parts)
            if explanation_parts
            else "No prohibited patterns detected"
        )

        return ModerationResult(
            decision=decision,
            risk_level=risk_level,
            matched_rules=matched_rules,
            explanation=explanation,
        )
