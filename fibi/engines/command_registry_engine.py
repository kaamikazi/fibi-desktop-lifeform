"""Read-only command metadata for Fibi's help system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CommandMetadata:
    command: str
    aliases: list[str] = field(default_factory=list)
    category: str = "general"
    description: str = ""
    examples: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    risk_level: str = "low"
    capability_id: str = ""
    available_in_packaged_mode: bool = True
    docs_path: str = ""


class CommandRegistryEngine:
    """Central discovery registry for commands.

    This engine stores metadata only. It never dispatches or executes commands.
    """

    def __init__(self) -> None:
        self._commands = _commands()

    def all(self) -> list[CommandMetadata]:
        return list(self._commands)

    def categories(self) -> list[str]:
        return sorted({command.category for command in self._commands})

    def by_category(self, category: str) -> list[CommandMetadata]:
        normalized = _normalize(category)
        return [
            command for command in self._commands
            if _normalize(command.category) == normalized
        ]

    def find(self, command_or_topic: str) -> CommandMetadata | None:
        needle = _normalize(command_or_topic)
        for command in self._commands:
            names = [_normalize(command.command), *[_normalize(alias) for alias in command.aliases]]
            if needle in names:
                return command
        for command in self._commands:
            haystack = " ".join(
                [
                    command.command,
                    command.category,
                    command.description,
                    command.capability_id,
                    " ".join(command.aliases),
                    " ".join(command.examples),
                ]
            )
            if needle and needle in _normalize(haystack):
                return command
        return None

    def search(self, term: str, limit: int = 8) -> list[CommandMetadata]:
        needle = _normalize(term)
        if not needle:
            return []
        matches: list[CommandMetadata] = []
        for command in self._commands:
            haystack = " ".join(
                [
                    command.command,
                    command.category,
                    command.description,
                    command.capability_id,
                    " ".join(command.aliases),
                    " ".join(command.examples),
                ]
            )
            if needle in _normalize(haystack):
                matches.append(command)
        return matches[:limit]

    def format_command(self, command: CommandMetadata) -> str:
        confirm = "confirm" if command.requires_confirmation else "no confirm"
        return f"{command.command} - {command.description} [{command.risk_level}, {confirm}]"

    def format_results(self, commands: list[CommandMetadata]) -> str:
        if not commands:
            return "no command crumbs matched."
        return "\n".join(self.format_command(command) for command in commands[:8])

    def beginner_line(self) -> str:
        return (
            "try: /what can you do, /commands, /help search browser, "
            "/memories, /memory consent, /workflow list, /browser safety, /permissions."
        )


def _commands() -> list[CommandMetadata]:
    return [
        CommandMetadata("/help", ["help me use Fibi", "/beginner guide"], "help", "Show beginner help and command discovery.", ["/help", "/help search browser"], False, "safe", "help", True, "docs/BEGINNER_GUIDE_V029.md"),
        CommandMetadata("/commands", ["show commands"], "help", "List commands or a category.", ["/commands", "/commands browser"], False, "safe", "help", True, "docs/COMMANDS_V029.md"),
        CommandMetadata("/capabilities", [], "help", "List Fibi capability cards.", ["/capabilities"], False, "safe", "help", True, "docs/CAPABILITIES_V029.md"),
        CommandMetadata("/capability <name>", [], "help", "Show one capability status and safety notes.", ["/capability browser"], False, "safe", "help", True, "docs/CAPABILITIES_V029.md"),
        CommandMetadata("/safety", ["what is safe?", "what can you not do?"], "safety", "Explain safety boundaries and refusals.", ["/safety", "/refusals"], False, "safe", "safety", True, "docs/SAFETY_MODEL_V029.md"),
        CommandMetadata("/permissions", ["what needs confirmation?"], "safety", "Show enabled/disabled local permissions.", ["/permissions"], False, "safe", "safety", True, "docs/SAFETY_MODEL_V029.md"),
        CommandMetadata("/memories", ["/memory list", "what do you remember?"], "memory", "List visible local memory crumbs.", ["/memories"], False, "safe", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory search <term>", ["search your memory for Fibi"], "memory", "Search local RAG memories.", ["/memory search project"], False, "safe", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory show <id>", [], "memory", "Show one memory with source and approval details.", ["/memory show 12"], False, "safe", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory approve <id>", [], "memory", "Approve a pending sensitive memory.", ["/memory approve 12"], False, "low", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory pin <id>", [], "memory", "Pin a useful memory.", ["/memory pin 12"], False, "low", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory unpin <id>", [], "memory", "Unpin a memory.", ["/memory unpin 12"], False, "low", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory archive <id>", [], "memory", "Hide a memory without deleting it.", ["/memory archive 12"], False, "low", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory edit <id>", [], "memory", "Stage an edit for confirmation.", ["/memory edit 12 user likes short replies", "memory edit confirm"], True, "medium", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory delete <id>", ["forget that"], "memory", "Stage a memory delete for confirmation.", ["/memory delete 12", "memory delete confirm"], True, "medium", "memory_review", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory delete category <category>", ["forget this project note"], "memory", "Stage a broad category delete for confirmation.", ["/memory delete category project"], True, "high", "memory_review", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory export", ["export my memories"], "memory", "Export visible memories locally without secrets or embeddings.", ["/memory export"], False, "medium", "memory_review", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory health", [], "memory", "Show RAG memory counts, index, cache, and storage health.", ["/memory health"], False, "safe", "rag_memory", True, "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CommandMetadata("/memory consent", [], "memory", "Show memory learning consent settings.", ["/memory consent"], False, "safe", "memory_consent", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory learning on", ["resume memory"], "memory", "Resume safe general memory learning.", ["/memory learning on"], False, "low", "memory_consent", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory learning off", ["pause memory"], "memory", "Pause new memory learning.", ["/memory learning off"], False, "safe", "memory_consent", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory approval required on", [], "memory", "Require approval for sensitive memories.", ["/memory approval required on"], False, "safe", "memory_consent", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory approval required off", [], "memory", "Disable sensitive approval prompts while still blocking secrets.", ["/memory approval required off"], False, "medium", "memory_consent", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/memory safety", ["is memory safe?"], "memory", "Explain memory privacy and sensitive-memory rules.", ["/memory safety"], False, "safe", "sensitive_memory_guard", True, "docs/MEMORY_PRIVACY_V030.md"),
        CommandMetadata("/provider status", ["/provider", "which model are you using?"], "models", "Show the selected language provider without exposing credentials.", ["/provider status"], False, "safe", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/provider list", [], "models", "List local and optional cloud language providers.", ["/provider list"], False, "safe", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/provider models", [], "models", "List safe Gemini text model IDs when configured.", ["/provider models"], False, "low", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/provider use ollama", ["switch back to local"], "models", "Select local Ollama and turn Gemini cloud routing off.", ["/provider use ollama"], False, "safe", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/provider use gemini", ["use Gemini"], "models", "Select configured Gemini and show the cloud context preview.", ["/provider use gemini"], False, "medium", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/provider test", ["test Gemini"], "models", "Send one tiny neutral Gemini provider test when explicitly selected.", ["/provider test"], False, "medium", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/provider privacy", ["what will be sent to the cloud?"], "models", "Explain Gemini context exclusions.", ["/provider privacy", "/provider context"], False, "safe", "gemini_provider", True, "docs/CLOUD_CONTEXT_PRIVACY_V0301.md"),
        CommandMetadata("/provider benchmark", [], "models", "Run one manual neutral latency comparison.", ["/provider benchmark"], False, "medium", "gemini_provider", True, "docs/GEMINI_PROVIDER_V0301.md"),
        CommandMetadata("/version", [], "health", "Show app version.", ["/version", "/version detailed"], False, "safe", "release_health", True),
        CommandMetadata("/health gui", ["/debug summary"], "health", "Show local runtime health.", ["/health gui"], False, "safe", "release_health", True),
        CommandMetadata("/startup diagnostics", [], "health", "Show startup diagnostics.", ["/startup diagnostics"], False, "safe", "release_health", True),
        CommandMetadata("/self test", [], "health", "Run Fibi's local self-test.", ["/self test"], False, "low", "release_health", True),
        CommandMetadata("/voice status", [], "voice", "Show voice input/output status.", ["/voice status"], False, "safe", "voice_output", True),
        CommandMetadata("/voice rvc off", [], "voice", "Use Edge TTS directly without RVC conversion.", ["/voice rvc off"], False, "safe", "voice_output", True),
        CommandMetadata("/voice output on", ["/voice on"], "voice", "Enable TTS output.", ["/voice output on"], False, "low", "voice_output", True),
        CommandMetadata("/voice output off", ["/voice off"], "voice", "Disable TTS output.", ["/voice output off"], False, "safe", "voice_output", True),
        CommandMetadata("/listen", [], "voice", "Start push-to-talk voice input if enabled.", ["/listen"], False, "low", "voice_input", True),
        CommandMetadata("/voice skin status", [], "voice", "Show RVC voice skin status.", ["/voice skin status"], False, "safe", "rvc_voice_skin", True),
        CommandMetadata("/voice skin on confirm", [], "voice", "Enable configured RVC voice skin.", ["/voice skin on confirm"], True, "medium", "rvc_voice_skin", True),
        CommandMetadata("/actions status", ["/actions"], "actions", "Show desktop action safety status.", ["/actions status"], False, "safe", "desktop_actions", True),
        CommandMetadata("/apps search <name>", [], "actions", "Search known local app shortcuts.", ["/apps search chrome"], False, "low", "desktop_actions", True),
        CommandMetadata("/pending action", [], "actions", "Show pending confirmed action.", ["/pending action"], False, "safe", "desktop_actions", True),
        CommandMetadata("/project", ["/projects"], "project", "Show project workspace commands or memories.", ["/project current", "/projects"], False, "safe", "project_workspace", True),
        CommandMetadata("/project add <path>", [], "project", "Register a local project folder.", ["/project add E:\\Fibi chubi"], True, "medium", "project_workspace", True),
        CommandMetadata("/project read <file>", [], "project", "Read a safe project file by explicit path.", ["/project read README.md"], True, "medium", "project_workspace", True),
        CommandMetadata("/edit file <path> <request>", [], "patch", "Suggest a safe patch for review.", ["/edit file README.md clarify setup"], True, "medium", "patch_apply", True),
        CommandMetadata("apply patch confirm", [], "patch", "Apply the currently pending reviewed patch.", ["apply patch confirm"], True, "high", "patch_apply", True),
        CommandMetadata("/check presets", [], "checks", "List safe project check presets.", ["/check presets"], False, "safe", "project_checks", True),
        CommandMetadata("/check run <preset>", ["run check confirm"], "checks", "Run a project check after confirmation.", ["/check run pytest"], True, "medium", "project_checks", True),
        CommandMetadata("/check analyze last", [], "checks", "Analyze saved failed check output.", ["/check analyze last"], False, "low", "check_failure_analysis", True),
        CommandMetadata("/check suggest fix", [], "checks", "Suggest a fix from last failed check.", ["/check suggest fix"], True, "medium", "check_failure_analysis", True),
        CommandMetadata("/session start <goal>", [], "sessions", "Start a guided work session.", ["/session start help me fix tests"], False, "low", "work_sessions", True),
        CommandMetadata("/session next", ["/session continue", "continue"], "sessions", "Advance a guided work session.", ["/session next"], False, "low", "work_sessions", True),
        CommandMetadata("/workflow list", ["/recipes"], "workflows", "List built-in workflow recipes.", ["/workflow list"], False, "safe", "workflow_recipes", True, "docs/WORKFLOW_RECIPES_V028.md"),
        CommandMetadata("/workflow start <name>", [], "workflows", "Start a guided recipe.", ["/workflow start Safe Release Build"], False, "low", "workflow_recipes", True, "docs/WORKFLOW_RECIPES_V028.md"),
        CommandMetadata("/workflow next", ["/workflow continue"], "workflows", "Advance the active recipe guide.", ["/workflow next"], False, "low", "workflow_recipes", True, "docs/WORKFLOW_RECIPES_V028.md"),
        CommandMetadata("/browser safety", [], "browser", "Explain browser helper safety.", ["/browser safety"], False, "safe", "browser_helper", True, "docs/BROWSER_HELPER_V027.md"),
        CommandMetadata("/browser open <url>", [], "browser", "Prepare confirmed URL opening.", ["/browser open https://example.com"], True, "medium", "browser_helper", True, "docs/BROWSER_HELPER_V027.md"),
        CommandMetadata("browser confirm", [], "browser", "Confirm pending browser open.", ["browser confirm"], True, "medium", "browser_helper", True, "docs/BROWSER_HELPER_V027.md"),
        CommandMetadata("/browser summarize", [], "browser", "Summarize user-provided page text.", ["/browser summarize"], False, "low", "browser_helper", True, "docs/BROWSER_HELPER_V027.md"),
        CommandMetadata("/issue new <title | details>", ["make a bug report"], "issues", "Create a local beta issue.", ["/issue new voice squeaked | steps"], False, "low", "issue_tracker", True),
        CommandMetadata("/issue list", [], "issues", "List local issues.", ["/issue list"], False, "safe", "issue_tracker", True),
        CommandMetadata("/feedback new <note>", ["beta feedback"], "feedback", "Save local beta feedback.", ["/feedback new feels cozy"], False, "low", "feedback_capture", True),
        CommandMetadata("/support bundle", [], "support", "Create a local safe diagnostic bundle.", ["/support bundle"], False, "medium", "support_bundle", True),
        CommandMetadata("/support bundle for issue <id>", [], "support", "Create and link a safe bundle to an issue.", ["/support bundle for issue ISS-1234"], False, "medium", "support_bundle", True),
        CommandMetadata("/release health", [], "release", "Show release/update readiness.", ["/release health"], False, "safe", "release_health", True),
        CommandMetadata("/update status", [], "release", "Read local update manifest status.", ["/update status"], False, "safe", "update_manifest", True),
        CommandMetadata("/debug paths", [], "debug", "Show local data/log/report paths.", ["/debug paths"], False, "safe", "release_health", True),
        CommandMetadata("python tools/build_windows.py --clean --zip", [], "packaging", "Build local Windows beta package manually.", ["python tools/build_windows.py --clean --zip"], True, "medium", "packaging_build_tools", False),
    ]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().replace("_", " ").replace("-", " ").split())
