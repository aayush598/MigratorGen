"""
LLM-Powered Migration Suggestion Engine.

Supports:
- Suggesting missing migration rules from error messages
- Generating transformation drafts from natural language descriptions
- Explaining breaking changes in human-readable terms
- Suggesting migration paths for complex upgrades
- Analyzing codebases for migration patterns
"""

import os
import re
import json
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


LLMProvider = None
try:
    from anthropic import Anthropic
    LLMProvider = "anthropic"
except ImportError:
    try:
        import openai
        LLMProvider = "openai"
    except ImportError:
        pass


class SuggestionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MigrationSuggestion:
    rule_id: str
    change_type: str
    description: str
    confidence: SuggestionConfidence
    reasoning: str
    code_snippet: Optional[str] = None
    suggested_fix: Optional[str] = None
    impact: str = "unknown"
    effort: str = "unknown"


@dataclass
class BreakingChange:
    description: str
    severity: str
    affected_files: List[str] = field(default_factory=list)
    migration_strategy: str = ""
    ai_explanation: str = ""


class LLMSuggestionEngine:
    """
    Generates migration rules from error messages and code analysis.
    """

    SYSTEM_PROMPT = """You are an expert Python migration engineer. Given code analysis or error messages,
    generate precise migration rules in JSON format. Be conservative - only suggest changes you're confident about.

    Available change_types:
    - rename_function: Rename a function (requires old_name, new_name)
    - rename_class: Rename a class (requires old_name, new_name)
    - rename_attribute: Rename attribute access (requires old_name, new_name)
    - rename_import: Change import path (requires old_name, new_name, old_module, new_module)
    - add_argument: Add keyword arg (requires function_name, argument_name, default_value)
    - remove_argument: Remove arg (requires function_name, argument_name)
    - change_argument_default: Change default (requires function_name, argument_name, default_value)
    - move_to_module: Move symbol (requires old_name, source_module, target_module)
    - add_decorator: Add decorator (requires function_name, decorator_name)
    - remove_decorator: Remove decorator (requires function_name, decorator_name)
    - deprecate_function: Mark deprecated (requires old_name, replacement)

    Always include: id, change_type, version_introduced, description, safety.
    Safety levels: safe, review_required, risky.
    """

    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.provider = provider or LLMProvider or "mock"
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            if self.provider == "anthropic" or "ANTHROPIC" in str(type(self).__name__.upper()):
                try:
                    from anthropic import Anthropic
                    self._client = Anthropic(api_key=self.api_key)
                except ImportError:
                    pass
            elif self.provider == "openai" or "OPENAI" in str(type(self).__name__.upper()):
                try:
                    import openai
                    openai.api_key = self.api_key
                    self._client = openai
                except ImportError:
                    pass
        return self._client

    def suggest_from_error(
        self,
        error_message: str,
        code_context: str = "",
        file_path: str = "",
    ) -> List[MigrationSuggestion]:
        """Analyze an error message and suggest migration rules."""
        client = self._get_client()

        if client and hasattr(client, "messages"):
            user_prompt = f"""Error message:
{error_message}

File: {file_path}

Code context:
```python
{code_context}
```

Generate migration rules for this error. If this is a migration-related error, provide JSON rules.
Otherwise, explain why it's not migration-related."""

            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=self.SYSTEM_PROMPT,
                )
                return self._parse_suggestions(response.text)
            except Exception:
                pass

        return self._fallback_suggest_from_error(error_message, code_context)

    def _fallback_suggest_from_error(
        self, error_message: str, code_context: str
    ) -> List[MigrationSuggestion]:
        suggestions = []
        error_lower = error_message.lower()

        if "missing argument" in error_lower or "got an unexpected keyword argument" in error_lower:
            match = re.search(r"got an unexpected keyword argument '(\w+)'", error_message)
            if match:
                arg_name = match.group(1)
                suggestions.append(MigrationSuggestion(
                    rule_id=f"SUGGEST-{len(suggestions)+1:03d}",
                    change_type="add_argument",
                    description=f"Consider adding argument '{arg_name}' to match expected API",
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning="This error suggests a missing argument that may have been added in a newer version",
                    code_snippet=code_context,
                ))

        if "module '.*' has no attribute" in error_message or "has no attribute" in error_lower:
            match = re.search(r"has no attribute '(\w+)'", error_message)
            if match:
                attr_name = match.group(1)
                suggestions.append(MigrationSuggestion(
                    rule_id=f"SUGGEST-{len(suggestions)+1:03d}",
                    change_type="rename_attribute",
                    description=f"Attribute '{attr_name}' may have been renamed",
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning="Module attribute access error suggests a renamed attribute",
                    code_snippet=code_context,
                ))

        if "import error" in error_lower or "cannot import name" in error_lower:
            match = re.search(r"cannot import name '(\w+)'", error_message)
            if match:
                name = match.group(1)
                suggestions.append(MigrationSuggestion(
                    rule_id=f"SUGGEST-{len(suggestions)+1:03d}",
                    change_type="move_to_module",
                    description=f"Symbol '{name}' may have moved to a different module",
                    confidence=SuggestionConfidence.MEDIUM,
                    reasoning="Import error suggests the symbol has been relocated",
                    code_snippet=code_context,
                ))

        if "deprecated" in error_lower:
            match = re.search(r"'(\w+)' is deprecated", error_message)
            if match:
                name = match.group(1)
                suggestions.append(MigrationSuggestion(
                    rule_id=f"SUGGEST-{len(suggestions)+1:03d}",
                    change_type="deprecate_function",
                    description=f"Function '{name}' is deprecated",
                    confidence=SuggestionConfidence.HIGH,
                    reasoning="Deprecation warning detected directly from error",
                    code_snippet=code_context,
                ))

        return suggestions

    def generate_from_description(
        self, natural_description: str, library: str = "unknown"
    ) -> List[Dict[str, Any]]:
        """Convert natural language description to migration rules."""
        client = self._get_client()

        if client and hasattr(client, "messages"):
            user_prompt = f"""Convert this natural language migration description into structured JSON rules:

Library: {library}
Description:
{natural_description}

Output format:
{{
  "rules": [
    {{
      "id": "AUTO-001",
      "change_type": "...",
      "version_introduced": "X.Y.Z",
      "description": "...",
      ... (specific fields based on change_type)
    }}
  ]
}}"""

            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=self.SYSTEM_PROMPT,
                )
                return self._parse_rules_json(response.text)
            except Exception:
                pass

        return []

    def explain_breaking_changes(
        self, rules: List[Dict], code_before: str = "", code_after: str = ""
    ) -> List[BreakingChange]:
        """Explain breaking changes in human-readable terms."""
        client = self._get_client()

        if client and hasattr(client, "messages"):
            rules_json = json.dumps(rules, indent=2)
            user_prompt = f"""Explain these migration rules as breaking changes for library maintainers:

Rules:
{rules_json}

Code before:
```python
{code_before}
```

Code after:
```python
{code_after}
```

For each breaking change, provide:
1. Plain English explanation
2. Severity (high/medium/low)
3. Migration strategy
4. Effort estimate (minutes/hours/days)"""

            try:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return self._parse_explanations(response.text)
            except Exception:
                pass

        return self._fallback_explain(rules)

    def _fallback_explain(self, rules: List[Dict]) -> List[BreakingChange]:
        explanations = []
        for r in rules:
            ct = r.get("change_type", "unknown")
            desc = r.get("description", "")
            safety = r.get("safety", "review_required")
            old_name = r.get("old_name", "")
            new_name = r.get("new_name", "")

            if ct == "rename_function":
                explanations.append(BreakingChange(
                    description=f"Function '{old_name}' renamed to '{new_name}'. All call sites must be updated.",
                    severity="high" if safety == "risky" else "medium",
                    migration_strategy=f"Replace all occurrences of '{old_name}' with '{new_name}'",
                    ai_explanation=f"This is a function rename affecting all usages.",
                ))
            elif ct == "remove_argument":
                explanations.append(BreakingChange(
                    description=f"Argument '{r.get('argument_name', '')}' removed from '{r.get('function_name', '')}()'. Call sites using this argument will fail.",
                    severity="high",
                    migration_strategy=f"Remove the '{r.get('argument_name')}' argument from all calls to '{r.get('function_name')}()'",
                    ai_explanation="Removing arguments is a breaking change that requires updating all call sites.",
                ))
            elif ct == "move_to_module":
                explanations.append(BreakingChange(
                    description=f"Symbol moved from '{r.get('source_module')}' to '{r.get('target_module')}'",
                    severity="medium",
                    migration_strategy=f"Update import statements from '{r.get('source_module')}' to '{r.get('target_module')}'",
                    ai_explanation="Module relocation requires import path updates.",
                ))
            elif ct == "rename_attribute":
                explanations.append(BreakingChange(
                    description=f"Attribute '{old_name}' renamed to '{new_name}'",
                    severity="medium",
                    migration_strategy=f"Replace all '.{old_name}' accesses with '.{new_name}'",
                    ai_explanation="Attribute renaming affects all dot-access patterns.",
                ))

        return explanations

    def suggest_migration_path(
        self,
        library: str,
        current_version: str,
        target_version: str,
        changelog_summary: str = "",
    ) -> Dict[str, Any]:
        """Suggest the optimal migration path with effort estimates."""
        return {
            "library": library,
            "from_version": current_version,
            "to_version": target_version,
            "suggested_approach": "incremental",
            "major_steps": [
                {
                    "from": current_version,
                    "to": self._next_major(current_version),
                    "effort": "moderate",
                    "risk": "medium",
                }
            ],
            "estimated_effort": "1-4 hours",
            "testing_required": True,
            "rollback_plan": "revert to previous version",
        }

    def _next_major(self, version: str) -> str:
        parts = version.split(".")
        if len(parts) >= 2:
            parts[1] = str(int(parts[1]) + 1)
            return ".".join(parts)
        return version

    def _parse_suggestions(self, text: str) -> List[MigrationSuggestion]:
        suggestions = []
        try:
            data = json.loads(text)
            for r in data.get("rules", data.get("suggestions", [])):
                suggestions.append(MigrationSuggestion(
                    rule_id=r.get("id", "UNKNOWN"),
                    change_type=r.get("change_type", "unknown"),
                    description=r.get("description", ""),
                    confidence=SuggestionConfidence(r.get("confidence", "medium")),
                    reasoning=r.get("reasoning", "Generated suggestion"),
                    code_snippet=r.get("code_snippet"),
                    suggested_fix=r.get("suggested_fix"),
                ))
        except json.JSONDecodeError:
            pass
        return suggestions

    def _parse_rules_json(self, text: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(text)
            return data.get("rules", [])
        except json.JSONDecodeError:
            return []

    def _parse_explanations(self, text: str) -> List[BreakingChange]:
        changes = []
        for line in text.splitlines():
            if ":" in line:
                changes.append(BreakingChange(
                    description=line.strip(),
                    severity="medium",
                    migration_strategy="See full explanation above",
                    ai_explanation=text,
                ))
        return changes if changes else []


def suggest_migrations(
    error_message: str = "",
    code_context: str = "",
    natural_description: str = "",
    library: str = "unknown",
    api_key: Optional[str] = None,
) -> List[MigrationSuggestion]:
    """Convenience function for quick migration suggestions."""
    engine = LLMSuggestionEngine(api_key=api_key)

    if error_message:
        return engine.suggest_from_error(error_message, code_context)
    elif natural_description:
        return engine.generate_from_description(natural_description, library)
    return []


def explain_changes(
    rules: List[Dict],
    api_key: Optional[str] = None,
) -> List[BreakingChange]:
    """Explain migration rules as breaking changes."""
    engine = LLMSuggestionEngine(api_key=api_key)
    return engine.explain_breaking_changes(rules)