"""
Category Detection Service for Archon

This module provides auto-detection of change categories based on:
- File patterns (test files, config files, documentation)
- Commit message parsing (conventional commits)
- Content analysis
- Tool context

Returns suggestions with confidence scores and reasoning.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from ..config.logfire_config import get_logger

logger = get_logger(__name__)


# Valid change types
VALID_CHANGE_TYPES = [
    "feature", "bugfix", "refactor", "docs", "config", "test", "style", "perf", "deps", "ci"
]


@dataclass
class DetectionSignal:
    """A single signal from the detection process."""
    signal_type: str  # file_pattern, commit_prefix, keyword, content
    pattern: str
    confidence: float
    category: str


@dataclass
class CategorySuggestion:
    """Result of category detection."""
    category: str
    sub_category: str | None
    confidence: float
    reasoning: str
    signals: list[DetectionSignal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "category": self.category,
            "sub_category": self.sub_category,
            "confidence": round(self.confidence, 2),
            "reasoning": self.reasoning,
            "signals": [
                {
                    "signal_type": s.signal_type,
                    "pattern": s.pattern,
                    "confidence": round(s.confidence, 2),
                    "category": s.category,
                }
                for s in self.signals
            ],
        }


class CategoryDetectionService:
    """Service for auto-detecting change categories."""

    # File pattern rules: pattern -> (category, sub_category, confidence)
    FILE_PATTERNS = {
        # Test files
        r"test[_/].*\.py$": ("test", "backend", 0.9),
        r".*_test\.py$": ("test", "backend", 0.9),
        r".*\.test\.(ts|tsx|js|jsx)$": ("test", "frontend", 0.9),
        r".*\.spec\.(ts|tsx|js|jsx)$": ("test", "frontend", 0.9),
        r"__tests__/.*": ("test", None, 0.85),
        r"tests?/.*": ("test", None, 0.8),
        r"cypress/.*": ("test", "e2e", 0.9),
        r"playwright/.*": ("test", "e2e", 0.9),

        # Documentation
        r".*\.md$": ("docs", None, 0.7),
        r"docs?/.*": ("docs", None, 0.85),
        r"README.*": ("docs", None, 0.8),
        r"CHANGELOG.*": ("docs", None, 0.8),
        r"LICENSE.*": ("docs", None, 0.7),

        # Configuration
        r"\.env.*": ("config", "env", 0.9),
        r".*\.config\.(ts|js|json)$": ("config", None, 0.85),
        r"tsconfig.*\.json$": ("config", "typescript", 0.9),
        r"package\.json$": ("deps", None, 0.7),
        r"requirements.*\.txt$": ("deps", "python", 0.8),
        r"pyproject\.toml$": ("deps", "python", 0.7),
        r"poetry\.lock$": ("deps", "python", 0.9),
        r"package-lock\.json$": ("deps", "npm", 0.9),
        r"yarn\.lock$": ("deps", "yarn", 0.9),
        r"pnpm-lock\.yaml$": ("deps", "pnpm", 0.9),
        r"Dockerfile.*": ("config", "docker", 0.85),
        r"docker-compose.*\.ya?ml$": ("config", "docker", 0.85),
        r"\.gitlab-ci\.yml$": ("ci", "gitlab", 0.95),
        r"\.github/workflows/.*\.ya?ml$": ("ci", "github-actions", 0.95),
        r"Jenkinsfile.*": ("ci", "jenkins", 0.95),
        r"\.circleci/.*": ("ci", "circleci", 0.95),
        r"azure-pipelines.*\.ya?ml$": ("ci", "azure", 0.95),
        r"\.travis\.yml$": ("ci", "travis", 0.95),

        # Style files
        r"\.prettierrc.*": ("style", "prettier", 0.9),
        r"\.eslintrc.*": ("style", "eslint", 0.9),
        r"\.stylelintrc.*": ("style", "stylelint", 0.9),
        r"biome\.json$": ("style", "biome", 0.9),
        r"\.editorconfig$": ("style", None, 0.85),
        r"ruff\.toml$": ("style", "ruff", 0.9),

        # Frontend components
        r"src/components/.*\.(tsx|jsx)$": ("feature", "ui", 0.6),
        r"src/features/.*\.(tsx|jsx)$": ("feature", "ui", 0.6),

        # API routes
        r".*api.*routes?.*\.py$": ("feature", "api", 0.6),
        r".*api.*\.py$": ("feature", "api", 0.5),

        # Database/migrations
        r"migration.*\.sql$": ("config", "database", 0.8),
        r".*migrations?/.*": ("config", "database", 0.7),
    }

    # Conventional commit prefixes -> (category, confidence)
    COMMIT_PREFIXES = {
        "feat": ("feature", 0.95),
        "feature": ("feature", 0.95),
        "fix": ("bugfix", 0.95),
        "bugfix": ("bugfix", 0.95),
        "bug": ("bugfix", 0.9),
        "refactor": ("refactor", 0.95),
        "docs": ("docs", 0.95),
        "doc": ("docs", 0.9),
        "style": ("style", 0.95),
        "perf": ("perf", 0.95),
        "performance": ("perf", 0.9),
        "test": ("test", 0.95),
        "tests": ("test", 0.9),
        "chore": ("config", 0.7),
        "build": ("config", 0.8),
        "ci": ("ci", 0.95),
        "deps": ("deps", 0.9),
        "dependency": ("deps", 0.85),
        "dependencies": ("deps", 0.85),
    }

    # Keyword patterns in commit messages -> (category, confidence)
    COMMIT_KEYWORDS = {
        r"\bfix(es|ed|ing)?\b": ("bugfix", 0.7),
        r"\bbug\b": ("bugfix", 0.65),
        r"\bcrash(es|ed|ing)?\b": ("bugfix", 0.7),
        r"\berror\b": ("bugfix", 0.5),
        r"\badd(s|ed|ing)?\b": ("feature", 0.5),
        r"\bimplement(s|ed|ing)?\b": ("feature", 0.6),
        r"\bfeature\b": ("feature", 0.7),
        r"\brefactor(s|ed|ing)?\b": ("refactor", 0.8),
        r"\bclean(s|ed|ing)?\s*up\b": ("refactor", 0.7),
        r"\brestructur(e|es|ed|ing)\b": ("refactor", 0.7),
        r"\bdocument(s|ed|ing|ation)?\b": ("docs", 0.7),
        r"\bupdate(s|ed|ing)?\s*(readme|docs?)\b": ("docs", 0.8),
        r"\btest(s|ed|ing)?\b": ("test", 0.6),
        r"\bunit\s*test\b": ("test", 0.8),
        r"\boptimiz(e|es|ed|ing|ation)\b": ("perf", 0.75),
        r"\bperformance\b": ("perf", 0.7),
        r"\bspeed(s|ed|ing)?\s*up\b": ("perf", 0.75),
        r"\bformat(s|ted|ting)?\b": ("style", 0.6),
        r"\blint(s|ed|ing)?\b": ("style", 0.7),
        r"\bstyle\b": ("style", 0.6),
        r"\bdependenc(y|ies)\b": ("deps", 0.75),
        r"\bupgrade(s|d)?\b": ("deps", 0.5),
        r"\bpipeline\b": ("ci", 0.7),
        r"\bworkflow\b": ("ci", 0.6),
        r"\bci(/cd)?\b": ("ci", 0.8),
    }

    def __init__(self):
        """Initialize the service."""
        # Compile regex patterns for efficiency
        self._file_patterns = [
            (re.compile(pattern, re.IGNORECASE), category, sub_cat, conf)
            for pattern, (category, sub_cat, conf) in self.FILE_PATTERNS.items()
        ]
        self._commit_prefix_pattern = re.compile(
            r"^(" + "|".join(self.COMMIT_PREFIXES.keys()) + r")[\s:(\[]",
            re.IGNORECASE
        )
        self._keyword_patterns = [
            (re.compile(pattern, re.IGNORECASE), category, conf)
            for pattern, (category, conf) in self.COMMIT_KEYWORDS.items()
        ]

    def suggest_category(
        self,
        file_paths: list[str] | None = None,
        commit_message: str | None = None,
        tool_context: dict[str, Any] | None = None,
    ) -> CategorySuggestion:
        """
        Suggest a category based on available signals.

        Args:
            file_paths: List of affected file paths
            commit_message: The commit message or change summary
            tool_context: Optional context from the tool being used

        Returns:
            CategorySuggestion with category, confidence, and reasoning
        """
        signals: list[DetectionSignal] = []

        # Analyze file patterns
        if file_paths:
            file_signals = self._analyze_file_patterns(file_paths)
            signals.extend(file_signals)

        # Analyze commit message
        if commit_message:
            commit_signals = self._analyze_commit_message(commit_message)
            signals.extend(commit_signals)

        # Analyze tool context
        if tool_context:
            context_signals = self._analyze_tool_context(tool_context)
            signals.extend(context_signals)

        # Aggregate signals to determine best category
        return self._aggregate_signals(signals)

    def _analyze_file_patterns(self, file_paths: list[str]) -> list[DetectionSignal]:
        """Analyze file paths for category signals."""
        signals = []

        for file_path in file_paths:
            for pattern, category, sub_cat, confidence in self._file_patterns:
                if pattern.search(file_path):
                    signals.append(DetectionSignal(
                        signal_type="file_pattern",
                        pattern=pattern.pattern,
                        confidence=confidence,
                        category=category,
                    ))
                    # Store sub_category hint in the signal
                    if sub_cat:
                        signals[-1].pattern = f"{pattern.pattern} -> {sub_cat}"
                    break  # Only one pattern per file

        return signals

    def _analyze_commit_message(self, message: str) -> list[DetectionSignal]:
        """Analyze commit message for category signals."""
        signals = []
        message_lower = message.lower().strip()

        # Check for conventional commit prefix
        prefix_match = self._commit_prefix_pattern.match(message_lower)
        if prefix_match:
            prefix = prefix_match.group(1).lower()
            if prefix in self.COMMIT_PREFIXES:
                category, confidence = self.COMMIT_PREFIXES[prefix]
                signals.append(DetectionSignal(
                    signal_type="commit_prefix",
                    pattern=f"{prefix}:",
                    confidence=confidence,
                    category=category,
                ))

        # Check for keywords in message
        for pattern, category, confidence in self._keyword_patterns:
            if pattern.search(message_lower):
                signals.append(DetectionSignal(
                    signal_type="keyword",
                    pattern=pattern.pattern,
                    confidence=confidence,
                    category=category,
                ))

        return signals

    def _analyze_tool_context(self, context: dict[str, Any]) -> list[DetectionSignal]:
        """Analyze tool context for category signals."""
        signals = []

        # Check for explicit tool hints
        tool_name = context.get("tool_name", "").lower()
        if tool_name:
            tool_category_hints = {
                "test": ("test", 0.8),
                "lint": ("style", 0.8),
                "format": ("style", 0.7),
                "build": ("config", 0.6),
                "deploy": ("ci", 0.7),
            }
            for hint, (category, conf) in tool_category_hints.items():
                if hint in tool_name:
                    signals.append(DetectionSignal(
                        signal_type="tool_context",
                        pattern=f"tool:{tool_name}",
                        confidence=conf,
                        category=category,
                    ))
                    break

        # Check for explicit category hint in context
        if "suggested_category" in context:
            suggested = context["suggested_category"]
            if suggested in VALID_CHANGE_TYPES:
                signals.append(DetectionSignal(
                    signal_type="tool_context",
                    pattern="explicit_suggestion",
                    confidence=0.9,
                    category=suggested,
                ))

        return signals

    def _aggregate_signals(self, signals: list[DetectionSignal]) -> CategorySuggestion:
        """Aggregate all signals to determine the best category."""
        if not signals:
            return CategorySuggestion(
                category="feature",
                sub_category=None,
                confidence=0.3,
                reasoning="No signals detected, defaulting to 'feature'",
                signals=[],
            )

        # Calculate weighted score for each category
        category_scores: dict[str, float] = {}
        category_signals: dict[str, list[DetectionSignal]] = {}

        for signal in signals:
            cat = signal.category
            if cat not in category_scores:
                category_scores[cat] = 0.0
                category_signals[cat] = []
            category_scores[cat] += signal.confidence
            category_signals[cat].append(signal)

        # Find the category with highest score
        best_category = max(category_scores, key=lambda k: category_scores[k])
        best_signals = category_signals[best_category]

        # Calculate overall confidence (normalized)
        total_score = category_scores[best_category]
        num_signals = len(best_signals)
        # Confidence increases with more signals but caps at 0.95
        confidence = min(0.95, total_score / max(num_signals, 1) + (num_signals - 1) * 0.05)

        # Extract sub_category if present in file pattern signals
        sub_category = None
        for signal in best_signals:
            if signal.signal_type == "file_pattern" and " -> " in signal.pattern:
                sub_category = signal.pattern.split(" -> ")[1]
                break

        # Build reasoning
        reasoning_parts = []
        signal_types_seen = set()
        for signal in best_signals:
            if signal.signal_type not in signal_types_seen:
                signal_types_seen.add(signal.signal_type)
                if signal.signal_type == "commit_prefix":
                    reasoning_parts.append(f"Conventional commit prefix '{signal.pattern}' detected")
                elif signal.signal_type == "file_pattern":
                    reasoning_parts.append(f"File pattern matched: {signal.pattern.split(' -> ')[0]}")
                elif signal.signal_type == "keyword":
                    reasoning_parts.append("Keyword pattern matched")
                elif signal.signal_type == "tool_context":
                    reasoning_parts.append(f"Tool context signal: {signal.pattern}")

        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Based on signal analysis"

        return CategorySuggestion(
            category=best_category,
            sub_category=sub_category,
            confidence=confidence,
            reasoning=reasoning,
            signals=signals,
        )
