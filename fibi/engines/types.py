"""Shared Python types for the Fibi engine layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MemoryCategory(str, Enum):
    FACT = "fact"
    USER_FACT = "user_fact"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"
    DECISION = "decision"
    IMPORTANT_EVENT = "important_event"
    TEMPORARY_CONTEXT = "temporary_context"
    EVENT = "event"
    PROJECT = "project"
    HABIT = "habit"
    BELIEF = "belief"
    GOAL = "goal"
    IMPORTANT_MOMENT = "important_moment"


class PresenceState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    SPEAKING = "speaking"
    LISTENING = "listening"
    OBSERVING = "observing"
    NAPPING = "napping"
    WAKING = "waking"
    BEING_DRAGGED = "being_dragged"


class Mood(str, Enum):
    HAPPY = "happy"
    SLEEPY = "sleepy"
    CURIOUS = "curious"
    FOCUSED = "focused"
    EXCITED = "excited"
    ANNOYED = "annoyed"
    IDLE = "idle"


@dataclass(slots=True)
class Memory:
    id: int | None
    category: MemoryCategory
    content: str
    importance: float = 0.5
    source: str = "conversation"
    created_at: str = ""
    updated_at: str = ""
    last_accessed_at: str = ""
    access_count: int = 0
    confidence: float = 0.5
    emotional_weight: float = 0.5
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class Observation:
    timestamp: str
    time_of_day: str
    active_app: str | None = None
    active_window_title: str | None = None
    clipboard_text: str | None = None


@dataclass(slots=True)
class PersonalityContext:
    system_prompt: str
    mood: str
    observation: Observation
    memories: list[Memory]
    memory_hints: list[str] = field(default_factory=list)
    patterns: list["DetectedPattern"] = field(default_factory=list)


@dataclass(slots=True)
class ModelResult:
    raw_text: str
    model: str
    duration_seconds: float
    error: str | None = None


@dataclass(slots=True)
class FibiResponse:
    display_text: str
    tts_text: str
    mood: str
    model_used: str
    used_fallback: bool = False
    timing: "TimingResult | None" = None
    motion: "MotionIntent | None" = None
    tts_priority: str = "medium"
    tts_skipped_reason: str = ""


@dataclass(slots=True)
class JournalEntry:
    id: int | None
    timestamp: str
    event_type: str
    mood: str
    presence_state: str
    short_summary: str
    related_project: str | None = None
    emotional_weight: float = 0.5
    source: str = "engine"
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class DetectedPattern:
    pattern: str
    confidence: float
    summary: str
    suggested_reaction: str


@dataclass(slots=True)
class BondState:
    affection: int = 25
    trust: int = 20
    comfort: int = 30
    mischief: int = 20
    attachment_level: int = 24
    last_affection_event_at: str | None = None


@dataclass(slots=True)
class AttentionResult:
    attention_level: int
    reason: str
    should_react: bool
    reaction_type: str


@dataclass(slots=True)
class HabitState:
    name: str
    line: str
    last_performed_at: str
    times_performed: int = 0


@dataclass(slots=True)
class InteractionEvent:
    event_type: str
    timestamp: str
    direct: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class NapState:
    is_napping: bool = False
    nap_started_at: str | None = None
    last_woke_at: str | None = None
    energy: int = 70


@dataclass(slots=True)
class WindowPosition:
    x: int
    y: int


@dataclass(slots=True)
class CreatureReaction:
    text: str
    expression: str
    reaction_type: str
    should_display: bool = True
    sound_name: str | None = None
    motion: "MotionIntent | None" = None
    timing: "TimingResult | None" = None


@dataclass(slots=True)
class RitualState:
    name: str
    last_triggered_at: str | None = None
    times_triggered: int = 0


@dataclass(slots=True)
class RitualResult:
    name: str
    reaction: CreatureReaction | None
    triggered: bool = False


@dataclass(slots=True)
class NestState:
    position: WindowPosition | None = None
    name: str = "desktop nest"
    confidence: float = 0.0
    created_at: str | None = None
    last_nested_at: str | None = None
    times_returned_to_nest: int = 0


@dataclass(slots=True)
class DailySummary:
    date: str
    main_mood: str
    notable_project: str | None
    interaction_count: int
    tiny_summary: str
    emotional_weight: int = 0
    notable_events: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectAffinity:
    project_name: str
    mention_count: int = 0
    last_seen_at: str | None = None
    affection_weight: float = 0.5
    frustration_weight: float = 0.0
    success_weight: float = 0.0


@dataclass(slots=True)
class ReactionCandidate:
    text: str
    mood: str = "idle"
    min_affection: int = 0
    max_annoyance: int = 100
    time_of_day: str | None = None
    cooldown_key: str | None = None
    weight: float = 1.0
    requires_teasing_allowed: bool = False
    blocked_when_quiet: bool = False
    blocked_when_boundary_active: bool = False
    min_familiarity: int = 0
    max_user_annoyance: int = 100
    social_tone: str = "neutral"
    can_be_motion_only: bool = False


@dataclass(slots=True)
class TimePersonalityCurve:
    time_of_day: str
    energy_bias: int
    sleepiness_bias: int
    curiosity_bias: int
    preferred_mood: str


@dataclass(slots=True)
class MotionIntent:
    motion_name: str
    duration_ms: int
    intensity: float
    expression_hint: str | None
    cooldown_key: str
    can_interrupt: bool
    reason: str


@dataclass(slots=True)
class TimingResult:
    pre_delay_ms: int = 0
    typing_style: str = "instant"
    show_thinking_bubble: bool = False
    thinking_line: str = "hmm..."


@dataclass(slots=True)
class ExpressionState:
    persistent_expression: str = "idle"
    current_expression: str = "idle"
    temporary_expression: str | None = None
    minimum_duration_ms: int = 500
    temporary_until_ms: int | None = None


@dataclass(slots=True)
class BubbleDisplayOptions:
    typing_style: str = "instant"
    auto_hide_ms: int = 0
    allow_repeat: bool = False
    keep_while_speaking: bool = True


@dataclass(slots=True)
class RepetitionState:
    spoken_lines: list[str] = field(default_factory=list)
    reaction_categories: list[str] = field(default_factory=list)
    motion_names: list[str] = field(default_factory=list)
    rituals: list[str] = field(default_factory=list)
    idle_reactions: list[str] = field(default_factory=list)
    project_references: list[str] = field(default_factory=list)


class SoundEvent(str, Enum):
    CLICK = "click"
    HAPPY = "happy"
    ANNOYED = "annoyed"
    SLEEP = "sleep"
    WAKE = "wake"
    DRAG = "drag"
    SUCCESS = "success"


class ActionRiskLevel(str, Enum):
    SAFE = "safe"
    CONFIRM_REQUIRED = "confirm_required"
    BLOCKED_FOR_NOW = "blocked_for_now"


@dataclass(slots=True)
class ActionIntent:
    action_type: str
    target: str = ""
    query: str = ""
    raw_text: str = ""
    confidence: float = 1.0
    direct_user_initiated: bool = True


@dataclass(slots=True)
class ActionSettings:
    allow_desktop_actions: bool = True
    allow_open_apps: bool = True
    allow_web_search: bool = True
    allow_volume_control: bool = True
    allow_screenshot: bool = False
    allow_shutdown: bool = False
    allow_unknown_executables: bool = False
    allow_terminal_commands: bool = False
    allow_file_modification: bool = False
    allow_clipboard_actions: bool = True
    allow_keyboard_actions: bool = True
    allow_create_folders: bool = True
    allow_safe_commands: bool = True
    allow_autonomous_actions: bool = False


@dataclass(slots=True)
class ActionPermissionResult:
    allowed: bool
    blocked: bool = False
    requires_confirmation: bool = False
    reason: str = ""
    confirmation_prompt: str = ""
    fibi_reply: str = ""


@dataclass(slots=True)
class DesktopActionResult:
    ok: bool
    message: str
    action_type: str
    target: str = ""
    provider_used: str = "local-action"
    error: str | None = None


@dataclass(slots=True)
class PendingAction:
    action_type: str
    target: str = ""
    query: str = ""
    created_at: str = ""
    expires_at: str = ""
    required_confirmation_phrase: str = ""
    risk_level: str = "confirm_required"


@dataclass(slots=True)
class ActionJournalEntry:
    timestamp: str
    action_type: str
    target: str
    risk_level: str
    allowed: bool
    blocked: bool
    required_confirmation: bool
    confirmed: bool
    result_summary: str
    user_initiated: bool


@dataclass(slots=True)
class AppIndexEntry:
    display_name: str
    normalized_name: str
    path: str
    source: str
    confidence: float = 1.0
    last_seen_at: str = ""


@dataclass(slots=True)
class AppSearchResult:
    matches: list[AppIndexEntry] = field(default_factory=list)
    query: str = ""


@dataclass(slots=True)
class VoiceInputSettings:
    allow_voice_input: bool = False
    push_to_talk_enabled: bool = True
    wake_word_enabled: bool = False
    wake_word_sensitivity: float = 0.72
    wake_word_cooldown_seconds: float = 2.5
    voice_confirmation_for_actions: bool = True
    require_confirmation_below_confidence: float = 0.75
    voice_language: str = "en-US"
    voice_provider: str = "local"
    show_transcript_before_action: bool = True
    save_voice_audio: bool = False
    save_transcripts_to_journal: bool = False
    microphone_device_id: str | None = None
    push_to_talk_hotkey: str | None = None


@dataclass(slots=True)
class VoiceListenState:
    state: str = "idle"
    source: str = "mic_button"
    started_at: str | None = None
    error: str | None = None


@dataclass(slots=True)
class VoiceTranscriptionResult:
    transcript: str = ""
    raw_text: str = ""
    confidence: float = 0.0
    duration_ms: float = 0.0
    error: str | None = None
    user_confirmed: bool = False
    source: str = "mic_button"
    should_route_to_core: bool = False


@dataclass(slots=True)
class VoiceCommandResult:
    handled: bool
    should_route_to_core: bool = False
    transcript: str = ""
    confidence: float = 0.0
    response_text: str = ""
    error: str | None = None
    needs_user_confirmation: bool = False
    source: str = "mic_button"


@dataclass(slots=True)
class VoicePermissionResult:
    allowed: bool
    reason: str = ""
    fibi_reply: str = ""


@dataclass(slots=True)
class VoiceDeviceInfo:
    device_id: str
    name: str
    is_default: bool = False


@dataclass(slots=True)
class PushToTalkState:
    enabled: bool = True
    hotkey: str | None = None
    listening: bool = False
    source: str = "mic_button"


@dataclass(slots=True)
class ContextSource:
    value: str


@dataclass(slots=True)
class ContextItem:
    context_id: str
    source: str
    title: str
    content_preview: str
    content_text: str
    mime_type: str
    file_path: str | None = None
    created_at: str = ""
    expires_at: str = ""
    token_estimate: int = 0
    user_initiated: bool = True
    can_remember: bool = True
    remembered: bool = False
    sensitivity_hint: str = "normal"
    error: str | None = None


@dataclass(slots=True)
class ContextSession:
    items: list[ContextItem] = field(default_factory=list)
    active_context_id: str | None = None


@dataclass(slots=True)
class ContextReadResult:
    ok: bool
    item: ContextItem | None = None
    message: str = ""
    error: str | None = None


@dataclass(slots=True)
class ContextPermissionResult:
    allowed: bool
    reason: str = ""
    fibi_reply: str = ""


@dataclass(slots=True)
class FileDropResult:
    ok: bool
    item: ContextItem | None = None
    message: str = ""
    error: str | None = None


@dataclass(slots=True)
class SelectedTextResult:
    ok: bool
    item: ContextItem | None = None
    message: str = ""
    error: str | None = None


@dataclass(slots=True)
class ContextSummary:
    context_id: str
    title: str
    summary: str
    token_estimate: int
    sensitivity_hint: str = "normal"


@dataclass(slots=True)
class ContextMemoryDecision:
    should_remember: bool
    summary: str
    reason: str


@dataclass(slots=True)
class BrowserSession:
    browser_session_id: str
    task_goal: str
    created_at: str
    updated_at: str
    source: str = "user_command"
    safety_level: str = "low"
    requires_confirmation: bool = False
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""
    status: str = "active"


@dataclass(slots=True)
class BrowserPageNote:
    browser_session_id: str
    url: str
    title: str
    user_provided_text: str
    summary: str
    created_at: str
    updated_at: str
    source: str = "user_provided"
    safety_level: str = "low"
    requires_confirmation: bool = False
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""
    note_id: str = ""


@dataclass(slots=True)
class BrowserTaskPlan:
    browser_session_id: str
    task_goal: str
    steps: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    source: str = "browser_helper"
    safety_level: str = "medium"
    requires_confirmation: bool = False
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""


@dataclass(slots=True)
class BrowserOpenRequest:
    browser_session_id: str
    url: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    source: str = "user_command"
    safety_level: str = "medium"
    requires_confirmation: bool = True
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""
    domain: str = ""


@dataclass(slots=True)
class BrowserSafetyResult:
    allowed: bool
    blocked: bool = False
    safety_level: str = "low"
    requires_confirmation: bool = False
    reason: str = ""
    fibi_reply: str = ""
    normalized_url: str = ""
    domain: str = ""


@dataclass(slots=True)
class BrowserSummaryResult:
    ok: bool
    summary: str
    title: str = ""
    source: str = "user_provided"
    safety_level: str = "low"
    requires_confirmation: bool = False
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""


@dataclass(slots=True)
class BrowserResearchNote:
    browser_session_id: str
    url: str
    title: str
    user_provided_text: str
    summary: str
    task_goal: str = ""
    created_at: str = ""
    updated_at: str = ""
    source: str = "user_provided"
    safety_level: str = "low"
    requires_confirmation: bool = False
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""


@dataclass(slots=True)
class PendingBrowserAction:
    browser_session_id: str
    action_type: str
    url: str
    title: str = ""
    created_at: str = ""
    updated_at: str = ""
    source: str = "user_command"
    safety_level: str = "medium"
    requires_confirmation: bool = True
    notes: list[str] = field(default_factory=list)
    linked_project_id: str = ""
    linked_issue_id: str = ""
    domain: str = ""


@dataclass(slots=True)
class WorkflowRecipeStep:
    step_id: str
    title: str
    instruction: str
    step_type: str
    requires_confirmation: bool = False
    allowed_to_auto_run: bool = False
    linked_command: str = ""
    expected_input: str = ""
    safety_notes: str = ""
    status: str = "pending"


@dataclass(slots=True)
class WorkflowRecipe:
    recipe_id: str
    name: str
    description: str
    category: str
    version: str
    steps: list[WorkflowRecipeStep] = field(default_factory=list)
    safety_level: str = "low"
    created_at: str = ""
    updated_at: str = ""
    built_in: bool = True
    enabled: bool = True


@dataclass(slots=True)
class WorkflowRun:
    run_id: str
    recipe_id: str
    recipe_name: str
    status: str
    created_at: str
    updated_at: str
    current_step_index: int = 0
    steps: list[WorkflowRecipeStep] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    linked_session_id: str = ""
    linked_project_id: str = ""
    linked_issue_ids: list[str] = field(default_factory=list)
    linked_support_bundles: list[str] = field(default_factory=list)
    linked_release_artifacts: list[str] = field(default_factory=list)
    safe_summaries: list[str] = field(default_factory=list)
    safety_level: str = "low"


@dataclass(slots=True)
class WorkflowRunState:
    active_run_id: str = ""
    runs: list[WorkflowRun] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowStepResult:
    ok: bool
    message: str
    step_id: str = ""
    step_type: str = ""
    completed: bool = False
    waiting_for_user: bool = False
    blocked: bool = False


@dataclass(slots=True)
class WorkflowRecipeSafetyResult:
    allowed: bool
    blocked: bool = False
    safety_level: str = "low"
    reason: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowRunSummary:
    run_id: str
    recipe_name: str
    status: str
    started_at: str
    completed_at: str = ""
    steps_completed: int = 0
    total_steps: int = 0
    skipped_steps: list[str] = field(default_factory=list)
    linked_issues: list[str] = field(default_factory=list)
    linked_support_bundles: list[str] = field(default_factory=list)
    linked_release_artifacts: list[str] = field(default_factory=list)
    safe_summaries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowExport:
    run_id: str
    markdown_path: str
    json_path: str
    created_at: str
    excluded: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectFileEntry:
    relative_path: str
    file_name: str
    extension: str
    size_bytes: int
    last_modified: str
    safe_to_read: bool
    ignored_reason: str = ""
    content_preview: str = ""
    token_estimate: int = 0


@dataclass(slots=True)
class ProjectNote:
    text: str
    created_at: str


@dataclass(slots=True)
class ProjectWorkspace:
    project_id: str
    name: str
    root_path: str
    created_at: str
    last_opened_at: str = ""
    last_scanned_at: str = ""
    trusted: bool = True
    file_count: int = 0
    detected_stack: list[str] = field(default_factory=list)
    summary: str = ""
    user_added: bool = True
    notes: list[ProjectNote] = field(default_factory=list)


@dataclass(slots=True)
class ProjectScanResult:
    ok: bool
    workspace: ProjectWorkspace | None = None
    files: list[ProjectFileEntry] = field(default_factory=list)
    ignored_count: int = 0
    message: str = ""
    error: str | None = None


@dataclass(slots=True)
class ProjectSummary:
    project_id: str
    name: str
    detected_stack: list[str]
    important_files: list[str]
    folders: list[str]
    summary: str


@dataclass(slots=True)
class ProjectQuestionResult:
    handled: bool
    response_text: str = ""
    needs_model: bool = False
    context_hint: str = ""


@dataclass(slots=True)
class ProjectPermissionResult:
    allowed: bool
    reason: str = ""
    fibi_reply: str = ""


@dataclass(slots=True)
class ProjectWorkspaceSettings:
    allow_project_workspaces: bool = True
    allow_hidden_folders: bool = False
    allow_vscode_folder: bool = True
    readable_file_limit_bytes: int = 1_000_000
    auto_scan_on_add: bool = True


@dataclass(slots=True)
class ProjectRecentFile:
    relative_path: str
    opened_at: str
    reason: str = ""


@dataclass(slots=True)
class ReplacementBlock:
    file_path: str
    start_line: int
    end_line: int
    before: str
    after: str
    explanation: str = ""


@dataclass(slots=True)
class UnifiedDiffSuggestion:
    file_path: str
    diff_text: str
    line_count: int = 0


@dataclass(slots=True)
class EditRiskAssessment:
    risk_level: str
    reason: str
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EditSafetyResult:
    allowed: bool
    risk: EditRiskAssessment
    refused_reason: str = ""
    fibi_reply: str = ""


@dataclass(slots=True)
class ProjectFileEditSuggestion:
    file_path: str
    summary: str
    suggested_diff: UnifiedDiffSuggestion | None = None
    replacement_blocks: list[ReplacementBlock] = field(default_factory=list)
    explanation: str = ""


@dataclass(slots=True)
class ProjectEditPlan:
    project_id: str
    target_files: list[str]
    user_request: str
    summary: str
    risk_level: str
    requires_user_review: bool = True
    can_apply_automatically: bool = False
    explanation: str = ""
    refused_reason: str = ""


@dataclass(slots=True)
class ProjectEditRequest:
    project_id: str
    target_files: list[str]
    user_request: str
    explicit_file: bool = False
    source: str = "user_message"


@dataclass(slots=True)
class EditSuggestionResult:
    ok: bool
    project_id: str = ""
    target_files: list[str] = field(default_factory=list)
    user_request: str = ""
    summary: str = ""
    risk_level: str = "low"
    requires_user_review: bool = True
    can_apply_automatically: bool = False
    suggested_diff: UnifiedDiffSuggestion | None = None
    replacement_blocks: list[ReplacementBlock] = field(default_factory=list)
    explanation: str = ""
    refused_reason: str = ""
    display_text: str = ""


@dataclass(slots=True)
class PatchFileChange:
    file_path: str
    before_hash: str
    after_hash: str
    diff_text: str = ""
    replacement: ReplacementBlock | None = None
    applied: bool = False
    error: str = ""


@dataclass(slots=True)
class PatchPlan:
    patch_id: str
    project_id: str
    target_files: list[str]
    diff_text: str
    file_changes: list[PatchFileChange] = field(default_factory=list)
    before_hash: str = ""
    after_hash: str = ""
    risk_level: str = "low"
    summary: str = ""
    created_at: str = ""
    expires_at: str = ""
    requires_confirmation: bool = True
    backup_paths: list[str] = field(default_factory=list)
    applied: bool = False
    rolled_back: bool = False
    error: str = ""


@dataclass(slots=True)
class PatchApplyRequest:
    patch_id: str
    confirmation_phrase: str
    user_initiated: bool = True


@dataclass(slots=True)
class PatchBackup:
    patch_id: str
    project_id: str
    original_relative_path: str
    backup_path: str
    before_hash: str
    created_at: str


@dataclass(slots=True)
class PatchApplyResult:
    ok: bool
    patch_id: str
    message: str
    applied_files: list[str] = field(default_factory=list)
    backup_paths: list[str] = field(default_factory=list)
    risk_level: str = ""
    error: str = ""


@dataclass(slots=True)
class PatchRollbackResult:
    ok: bool
    patch_id: str
    message: str
    restored_files: list[str] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class PatchRiskResult:
    allowed: bool
    risk_level: str
    reason: str
    requires_confirmation: bool = True
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)
    fibi_reply: str = ""


@dataclass(slots=True)
class PendingPatch:
    patch: PatchPlan
    required_confirmation_phrase: str = "apply patch confirm"
    created_at: str = ""
    expires_at: str = ""


@dataclass(slots=True)
class PatchReviewSummary:
    patch_id: str
    project_id: str
    target_files: list[str]
    risk_level: str
    summary: str
    confirmation_phrase: str = "apply patch confirm"
    manual_review_note: str = "review the diff first. tiny hands wait for confirm."


@dataclass(slots=True)
class ProjectCheckCommand:
    command_key: str
    command_args: list[str]
    cwd: str
    timeout_seconds: int = 60
    risk_level: str = "low"
    display: str = ""


@dataclass(slots=True)
class CheckCommandPreset:
    command_key: str
    display: str
    command_args: list[str]
    risk_level: str = "low"
    source: str = "preset"
    description: str = ""


@dataclass(slots=True)
class ProjectCheckRequest:
    check_id: str
    project_id: str
    command_key: str
    command_args: list[str]
    cwd: str
    timeout_seconds: int = 60
    allowed: bool = False
    requires_confirmation: bool = True
    risk_level: str = "low"


@dataclass(slots=True)
class ProjectCheckSafetyResult:
    allowed: bool
    risk_level: str
    reason: str
    requires_confirmation: bool = True
    error: str = ""


@dataclass(slots=True)
class PendingProjectCheck:
    request: ProjectCheckRequest
    required_confirmation_phrase: str = "run check confirm"
    created_at: str = ""
    expires_at: str = ""


@dataclass(slots=True)
class ProjectCheckOutputSummary:
    status: str
    summary: str
    error_count: int = 0
    warning_count: int = 0
    hints: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectCheckResult:
    check_id: str
    project_id: str
    command_key: str
    command_args: list[str]
    cwd: str
    timeout_seconds: int
    started_at: str = ""
    ended_at: str = ""
    exit_code: int | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""
    output_path: str = ""
    summary: str = ""
    error: str = ""
    risk_level: str = "low"
    timed_out: bool = False


@dataclass(slots=True)
class ProjectCheckHistoryEntry:
    check_id: str
    project_id: str
    command_key: str
    command_display: str
    exit_code: int | None
    duration_ms: float
    summary: str
    output_dir: str
    created_at: str


@dataclass(slots=True)
class ProjectCheckSettings:
    allow_project_checks: bool = True
    require_check_confirmation: bool = True
    allow_low_risk_checks_without_confirmation: bool = False
    check_timeout_seconds: int = 60
    max_check_output_chars: int = 12_000
    save_full_check_output: bool = True
    auto_suggest_check_after_patch: bool = True
    auto_run_check_after_patch: bool = False


@dataclass(slots=True)
class ErrorLocation:
    file_path: str
    line: int | None = None
    column: int | None = None
    raw: str = ""


@dataclass(slots=True)
class RelatedFileCandidate:
    relative_path: str
    absolute_path: str
    safe_to_read: bool
    score: float
    reason: str = ""
    snippet: str = ""
    suspected_line: int | None = None
    refused_reason: str = ""


@dataclass(slots=True)
class FixConfidenceResult:
    confidence: float
    reason: str


@dataclass(slots=True)
class CheckFailureAnalysis:
    check_id: str
    project_id: str
    error_type: str
    error_message: str
    related_files: list[ErrorLocation] = field(default_factory=list)
    suspected_file: str = ""
    suspected_line: int | None = None
    confidence: float = 0.0
    refused_reason: str = ""


@dataclass(slots=True)
class CheckFixSuggestion:
    check_id: str
    project_id: str
    error_type: str
    error_message: str
    related_files: list[str] = field(default_factory=list)
    suspected_file: str = ""
    suspected_line: int | None = None
    confidence: float = 0.0
    fix_summary: str = ""
    risk_level: str = "low"
    suggested_patch_id: str = ""
    requires_user_review: bool = True
    refused_reason: str = ""


@dataclass(slots=True)
class CheckFixPlan:
    check_id: str
    project_id: str
    error_type: str
    error_message: str
    related_files: list[str] = field(default_factory=list)
    suspected_file: str = ""
    suspected_line: int | None = None
    confidence: float = 0.0
    fix_summary: str = ""
    risk_level: str = "low"
    suggested_patch_id: str = ""
    requires_user_review: bool = True
    refused_reason: str = ""
    edit_suggestion: EditSuggestionResult | None = None


@dataclass(slots=True)
class PendingFixSuggestion:
    check_id: str
    project_id: str
    error_type: str
    error_message: str
    related_files: list[str] = field(default_factory=list)
    suspected_file: str = ""
    suspected_line: int | None = None
    confidence: float = 0.0
    fix_summary: str = ""
    risk_level: str = "low"
    suggested_patch_id: str = ""
    requires_user_review: bool = True
    refused_reason: str = ""
    created_at: str = ""


@dataclass(slots=True)
class WorkSessionStep:
    step_id: str
    title: str
    description: str
    step_type: str
    status: str = "pending"
    requires_confirmation: bool = False
    allowed_to_run_automatically: bool = False
    related_files: list[str] = field(default_factory=list)
    result_summary: str = ""
    error: str = ""


@dataclass(slots=True)
class WorkSession:
    session_id: str
    project_id: str
    user_goal: str
    status: str
    created_at: str
    updated_at: str
    current_step_index: int = 0
    steps: list[WorkSessionStep] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    pending_action_type: str = ""
    pending_confirmation: str = ""
    notes: list[str] = field(default_factory=list)
    risk_level: str = "low"
    last_result_summary: str = ""


@dataclass(slots=True)
class WorkSessionPlan:
    user_goal: str
    steps: list[WorkSessionStep] = field(default_factory=list)
    risk_level: str = "low"
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkSessionState:
    active_session_id: str = ""
    sessions: list[WorkSession] = field(default_factory=list)


@dataclass(slots=True)
class WorkSessionProgress:
    session_id: str
    status: str
    current_step_index: int
    total_steps: int
    completed_steps: list[str] = field(default_factory=list)
    current_step: WorkSessionStep | None = None
    next_step: WorkSessionStep | None = None
    summary: str = ""


@dataclass(slots=True)
class WorkSessionAction:
    action_type: str
    description: str
    requires_confirmation: bool = True
    confirmation_phrase: str = ""
    blocked: bool = False
    reason: str = ""


@dataclass(slots=True)
class WorkSessionDecision:
    allowed: bool
    action: WorkSessionAction | None = None
    message: str = ""
    waiting_for_user: bool = False


@dataclass(slots=True)
class WorkSessionSummary:
    session_id: str
    project_id: str
    user_goal: str
    status: str
    completed_count: int
    total_steps: int
    last_result_summary: str = ""


@dataclass(slots=True)
class InnerThought:
    id: int | None
    timestamp: str
    category: str
    mood: str
    text: str
    related_memory_id: int | None = None
    related_project: str | None = None
    emotional_weight: float = 0.2
    should_surface_to_user: bool = False
    source: str = "inner_life_engine"


@dataclass(slots=True)
class DreamFragment:
    id: int | None
    timestamp: str
    dream_text: str
    mood: str
    related_project: str | None = None
    emotional_weight: float = 0.2
    surfaced_to_user: bool = False


@dataclass(slots=True)
class PreferenceState:
    preference_key: str
    value: str
    confidence: float
    formed_from: str
    last_updated_at: str


@dataclass(slots=True)
class OpinionResult:
    text: str
    mood: str = "thinking"
    confidence: float = 0.0
    evidence_count: int = 0
    supported: bool = False
    source: str = "opinion_engine"


@dataclass(slots=True)
class MoodDriftResult:
    previous_mood: str
    new_mood: str
    reason: str
    drift_strength: float = 0.0


@dataclass(slots=True)
class EmotionalWeightUpdate:
    event_type: str
    weight: float
    reason: str
    related_project: str | None = None


@dataclass(slots=True)
class ThoughtBubbleCandidate:
    text: str
    expression: str
    emotional_weight: float
    category: str
    motion: "MotionIntent | None" = None
    should_display: bool = False


@dataclass(slots=True)
class MemorySourceInfo:
    category: str
    source: str
    confidence: float
    emotional_weight: float
    created_at: str
    updated_at: str
    last_accessed_at: str


@dataclass(slots=True)
class MemoryCareAction:
    action: str
    target: str = ""
    category: str | None = None
    confirm: bool = False


@dataclass(slots=True)
class NotebookEntry:
    entry_id: int | str | None
    section: str
    title: str
    body: str
    source_info: MemorySourceInfo | None = None


@dataclass(slots=True)
class MemoryCareResult:
    ok: bool
    message: str
    entries: list[NotebookEntry] = field(default_factory=list)
    export_path: str | None = None
    changed_count: int = 0


@dataclass(slots=True)
class MemoryReviewItem:
    memory_id: int
    source: str
    category: str
    text: str
    summary: str
    created_at: str
    updated_at: str
    confidence: float
    approved: bool
    pinned: bool
    archived: bool
    sensitive_flag: str
    source_event_id: str
    provenance: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    user_visible: bool = True
    deletion_status: str = "active"


@dataclass(slots=True)
class MemorySearchResult:
    item: MemoryReviewItem
    score: float
    similarity: float
    rank: int


@dataclass(slots=True)
class MemoryConsentState:
    memory_learning_enabled: bool = True
    remember_project_events: bool = True
    remember_browser_notes: bool = True
    remember_workflow_summaries: bool = True
    remember_user_preferences: bool = True
    remember_personality_notes: bool = True
    require_approval_for_sensitive_memory: bool = True
    auto_archive_low_confidence_memory: bool = False


@dataclass(slots=True)
class MemoryEditRequest:
    memory_id: int
    new_text: str
    user_confirmed: bool = False
    reason: str = "user_edit"


@dataclass(slots=True)
class MemoryDeleteRequest:
    memory_id: int | None = None
    category: str = ""
    user_confirmed: bool = False
    reason: str = "user_delete"
    broad_delete: bool = False


@dataclass(slots=True)
class MemoryExportRequest:
    memory_ids: list[int] = field(default_factory=list)
    include_archived: bool = False
    include_sensitive: bool = False
    format: str = "both"


@dataclass(slots=True)
class MemoryApprovalResult:
    ok: bool
    memory_id: int | None = None
    message: str = ""
    requires_confirmation: bool = False


@dataclass(slots=True)
class MemoryLearningStatus:
    enabled: bool
    consent: MemoryConsentState
    summary: str


@dataclass(slots=True)
class MemoryRiskResult:
    allowed: bool
    blocked: bool = False
    requires_approval: bool = False
    sensitive_flag: str = ""
    reason: str = ""
    safe_summary: str = ""
    masked_preview: str = ""


@dataclass(slots=True)
class PrivacySettings:
    allow_foreground_app_observation: bool = True
    allow_window_title_observation: bool = True
    allow_clipboard_observation: bool = False
    allow_journal: bool = True
    allow_dreams: bool = True
    allow_inner_thoughts: bool = True
    allow_pattern_detection: bool = True
    allow_idle_bubbles: bool = True
    allow_tts: bool = True
    allow_sounds: bool = True
    allow_ollama: bool = True
    allow_memory_learning: bool = True
    allow_nvidia_api: bool = False
    allow_gemini_api: bool = False
    allow_cloud_model: bool = False
    cloud_context_level: str = "minimal"
    cloud_context_preview: bool = True


@dataclass(slots=True)
class ExportBundle:
    created_at: str
    version: str
    memories: list[dict] = field(default_factory=list)
    journal_summaries: list[dict] = field(default_factory=list)
    dreams: list[dict] = field(default_factory=list)
    preferences: list[dict] = field(default_factory=list)
    project_affinity: list[dict] = field(default_factory=list)
    life_state: dict = field(default_factory=dict)
    privacy_settings: dict = field(default_factory=dict)


@dataclass(slots=True)
class ResetRequest:
    scope: str
    confirmation: str = ""
    create_backup: bool = True


@dataclass(slots=True)
class LocalCommandResult:
    handled: bool
    response: FibiResponse | None = None
    referenced_memory_id: int | None = None


@dataclass(slots=True)
class ModelRouterResult:
    provider_used: str
    model_used: str
    duration_ms: float
    was_cloud: bool
    fallback_used: bool
    error: str | None
    reply_text: str
    attempted_provider: str = ""
    retry_count: int = 0
    error_category: str = ""
    generation_latency_ms: float = 0.0
    fallback_latency_ms: float = 0.0
    model_router_used: bool = True


@dataclass(slots=True)
class FastResponseCategory:
    category: str
    confidence: float = 1.0
    should_use_model: bool = False


@dataclass(slots=True)
class RouteDecision:
    route_name: str
    provider_allowed: bool
    model_router_allowed: bool
    local_action_allowed: bool
    reason: str
    expected_budget_ms: int = 0
    action_type: str = ""
    fast_category: str = ""


@dataclass(slots=True)
class ResponseBudget:
    category: str
    budget_ms: int
    elapsed_ms: float = 0.0
    budget_exceeded: bool = False
    fallback_used: bool = False


@dataclass(slots=True)
class ProviderHealth:
    available: bool = False
    last_latency_ms: float = 0.0
    consecutive_failures: int = 0
    disabled_until: str | None = None


@dataclass(slots=True)
class ModelHealthState:
    ollama_available: bool = False
    cloud_available: bool = False
    last_ollama_latency_ms: float = 0.0
    last_cloud_latency_ms: float = 0.0
    consecutive_model_failures: int = 0
    provider_disabled_until: str | None = None
    last_successful_provider: str = "local"
    average_reply_latency_ms: float = 0.0


@dataclass(slots=True)
class PerformanceMetric:
    last_reply_time_ms: float = 0.0
    provider_used: str = "local"
    fast_path_used: bool = False
    model_latency_ms: float = 0.0
    tts_latency_ms: float = 0.0
    db_latency_ms: float = 0.0
    average_reply_time_ms: float = 0.0
    slowest_recent_step: str = ""


@dataclass(slots=True)
class LocalMicroBrainResult:
    text: str | None
    mood: str = "idle"
    category: str = "unknown"
    provider_used: str = "local"
    fallback_used: bool = False
    confidence: str = "high"
    handled: bool = True


@dataclass(slots=True)
class CloudProviderConfig:
    name: str = "disabled"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 8
    max_tokens: int = 60
    supports_streaming: bool = False
    privacy_level: str = "minimal"


@dataclass(slots=True)
class CancelRequest:
    requested: bool = False
    reason: str = "user"
    requested_at: str | None = None


@dataclass(slots=True)
class StreamingChunk:
    text: str
    done: bool = False
    provider: str = ""
    sequence: int = 0


@dataclass(slots=True)
class AppSettings:
    start_minimized: bool = False
    minimize_to_tray: bool = True
    always_on_top: bool = True
    click_through_mode: bool = False
    animation_intensity: str = "normal"
    bubble_typing_effect: bool = True
    performance_debug_logs: bool = False
    setup_complete: bool = False
    first_run_skipped: bool = False
    allow_project_checks: bool = True
    require_check_confirmation: bool = True
    allow_low_risk_checks_without_confirmation: bool = False
    check_timeout_seconds: int = 60
    max_check_output_chars: int = 12_000
    save_full_check_output: bool = True
    auto_suggest_check_after_patch: bool = True
    auto_run_check_after_patch: bool = False
    beta_mode: bool = False
    language_provider: str = ""
    automatic_provider_fallback: bool = False
    window_mode: str = "compact"
    reply_style: str = "concise"
    start_pet_with_windows: bool = False


@dataclass(slots=True)
class TrayAction:
    action: str
    label: str


@dataclass(slots=True)
class SettingsUpdate:
    key: str
    value: object


@dataclass(slots=True)
class FirstRunState:
    completed: bool = False
    skipped: bool = False
    completed_at: str | None = None


@dataclass(slots=True)
class AutostartState:
    enabled: bool = False
    method: str = "startup_folder"
    target_path: str = ""
    error: str | None = None


@dataclass(slots=True)
class DataHealthResult:
    ok: bool
    message: str
    checks: dict = field(default_factory=dict)


@dataclass(slots=True)
class AssetHealthResult:
    ok: bool
    message: str
    checks: dict = field(default_factory=dict)


@dataclass(slots=True)
class ShutdownState:
    clean_shutdown: bool = True
    last_shutdown_at: str | None = None
    unclean_shutdown_detected: bool = False


@dataclass(slots=True)
class GuiCommandResult:
    handled: bool
    action: str = ""
    message: str = ""


@dataclass(slots=True)
class RelationshipState:
    familiarity_level: int = 10
    teasing_allowed: bool = False
    comfort_with_silence: int = 50
    user_prefers_quiet: bool = False
    user_prefers_playful: bool = False
    user_annoyance_level: int = 0
    last_boundary_signal_at: str | None = None
    last_apology_at: str | None = None
    social_warmth: int = 20
    social_distance: int = 40
    interaction_style: str = "shy"


@dataclass(slots=True)
class BoundarySignal:
    level: str
    phrase: str
    quiet_minutes: int
    should_apologize: bool = False


@dataclass(slots=True)
class BoundaryState:
    active: bool = False
    level: str = ""
    started_at: str | None = None
    expires_at: str | None = None
    last_phrase: str = ""


@dataclass(slots=True)
class QuietModeState:
    active: bool = False
    started_at: str | None = None
    expires_at: str | None = None
    reason: str = ""
    mute_tts: bool = False


@dataclass(slots=True)
class SocialContextDecision:
    action: str
    text: str = ""
    reason: str = ""
    motion_only: bool = False


@dataclass(slots=True)
class SocialPreferenceUpdate:
    key: str
    value: object
    confidence: float
    reason: str


@dataclass(slots=True)
class RelationshipCommandResult:
    ok: bool
    message: str
    state: RelationshipState | None = None
