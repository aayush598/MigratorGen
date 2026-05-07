"""
LLM Integration - Uses NVIDIA/Gemma model to:
1. Parse unstructured markdown changelogs into structured MigrationRule objects
2. Handle CUSTOM_TRANSFORM rules that can't be expressed as predefined patterns
3. Suggest which transformer function to call based on changelog text
"""

import json
import re
from typing import List, Optional
from openai import OpenAI
from .changelog_parser import MigrationRule, ChangeType, VersionChangelog


SYSTEM_PROMPT = """You are an expert Python library migration analyzer.
Your job is to analyze changelog entries and extract structured migration rules.

For each breaking change in the changelog, output a JSON array of migration rule objects.
Each rule must have:
- "change_type": one of [
    "rename_function", "rename_class", "rename_attribute", "rename_import",
    "add_argument", "remove_argument", "change_argument_default", "reorder_arguments",
    "deprecate_function", "remove_function", "remove_class", "replace_with_property",
    "move_to_module", "add_decorator", "remove_decorator", "custom_transform"
  ]
- "version_introduced": the version string
- "description": human-readable description

Optional fields based on change_type:
- "old_name": original name (for renames, deprecations)
- "new_name": new name (for renames)
- "function_name": function/method being changed (for argument changes)
- "argument_name": argument name
- "new_argument_name": new argument name (for rename_argument)
- "default_value": Python expression as string (for add_argument, change_argument_default)
- "old_module": old import module path
- "new_module": new import module path
- "replacement": what to use instead (for deprecations)
- "source_module": original module (for move_to_module)
- "target_module": destination module (for move_to_module)
- "decorator_name": decorator to add/remove
- "new_order": list of param names in new order (for reorder_arguments)

IMPORTANT:
- Only extract BREAKING CHANGES and deprecations, not new features.
- Output ONLY the JSON array, no markdown, no explanation.
- If no migration rules are needed, output: []
"""


class LLMParser:
    """
    Uses the NVIDIA-hosted Gemma model to parse markdown changelogs
    and extract structured MigrationRule objects.
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.client = OpenAI(
            base_url=base_url or "https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
        self.model = "google/gemma-2-2b-it"

    def _call_llm(self, prompt: str, stream: bool = False) -> str:
        """Make a call to the LLM and return the full text response."""
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            top_p=0.7,
            max_tokens=2048,
            stream=True,
        )

        result = []
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                result.append(chunk.choices[0].delta.content)

        return "".join(result)

    def parse_changelog_entry(
        self, version: str, changelog_text: str
    ) -> List[MigrationRule]:
        """
        Parse a single version's changelog text into MigrationRule objects.
        Returns a list of rules extracted by the LLM.
        """
        prompt = f"""
Version: {version}

Changelog entry:
{changelog_text}

Extract all migration rules as a JSON array.
"""
        response = self._call_llm(prompt)
        return self._parse_llm_response(response, version)

    def detect_new_rules(
        self,
        old_changelogs: List[VersionChangelog],
        new_changelogs: List[VersionChangelog],
    ) -> List[VersionChangelog]:
        """
        Given old and new changelogs, identify newly added versions
        and use LLM to extract migration rules from their raw notes.
        """
        old_versions = {vc.version for vc in old_changelogs}
        new_entries = [vc for vc in new_changelogs if vc.version not in old_versions]

        enriched = []
        for vc in new_entries:
            if vc.raw_notes and not vc.rules:
                print(f"  [LLM] Parsing changelog for version {vc.version}...")
                rules = self.parse_changelog_entry(vc.version, vc.raw_notes)
                vc.rules = rules
                print(f"  [LLM] Extracted {len(rules)} rule(s) for v{vc.version}")
            enriched.append(vc)

        return enriched

    def generate_custom_transform(
        self, rule: MigrationRule, source_code: str
    ) -> Optional[str]:
        """
        For CUSTOM_TRANSFORM rules, ask the LLM to rewrite the specific code.
        Returns the transformed code or None if no change needed.
        """
        prompt = f"""
You are rewriting Python source code to migrate it to a new library version.

Migration rule: {rule.description}

Source code:
```python
{source_code}
```

Apply the migration. Output ONLY the migrated Python code, nothing else.
If no changes are needed, output the original code unchanged.
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            top_p=0.7,
            max_tokens=4096,
            stream=True,
        )

        result = []
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                result.append(chunk.choices[0].delta.content)

        text = "".join(result)
        # Strip markdown code fences if present
        text = re.sub(r"```python\n?", "", text)
        text = re.sub(r"```\n?", "", text)
        return text.strip()

    def suggest_change_type(self, description: str) -> str:
        """
        Given a description of a change, suggest the most appropriate ChangeType.
        Useful for interactive rule building.
        """
        prompt = f"""
Given this breaking change description:
"{description}"

Which change_type is most appropriate? Choose from:
rename_function, rename_class, rename_attribute, rename_import,
add_argument, remove_argument, change_argument_default, reorder_arguments,
deprecate_function, remove_function, remove_class, replace_with_property,
move_to_module, add_decorator, remove_decorator, custom_transform

Output ONLY the change_type string.
"""
        response = self._call_llm(prompt)
        return response.strip().lower()

    def _parse_llm_response(
        self, response: str, version: str
    ) -> List[MigrationRule]:
        """Parse LLM JSON response into MigrationRule objects."""
        # Find JSON array in response
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if not json_match:
            print(f"  [LLM] No JSON found in response for v{version}")
            return []

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            print(f"  [LLM] JSON parse error for v{version}: {e}")
            return []

        rules = []
        for item in data:
            try:
                if "version_introduced" not in item:
                    item["version_introduced"] = version
                rule = MigrationRule.from_dict(item)
                rules.append(rule)
            except Exception as e:
                print(f"  [LLM] Skipping invalid rule: {e}")

        return rules

    def enrich_rules_with_context(
        self, rules: List[MigrationRule], changelog_text: str
    ) -> List[MigrationRule]:
        """
        Use LLM to fill in missing details for rules that were parsed
        from structured JSON but have incomplete information.
        """
        incomplete = [r for r in rules if r.change_type == ChangeType.CUSTOM_TRANSFORM]
        if not incomplete:
            return rules

        prompt = f"""
These migration rules were extracted but need more details:
{json.dumps([r.to_dict() for r in incomplete], indent=2)}

From this changelog context:
{changelog_text}

For each rule, add any missing fields. Output the same JSON array with enriched data.
"""
        response = self._call_llm(prompt)
        enriched_data = self._parse_llm_response(response, "")

        # Replace incomplete rules with enriched versions
        enriched_map = {r.description: r for r in enriched_data}
        result = []
        for rule in rules:
            if rule in incomplete and rule.description in enriched_map:
                result.append(enriched_map[rule.description])
            else:
                result.append(rule)

        return result