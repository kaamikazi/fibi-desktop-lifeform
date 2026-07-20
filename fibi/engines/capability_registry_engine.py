"""Capability registry for Fibi's command center."""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    capability_id: str
    name: str
    description: str
    category: str
    enabled: bool = True
    safety_level: str = "low"
    requires_confirmation: bool = False
    commands: list[str] = field(default_factory=list)
    settings_keys: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    docs_path: str = ""
    status_summary: str = "available"


class CapabilityRegistryEngine:
    """Read-only capability map with optional runtime status overlays."""

    def __init__(self) -> None:
        self._capabilities = _capabilities()

    def all(self, statuses: dict[str, dict[str, object]] | None = None) -> list[CapabilityMetadata]:
        overlays = statuses or {}
        result: list[CapabilityMetadata] = []
        for capability in self._capabilities:
            overlay = overlays.get(capability.capability_id, {})
            result.append(
                replace(
                    capability,
                    enabled=bool(overlay.get("enabled", capability.enabled)),
                    status_summary=str(overlay.get("status_summary", capability.status_summary)),
                )
            )
        return result

    def find(self, name_or_id: str, statuses: dict[str, dict[str, object]] | None = None) -> CapabilityMetadata | None:
        needle = _normalize(name_or_id)
        for capability in self.all(statuses):
            if needle in {_normalize(capability.capability_id), _normalize(capability.name)}:
                return capability
        for capability in self.all(statuses):
            haystack = " ".join([capability.name, capability.description, capability.category, capability.capability_id])
            if needle and needle in _normalize(haystack):
                return capability
        return None

    def format_list(self, statuses: dict[str, dict[str, object]] | None = None) -> str:
        caps = self.all(statuses)
        bits = [
            f"{cap.name}: {'on' if cap.enabled else 'off'} ({cap.safety_level})"
            for cap in caps
        ]
        return "capabilities:\n" + "\n".join(bits[:24])

    def format_one(self, capability: CapabilityMetadata) -> str:
        confirm = "needs confirmation" if capability.requires_confirmation else "no confirmation for discovery"
        blocked = ", ".join(capability.blocked_actions[:4]) if capability.blocked_actions else "none"
        commands = ", ".join(capability.commands[:5]) if capability.commands else "none"
        return (
            f"{capability.name}: {'on' if capability.enabled else 'off'}.\n"
            f"{capability.description}\n"
            f"safety: {capability.safety_level}; {confirm}.\n"
            f"commands: {commands}.\n"
            f"blocked: {blocked}.\n"
            f"status: {capability.status_summary}."
        )


def _capabilities() -> list[CapabilityMetadata]:
    return [
        CapabilityMetadata("chat", "Chat", "Short local-first conversation with optional local model.", "core", True, "low", False, ["/help"], ["allow_ollama"], ["identity rewrite by model"]),
        CapabilityMetadata("gemini_provider", "Gemini Provider", "Optional replaceable cloud language cortex with local privacy controls.", "models", False, "medium", False, ["/provider status", "/provider use gemini", "/provider privacy"], ["allow_cloud_model", "allow_gemini_api"], ["identity ownership", "memory writes", "actions", "raw private context"], "docs/GEMINI_PROVIDER_V0301.md"),
        CapabilityMetadata("memory", "Memory", "Local memory notebook and care commands.", "memory", True, "medium", True, ["/memories", "/memory search"], ["allow_memory_learning"], ["secret harvesting"], "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CapabilityMetadata("memory_review", "Memory Review", "User-visible memory list, search, approve, edit, delete, and export.", "memory", True, "medium", True, ["/memories", "/memory show", "/memory edit", "/memory delete", "/memory export"], ["memory_learning_enabled"], ["hidden memory collection"], "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CapabilityMetadata("memory_consent", "Memory Consent", "Pause/resume learning and control sensitive-memory approval.", "memory", True, "medium", False, ["/memory consent", "/memory learning off", "/memory approval required on"], ["memory_learning_enabled", "require_approval_for_sensitive_memory"], ["storing secrets"], "docs/MEMORY_PRIVACY_V030.md"),
        CapabilityMetadata("sensitive_memory_guard", "Sensitive Memory Guard", "Blocks secrets and requires approval for sensitive personal memories.", "memory", True, "high", False, ["/memory safety"], ["require_approval_for_sensitive_memory"], ["passwords", "tokens", "private keys", "raw private pages"], "docs/MEMORY_PRIVACY_V030.md"),
        CapabilityMetadata("rag_memory", "RAG Memory", "Local SQLite/FAISS retrieval memory.", "memory", True, "medium", False, ["/memory search", "/memory health"], ["allow_memory_learning"], ["cloud indexing"], "docs/MEMORY_REVIEW_CENTER_V030.md"),
        CapabilityMetadata("voice_output", "Voice Output", "Optional text-to-speech output.", "voice", True, "low", False, ["/voice output on", "/voice output off"], ["allow_tts"], ["speaking secrets intentionally hidden by support masking"]),
        CapabilityMetadata("voice_input", "Voice Input", "Push-to-talk voice input when enabled.", "voice", False, "medium", True, ["/listen", "/voice input on confirm"], ["allow_voice_input"], ["wake word by default"]),
        CapabilityMetadata("rvc_voice_skin", "RVC Voice Skin", "Optional local RVC conversion layer.", "voice", False, "medium", True, ["/voice skin status", "/voice skin on confirm"], ["rvc_enabled"], ["remote voice upload"]),
        CapabilityMetadata("desktop_actions", "Desktop Actions", "Small confirmed desktop actions.", "actions", True, "medium", True, ["/actions status", "/pending action"], ["allow_desktop_actions"], ["autonomous actions", "shutdown by default"]),
        CapabilityMetadata("project_workspace", "Project Workspace", "Safe local project registration and reading.", "project", True, "medium", True, ["/project add", "/project read"], ["allow_project_workspaces"], ["reading ignored secrets"]),
        CapabilityMetadata("patch_apply", "Patch Apply", "Suggest and apply reviewed patches only after confirmation.", "project", True, "high", True, ["/edit file", "apply patch confirm"], ["allow_file_modification"], ["auto-apply patch"]),
        CapabilityMetadata("project_checks", "Project Checks", "Run safe project checks after confirmation.", "project", True, "medium", True, ["/check presets", "/check run"], ["allow_project_checks"], ["arbitrary terminal"]),
        CapabilityMetadata("check_failure_analysis", "Check Failure Analysis", "Analyze saved check failures and suggest safe fixes.", "project", True, "medium", True, ["/check analyze last", "/check suggest fix"], [], ["editing without review"]),
        CapabilityMetadata("work_sessions", "Work Sessions", "Guided supervised project task steps.", "workflow", True, "low", False, ["/session start", "/session next"], [], ["autopilot"]),
        CapabilityMetadata("browser_helper", "Browser Helper", "Confirmed URL opening and pasted page summaries.", "browser", True, "medium", True, ["/browser open", "/browser summarize"], [], ["history", "cookies", "passwords", "scraping"]),
        CapabilityMetadata("workflow_recipes", "Workflow Recipes", "Named guided rituals for repeatable workflows.", "workflow", True, "low", False, ["/workflow list", "/workflow start"], [], ["auto-run commands"]),
        CapabilityMetadata("issue_tracker", "Issue Tracker", "Local beta issue notes.", "support", True, "low", False, ["/issue new", "/issue list"], [], ["telemetry upload"]),
        CapabilityMetadata("feedback_capture", "Feedback Capture", "Local feedback notes.", "support", True, "low", False, ["/feedback new"], [], ["telemetry upload"]),
        CapabilityMetadata("support_bundle", "Support Bundle", "Masked local diagnostic bundle.", "support", True, "medium", False, ["/support bundle"], [], ["memory DB export", "project source export", "secrets"]),
        CapabilityMetadata("release_health", "Release Health", "Local release and runtime readiness checks.", "release", True, "low", False, ["/release health", "/health gui"], [], ["network update"]),
        CapabilityMetadata("update_manifest", "Update Manifest", "Local update manifest status only.", "release", True, "safe", False, ["/update status"], [], ["auto-download", "auto-install"]),
        CapabilityMetadata("packaging_build_tools", "Packaging/Build Tools", "Manual local build scripts for beta zip/installer prep.", "release", True, "medium", True, ["python tools/build_windows.py --clean --zip"], [], ["auto-build from chat"]),
    ]


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().replace("_", " ").replace("-", " ").split())
