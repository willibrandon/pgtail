"""Context-aware ghost text suggester for tail mode commands.

Combines structural completions (command names, arguments, flags) with
history prefix fallback for ghost text suggestions in TailInput.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from textual.suggester import Suggester

from pgtail_py.tail_history import TailCommandHistory

if TYPE_CHECKING:
    from pgtail_py.tail_completion_data import CompletionSpec

# Regex for detecting --flag=value tokens and partials
_FLAG_EQ_RE = re.compile(r"^(--[A-Za-z][\w-]*)=(.*)")


class TailCommandSuggester(Suggester):
    """Context-aware ghost text suggester combining structural and history completions.

    Extends Textual's Suggester with use_cache=False (FR-020) and case_sensitive=True
    (mixed case handling per FR-018).
    """

    def __init__(
        self,
        history: TailCommandHistory,
        completion_data: dict[str, CompletionSpec],
        dynamic_sources: dict[str, Callable[[], list[str]]],
    ) -> None:
        """Initialize suggester.

        Args:
            history: Command history for prefix search fallback (FR-016).
            completion_data: Per-command completion specs.
            dynamic_sources: Named callables returning dynamic value lists (FR-015).
        """
        super().__init__(use_cache=False, case_sensitive=True)
        self._history = history
        self._completion_data = completion_data
        self._dynamic_sources = dynamic_sources

    def _parse_input(self, value: str) -> tuple[str | None, list[str], str]:
        """Parse input into (command, completed_args, partial_word).

        Uses str.split() semantics (FR-021). Handles trailing whitespace detection.

        Returns:
            - command: first completed token (casefolded), or None if still typing command.
              command=None means "the user is still typing the first word" (no complete
              tokens yet). It does NOT mean "command not recognized" -- unknown commands
              have command set to the casefolded first token and receive no structural
              suggestions (fall through to history).
            - completed_args: list of completed argument tokens (after command)
            - partial: the partial word being typed (may be empty string)
        """
        if not value or value.isspace():
            return (None, [], "")

        tokens = value.split()
        trailing_space = value[-1].isspace()

        if trailing_space:
            # All tokens are complete
            command = tokens[0].lower() if tokens else None
            completed_args = tokens[1:] if len(tokens) > 1 else []
            return (command, completed_args, "")

        if len(tokens) == 1:
            # Still typing the first (and only) word -- no command identified yet
            return (None, [], tokens[0])

        # Multiple tokens, last one is the partial
        command = tokens[0].lower()
        completed_args = tokens[1:-1]
        partial = tokens[-1]
        return (command, completed_args, partial)

    def _match_values(
        self,
        values: list[str],
        partial: str,
        case_sensitive: bool,
    ) -> str | None:
        """Find first value matching partial prefix.

        Args:
            values: Sorted list of candidate values.
            partial: Prefix to match against.
            case_sensitive: Whether to use case-sensitive matching.

        Returns:
            First matching value (original casing), or None.
        """
        for v in values:
            if case_sensitive:
                if v.startswith(partial):
                    return v
            else:
                if v.lower().startswith(partial.lower()):
                    return v
        return None

    def _resolve_spec_values(
        self,
        spec: CompletionSpec,
        partial: str,
    ) -> str | None:
        """Resolve values from a CompletionSpec (static or dynamic).

        Static values use case-insensitive matching. Dynamic sources use
        case-sensitive matching (FR-018).

        Args:
            spec: CompletionSpec defining the value source.
            partial: Prefix to match against.

        Returns:
            Matched value (full value, not suffix), or None.
        """
        if spec.static_values is not None:
            return self._match_values(spec.static_values, partial, case_sensitive=False)
        if spec.dynamic_source is not None:
            source_fn = self._dynamic_sources.get(spec.dynamic_source)
            if source_fn is not None:
                values = source_fn()
                return self._match_values(values, partial, case_sensitive=True)
        return None

    def _resolve_structural(
        self,
        command: str,
        completed_args: list[str],
        partial: str,
    ) -> str | None:
        """Resolve structural completion for command arguments.

        Applies composition rules (flag vs positional vs subcommand resolution)
        and the flag scanning algorithm (FR-014).

        Args:
            command: Command name (already casefolded).
            completed_args: List of completed argument tokens after the command.
            partial: The partial word being typed (may be empty string).

        Returns:
            Suggested value (full value, not just suffix), or None.
        """
        spec = self._completion_data.get(command)
        if spec is None:
            return None

        if spec.no_args:
            return None

        # --- Subcommand resolution ---
        if spec.subcommands:
            if completed_args:
                # First completed arg might be a subcommand
                first_arg_lower = completed_args[0].lower()
                for sub_name, sub_spec in spec.subcommands.items():
                    if sub_name.lower() == first_arg_lower:
                        # Recurse into subcommand with remaining args
                        return self._resolve_structural_with_spec(
                            sub_spec, completed_args[1:], partial
                        )
                # First arg is not a recognized subcommand; no structural suggestion
                return None
            else:
                # No completed args yet -- suggest subcommand names
                sub_names = sorted(spec.subcommands.keys())
                return self._match_values(sub_names, partial, case_sensitive=False)

        # No subcommands -- resolve with this spec directly
        return self._resolve_structural_with_spec(spec, completed_args, partial)

    def _resolve_structural_with_spec(
        self,
        spec: CompletionSpec,
        completed_args: list[str],
        partial: str,
    ) -> str | None:
        """Resolve structural completion using a specific CompletionSpec.

        Handles flag scanning, positional tracking, and composition rules.

        Args:
            spec: The CompletionSpec to resolve against.
            completed_args: Completed argument tokens (after command/subcommand).
            partial: The partial word being typed.

        Returns:
            Suggested value (full value), or None.
        """
        if spec.no_args:
            return None

        flags = spec.flags or {}
        positionals = spec.positionals

        # --- Flag scanning algorithm (FR-014) ---
        positional_index = 0
        consumed_flags: set[str] = set()
        pending_value_flag: str | None = None  # Last unconsumed value-taking flag

        for token in completed_args:
            # Check --flag=value pattern
            eq_match = _FLAG_EQ_RE.match(token)
            if eq_match:
                flag_name = eq_match.group(1)
                # Mark as consumed regardless of type
                consumed_flags.add(flag_name.lower())
                pending_value_flag = None
                continue

            if token.startswith("--"):
                # Look up flag in spec
                flag_spec = self._lookup_flag(flags, token)
                consumed_flags.add(token.lower())
                if flag_spec is None:
                    # Boolean flag (maps to None) -- never consumes next token
                    pending_value_flag = None
                else:
                    # Value-taking flag -- mark as pending
                    pending_value_flag = token
                continue

            # Non-flag token
            if pending_value_flag is not None:
                # Consumed by the pending value-taking flag
                pending_value_flag = None
            else:
                # Positional argument
                positional_index += 1

        # --- Resolve what to suggest for the partial ---

        # If we have a pending unconsumed value-taking flag and the partial
        # doesn't start with "--", resolve its values
        if pending_value_flag is not None and not partial.startswith("--"):
            flag_value_spec = self._lookup_flag(flags, pending_value_flag)
            if flag_value_spec is not None:
                return self._resolve_spec_values(flag_value_spec, partial)
            return None

        # Handle --flag=value partial: partial contains "=" after "--" prefix
        if partial.startswith("--") and "=" in partial:
            eq_idx = partial.index("=")
            flag_part = partial[:eq_idx]
            value_part = partial[eq_idx + 1 :]
            flag_value_spec = self._lookup_flag(flags, flag_part)
            if flag_value_spec is not None:
                matched = self._resolve_spec_values(flag_value_spec, value_part)
                if matched is not None:
                    # Return the full --flag=value form
                    return flag_part + "=" + matched
            return None

        # Composition rule 1: partial starts with "--" → match flag names only
        if partial.startswith("--"):
            flag_names = sorted(flags.keys())
            # Exclude already-consumed flags
            available = [f for f in flag_names if f.lower() not in consumed_flags]
            return self._match_values(available, partial, case_sensitive=False)

        # Composition rule 2: check positional sequence at current index
        if positionals is not None and positional_index < len(positionals):
            slot = positionals[positional_index]
            if slot is None:
                # Free-form positional -- skip structural (FR-022)
                return None
            return self._resolve_spec_values(slot, partial)

        # Composition rule 4: positional slots exhausted
        # Only suggest flags if partial starts with "--" (already handled above)
        return None

    def _lookup_flag(
        self,
        flags: dict[str, CompletionSpec | None],
        flag_token: str,
    ) -> CompletionSpec | None:
        """Look up a flag in the flags dict (case-insensitive).

        Args:
            flags: Flag name to CompletionSpec mapping.
            flag_token: The flag token (e.g., "--code").

        Returns:
            The CompletionSpec for the flag's value (None for boolean flags),
            or None if the flag is not found (also treated as boolean-like).
        """
        flag_lower = flag_token.lower()
        for name, value_spec in flags.items():
            if name.lower() == flag_lower:
                return value_spec
        return None

    async def get_suggestion(self, value: str) -> str | None:
        """Return full-line suggestion for the given input value, or None.

        Pipeline:
        1. Parse input into command, complete tokens, partial word
        2. If command is None -> command name completion (case-insensitive)
        3. If command identified -> structural argument completion (T012/T014)
        4. Fall back to history prefix search (FR-016)
        5. Return full input line with suggestion appended (FR-017)
        """
        command, completed_args, partial = self._parse_input(value)

        if command is None:
            if not partial:
                return None
            # Command name completion: case-insensitive prefix match
            commands = sorted(self._completion_data.keys())
            matched = self._match_values(commands, partial, case_sensitive=False)
            if matched is not None:
                suffix = matched[len(partial) :]
                if suffix:
                    return value + suffix
            return None

        # Command identified -- resolve structural argument completion (T014)
        structural_match = self._resolve_structural(command, completed_args, partial)
        if structural_match is not None:
            suffix = structural_match[len(partial) :]
            if suffix:
                return value + suffix

        # History fallback: search history for prefix match (FR-016)
        history_match = self._history.search_prefix(value)
        if history_match is not None:
            return history_match

        return None
