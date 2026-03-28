import os
from dataclasses import dataclass

@dataclass
class ICPConfig:
    """Ideal Customer Profile — tune this to your niche."""
    min_budget: int = 2000
    preferred_stack: list = None
    positive_signals: list = None
    negative_signals: list = None

    def __post_init__(self):
        self.preferred_stack = ["React", "Next.js", "Python", "Django", "Node"]
        self.positive_signals = [
            "e-commerce", "SaaS", "startup", "custom development",
            "MVP", "web app", "API integration", "full-stack"
        ]
        self.negative_signals = [
            "WordPress", "template", "cheap", "budget", "simple website",
            "landing page only", "logo"
        ]

    def to_prompt_context(self) -> str:
        return f"""
        IDEAL CUSTOMER PROFILE:
        - Minimum budget: ${self.min_budget}
        - Preferred tech stack: {', '.join(self.preferred_stack)}
        - Positive signals (increase score): {', '.join(self.positive_signals)}
        - Negative signals (decrease score): {', '.join(self.negative_signals)}
        - Ideal: High-end custom web/app development, technical clients who
          understand scope, projects requiring senior-level expertise
        """

BARK_EMAIL = os.environ.get("BARK_EMAIL", "your@email.com")
BARK_PASSWORD = os.environ.get("BARK_PASSWORD", "yourpassword")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ICP = ICPConfig()