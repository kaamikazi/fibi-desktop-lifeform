"""Fibi v0.05 orchestration: presence first, model last."""

from __future__ import annotations

import random
import re
import time
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from fibi.brain.cleanup import clean_response, is_effectively_empty, remove_mood_tags, tts_safe_text
from fibi.build_info import APP_VERSION
from fibi.engines.action_confirmation_engine import ActionConfirmationEngine
from fibi.engines.action_intent_detector import ActionIntentDetector
from fibi.engines.action_journal_engine import ActionJournalEngine
from fibi.engines.action_settings_engine import ActionSettingsEngine
from fibi.engines.action_types import get_action_definition
from fibi.engines.app_index_engine import AppIndexEngine
from fibi.engines.app_settings_engine import AppSettingsEngine
from fibi.engines.asset_health_engine import AssetHealthEngine
from fibi.engines.autostart_engine import AutostartEngine
from fibi.engines.attention_engine import AttentionEngine
from fibi.engines.boundary_engine import BoundaryEngine
from fibi.engines.check_failure_analyzer import CheckFailureAnalyzer
from fibi.engines.check_fix_planner import CheckFixPlanner
from fibi.engines.context_engine import ContextEngine
from fibi.engines.data_health_engine import DataHealthEngine
from fibi.engines.emotional_weighting import emotional_weight_for_message
from fibi.engines.error_report_engine import ErrorReportEngine
from fibi.engines.beta_feedback_engine import BetaFeedbackEngine
from fibi.engines.browser_helper_engine import BrowserHelperEngine
from fibi.engines.browser_safety_engine import BrowserSafetyEngine
from fibi.engines.browser_research_notes_engine import BrowserResearchNotesEngine
from fibi.engines.capability_registry_engine import CapabilityRegistryEngine
from fibi.engines.command_registry_engine import CommandRegistryEngine
from fibi.engines.html_text_extractor import HtmlTextExtractor
from fibi.engines.fast_response_classifier import FastResponseClassifier
from fibi.engines.file_reader_engine import FileReaderEngine
from fibi.engines.habit_engine import HabitEngine
from fibi.engines.inner_life_engine import InnerLifeEngine
from fibi.engines.issue_tracker_engine import IssueRecord, IssueTrackerEngine
from fibi.engines.life_engine import EXPRESSION_MAP, LifeEngine
from fibi.engines.journal_engine import JournalEngine
from fibi.engines.local_micro_brain import LocalMicroBrain
from fibi.engines.memory_care_engine import MemoryCareEngine
from fibi.engines.memory_consent_engine import MemoryConsentEngine
from fibi.engines.memory_engine import MemoryEngine
from fibi.engines.memory_review_engine import MemoryReviewEngine
from fibi.engines.model_engine import ModelEngine
from fibi.engines.model_health_engine import ModelHealthEngine
from fibi.engines.model_router import ModelRouter
from fibi.engines.motion_engine import MotionEngine
from fibi.engines.nvidia_model_engine import NvidiaModelEngine
from fibi.engines.observation_engine import ObservationEngine
from fibi.engines.opinion_engine import OpinionEngine
from fibi.engines.pattern_engine import PatternEngine
from fibi.engines.patch_confirmation_engine import PatchConfirmationEngine
from fibi.engines.patch_engine import PatchEngine
from fibi.engines.patch_history_engine import PatchHistoryEngine
from fibi.engines.patch_safety_engine import PatchSafetyEngine
from fibi.engines.permission_engine import PermissionEngine
from fibi.engines.permission_overview_engine import PermissionOverview, PermissionOverviewEngine
from fibi.engines.personality_engine import PersonalityEngine
from fibi.engines.preference_engine import PreferenceEngine
from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
from fibi.engines.project_check_confirmation_engine import ProjectCheckConfirmationEngine
from fibi.engines.project_check_history_engine import ProjectCheckHistoryEngine
from fibi.engines.project_check_preset_engine import ProjectCheckPresetEngine
from fibi.engines.project_check_runner import ProjectCheckRunner
from fibi.engines.project_check_safety_engine import ProjectCheckSafetyEngine
from fibi.engines.project_edit_planner import ProjectEditPlanner
from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.reaction_library import ReactionLibrary
from fibi.engines.related_file_resolver import RelatedFileResolver
from fibi.engines.release_health_engine import ReleaseHealthEngine
from fibi.engines.relationship_engine import RelationshipEngine
from fibi.engines.ritual_engine import RitualEngine
from fibi.engines.repetition_guard import RepetitionGuard
from fibi.engines.response_budget_engine import BUDGET_FALLBACKS, ResponseBudgetEngine
from fibi.engines.route_decision_engine import RouteDecisionEngine
from fibi.engines.routers import (
    ActionRouter,
    ChatRouter,
    CommandRouter,
    ContextRouter,
    MemoryRouter,
    ProjectRouter,
    ResponsePipeline,
    VoiceRouter,
)
from fibi.engines.rvc_voice_skin_engine import RvcVoiceSkinEngine
from fibi.engines.secret_sanitizer import SecretSanitizer
from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
from fibi.engines.safety_explainer_engine import SafetyExplainerEngine
from fibi.engines.social_context_engine import SocialContextEngine
from fibi.engines.shutdown_manager import ShutdownManager
from fibi.engines.startup_diagnostics_engine import StartupDiagnosticsEngine
from fibi.engines.timing_engine import TimingEngine
from fibi.engines.tts_manager import TtsManager
from fibi.engines.update_manifest_engine import UpdateManifestEngine
from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
from fibi.engines.voice_command_router import VoiceCommandRouter
from fibi.engines.voice_health_engine import VoiceHealthEngine
from fibi.engines.voice_cache_engine import VoiceCacheEngine
from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine
from fibi.engines.voice_settings_engine import VoiceSettingsEngine
from fibi.engines.warmup_engine import WarmupEngine
from fibi.engines.workflow_export_engine import WorkflowExportEngine
from fibi.engines.workflow_recipe_engine import WorkflowRecipeEngine
from fibi.engines.workflow_safety_engine import WorkflowSafetyEngine
from fibi.engines.work_planner_engine import WorkPlannerEngine
from fibi.engines.work_session_engine import WorkSessionEngine
from fibi.engines.work_step_runner import WorkStepRunner
from fibi.engines.desktop_action_engine import DesktopActionEngine
from fibi.version import detailed_version_line, version_line
from fibi.engines.types import ActionIntent, CheckFixPlan, CreatureReaction, FibiResponse, LocalCommandResult, Memory, MemoryCategory, MemoryDeleteRequest, MemoryEditRequest, MemoryExportRequest, Observation, PendingAction, PendingFixSuggestion, ProjectCheckRequest, VoiceTranscriptionResult, WorkSessionPlan, WorkSessionStep, WorkflowRun
from fibi.rag.rag_memory_service import RAGMemoryServiceFacade
from fibi.runtime_paths import logs_dir, is_packaged, runtime_info
from fibi.logging_config import mask_secrets

LOGGER = logging.getLogger(__name__)

FALLBACKS = [
    "eepy... say that again?",
    "my tiny brain dropped the thought.",
    "wait wait, I forgot what I was saying.",
    "hmm... Windows distracted me.",
]

FAST_GREETINGS = {"hi", "hey", "hello", "yo", "sup", "oi", "oi g", "heyy", "hii", "fibi", "you there"}
FAST_GREETING_LINES = ["eep.", "hm?", "hi.", "tiny creature online.", "guarding.", "back?"]

SUCCESS_SIGNALS = (
    "it worked",
    "fixed",
    "done",
    "passed",
    "finally",
    "build passed",
    "compile passed",
    "deployed",
    "launched",
    "solved",
)

FRUSTRATION_SIGNALS = (
    "broken",
    "failed",
    "error",
    "crash",
    "i quit",
    "i hate this",
    "nothing works",
    "i'm tired",
    "im tired",
)


class FibiCore:
    """Coordinate engines without allowing the model to own Fibi."""

    def __init__(
        self,
        life: LifeEngine | None = None,
        memory: MemoryEngine | None = None,
        observation: ObservationEngine | None = None,
        journal: JournalEngine | None = None,
        patterns: PatternEngine | None = None,
        attention: AttentionEngine | None = None,
        habits: HabitEngine | None = None,
        personality: PersonalityEngine | None = None,
        model: ModelEngine | None = None,
        nvidia_model: NvidiaModelEngine | None = None,
        model_router: ModelRouter | None = None,
        reactions: ReactionLibrary | None = None,
        rituals: RitualEngine | None = None,
        motion: MotionEngine | None = None,
        timing: TimingEngine | None = None,
        repetition: RepetitionGuard | None = None,
        inner_life: InnerLifeEngine | None = None,
        preferences: PreferenceEngine | None = None,
        opinions: OpinionEngine | None = None,
        memory_care: MemoryCareEngine | None = None,
        privacy: PrivacySettingsEngine | None = None,
        relationship: RelationshipEngine | None = None,
        boundary: BoundaryEngine | None = None,
        social: SocialContextEngine | None = None,
        classifier: FastResponseClassifier | None = None,
        micro_brain: LocalMicroBrain | None = None,
        budget: ResponseBudgetEngine | None = None,
        route_decisions: RouteDecisionEngine | None = None,
        health: ModelHealthEngine | None = None,
        warmup: WarmupEngine | None = None,
        app_settings: AppSettingsEngine | None = None,
        autostart: AutostartEngine | None = None,
        data_health: DataHealthEngine | None = None,
        asset_health: AssetHealthEngine | None = None,
        action_settings: ActionSettingsEngine | None = None,
        action_intents: ActionIntentDetector | None = None,
        permissions: PermissionEngine | None = None,
        app_index: AppIndexEngine | None = None,
        desktop_actions: DesktopActionEngine | None = None,
        action_confirmations: ActionConfirmationEngine | None = None,
        action_journal: ActionJournalEngine | None = None,
        voice_settings: VoiceSettingsEngine | None = None,
        speech_recognition: SpeechRecognitionEngine | None = None,
        voice_router: VoiceCommandRouter | None = None,
        voice_health: VoiceHealthEngine | None = None,
        voice_skin_settings: VoiceSkinSettingsEngine | None = None,
        rvc_voice_skin: RvcVoiceSkinEngine | None = None,
        voice_cache: VoiceCacheEngine | None = None,
        secret_sanitizer: SecretSanitizer | None = None,
        context_engine: ContextEngine | None = None,
        file_reader: FileReaderEngine | None = None,
        project_workspace: ProjectWorkspaceEngine | None = None,
        project_edit_planner: ProjectEditPlanner | None = None,
    ) -> None:
        self._started_monotonic = time.monotonic()
        self._last_error_summary = ""
        self.life = life or LifeEngine()
        self.memory = memory or MemoryEngine()
        self.privacy = privacy or PrivacySettingsEngine(self.life.state_path)
        self.observation = observation or ObservationEngine(
            allow_clipboard=self.privacy.settings.allow_clipboard_observation
        )
        self.journal = journal or JournalEngine(self.memory.database_path)
        self.patterns = patterns or PatternEngine(self.memory, self.journal)
        self.attention = attention or AttentionEngine()
        self.habits = habits or HabitEngine()
        self.personality = personality or PersonalityEngine(self.memory)
        self.model = model or ModelEngine()
        self.model_router = model_router or ModelRouter(self.model, nvidia_model)
        self.reactions = reactions or ReactionLibrary()
        self.rituals = rituals or RitualEngine(self.reactions, self.life.ritual_states)
        self.motion = motion or MotionEngine()
        self.timing = timing or TimingEngine()
        self.repetition = repetition or RepetitionGuard(self.life.repetition_state)
        self.inner_life = inner_life or InnerLifeEngine(self.memory.database_path)
        self.preferences = preferences or PreferenceEngine(self.memory.database_path)
        self.opinions = opinions or OpinionEngine(self.memory.database_path)
        self.memory_care = memory_care or MemoryCareEngine(self.memory.database_path, self.life.state_path)
        self.relationship = relationship or RelationshipEngine(self.life.state_path)
        self.boundary = boundary or BoundaryEngine(self.life.state_path)
        self.social = social or SocialContextEngine()
        self.classifier = classifier or FastResponseClassifier()
        self.micro_brain = micro_brain or LocalMicroBrain()
        self.budget = budget or ResponseBudgetEngine()
        self.route_decisions = route_decisions or RouteDecisionEngine()
        self.health = health or ModelHealthEngine(self.life.state_path)
        self.tts_manager = TtsManager()
        self.warmup = warmup or WarmupEngine()
        self.app_settings = app_settings or AppSettingsEngine()
        self.autostart = autostart or AutostartEngine()
        self.data_health = data_health or DataHealthEngine(
            self.memory.database_path,
            self.life.state_path,
            self.app_settings.settings_path,
        )
        self.asset_health = asset_health or AssetHealthEngine()
        self.startup_diagnostics = StartupDiagnosticsEngine()
        self.startup_diagnostics.run()
        self.shutdown_manager = ShutdownManager()
        self.error_reports = ErrorReportEngine()
        self.issues = IssueTrackerEngine()
        self.feedback = BetaFeedbackEngine()
        self.updates = UpdateManifestEngine()
        self.release_health = ReleaseHealthEngine(self.issues, self.updates)
        self.action_settings = action_settings or ActionSettingsEngine(self.life.state_path)
        self.action_intents = action_intents or ActionIntentDetector()
        self.permissions = permissions or PermissionEngine()
        self.app_index = app_index or AppIndexEngine()
        self.desktop_actions = desktop_actions or DesktopActionEngine(self.app_index)
        self.secret_sanitizer = secret_sanitizer or SecretSanitizer()
        self.sensitive_memory_guard = SensitiveMemoryGuard(self.secret_sanitizer)
        self.memory_consent = MemoryConsentEngine(self.life.state_path)
        self.browser_safety = BrowserSafetyEngine()
        self.html_extractor = HtmlTextExtractor(self.secret_sanitizer)
        self.browser_research = BrowserResearchNotesEngine()
        self.browser_helper = BrowserHelperEngine(
            safety=self.browser_safety,
            extractor=self.html_extractor,
            research=self.browser_research,
            browser_open=self.desktop_actions.browser_open,
        )
        self.command_registry = CommandRegistryEngine()
        self.capability_registry = CapabilityRegistryEngine()
        self.safety_explainer = SafetyExplainerEngine()
        self.permission_overview = PermissionOverviewEngine()
        self.action_confirmations = action_confirmations or ActionConfirmationEngine(self.life.state_path)
        self.action_journal = action_journal or ActionJournalEngine()
        self.voice_settings = voice_settings or VoiceSettingsEngine(self.life.state_path)
        self.speech_recognition = speech_recognition or SpeechRecognitionEngine()
        self.voice_router = voice_router or VoiceCommandRouter(self.action_intents)
        self.voice_transcript_router = VoiceRouter(self.voice_router)
        self.voice_health = voice_health or VoiceHealthEngine(self.speech_recognition)
        self.voice_skin_settings = voice_skin_settings or VoiceSkinSettingsEngine()
        self.rvc_voice_skin = rvc_voice_skin or RvcVoiceSkinEngine()
        self.voice_cache = voice_cache or VoiceCacheEngine()
        self.context_engine = context_engine or ContextEngine(self.secret_sanitizer)
        self.file_reader = file_reader or FileReaderEngine(self.context_engine)
        self.project_workspace = project_workspace or ProjectWorkspaceEngine(context=self.context_engine, sanitizer=self.secret_sanitizer)
        self.project_edit_planner = project_edit_planner or ProjectEditPlanner(self.project_workspace)
        self.patch_safety = PatchSafetyEngine()
        self.patch_engine = PatchEngine(self.project_workspace, self.patch_safety)
        self.patch_confirmations = PatchConfirmationEngine()
        self.patch_history = PatchHistoryEngine()
        self.check_presets = ProjectCheckPresetEngine()
        self.check_safety = ProjectCheckSafetyEngine()
        self.check_runner = ProjectCheckRunner(sanitizer=self.secret_sanitizer)
        self.check_confirmations = ProjectCheckConfirmationEngine()
        self.check_history = ProjectCheckHistoryEngine()
        self.check_failure_analyzer = CheckFailureAnalyzer()
        self.related_file_resolver = RelatedFileResolver(self.project_workspace)
        self.check_fix_planner = CheckFixPlanner()
        self.work_sessions = WorkSessionEngine()
        self.work_planner = WorkPlannerEngine()
        self.work_step_runner = WorkStepRunner(
            self._session_project_summary,
            self._session_check_analysis,
            self._session_suggest_fix,
        )
        self.workflow_safety = WorkflowSafetyEngine()
        self.workflow_recipes = WorkflowRecipeEngine(safety=self.workflow_safety)
        self.workflow_export = WorkflowExportEngine()
        self.chat_router = ChatRouter(self.classifier, self.micro_brain)
        self.command_router = CommandRouter(self._handle_local_command)
        self.action_router = ActionRouter(self._handle_pending_action_confirmation, self._handle_action_intent)
        self.context_router = ContextRouter(self._handle_context_command, self._maybe_capture_pasted_context)
        self.project_router = ProjectRouter(
            self._handle_project_command,
            self._maybe_handle_project_edit_intent,
            self._handle_patch_command,
            self._handle_check_command,
            self._maybe_handle_project_check_intent,
        )
        self.memory_router = MemoryRouter(RAGMemoryServiceFacade(database_path=self.memory.database_path))
        self.memory_review = MemoryReviewEngine(self.memory_router.rag_memory, guard=self.sensitive_memory_guard)
        self.response_pipeline = ResponsePipeline()
        self._last_referenced_memory_id: int | None = None
        self._cancel_requested = False
        self._last_drag_spammed = False
        self._pending_idle_motion = None
        self._last_ambient_signature = None
        self._pending_project_path: str | None = None
        self._pending_memory_edit: MemoryEditRequest | None = None
        self._pending_memory_delete: MemoryDeleteRequest | None = None
        self._last_applied_patch = None
        self._last_check_result = None
        self._last_check_failure_analysis = None
        self._last_check_fix_plan = None
        self._pending_fix_suggestion = None
        self._unclean_shutdown_detected = bool(self.life._saved_state.get("clean_shutdown") is False)
        self._mark_running()
        startup_observation = self._observe()
        favorite = self.patterns.favorite_project()
        self.boundary.refresh()
        self._start_warmup()
        ritual = self.rituals.startup(
            startup_observation.time_of_day,
            self.life.bond.affection,
            self.life.continuity_gap_hours(),
            favorite.project_name if favorite and favorite.mention_count >= 2 else None,
        )
        first_run_packaged = bool(getattr(self.app_settings, "was_first_run", False) and is_packaged())
        self._startup_message = (
            "hi. i live here now. cloud off. secrets safe. tiny setup survived."
            if first_run_packaged
            else "back. tiny crash survived." if self._unclean_shutdown_detected
            else "" if self.boundary.quiet.active
            else ritual.reaction.text if ritual.reaction
            else self.life.startup_line
        )
        self.life.set_ritual_states(self.rituals.export_state())
        self._journal_record(
            "startup",
            self.life.mood,
            self.life.presence.value,
            self._startup_message,
            emotional_weight=0.35,
            source="life_engine",
            metadata={
                "gap_hours": self.life.continuity_gap_hours(),
                "time_of_day": startup_observation.time_of_day,
                "active_app": startup_observation.active_app,
                "ritual": ritual.name if ritual.triggered else None,
            },
        )
        if ritual.triggered:
            self.repetition.remember(line=ritual.reaction.text, category="ritual", ritual=ritual.name)
            self._save_repetition()
            self._journal_record(
                "ritual", ritual.reaction.expression, self.life.presence.value,
                ritual.reaction.text, emotional_weight=0.45, source="ritual_engine",
                metadata={"ritual": ritual.name},
            )

    @property
    def startup_message(self) -> str:
        return self._startup_message

    def handle_user_message(self, user_message: str) -> FibiResponse:
        return self.respond(user_message)

    def start_voice_listen(self, source: str = "slash_command") -> FibiResponse:
        if not self.voice_settings.settings.allow_voice_input:
            return self._local_response("ears tucked away.", "sleepy").response
        if source == "future_wake_word" and not self.voice_settings.settings.wake_word_enabled:
            return self._local_response("wake word sleeping.", "sleepy").response
        transcription = self.speech_recognition.listen(self.voice_settings.settings, source=source)
        return self.handle_voice_transcript(transcription)

    def cancel_voice_listen(self) -> FibiResponse:
        return self._local_response("ears canceled.", "sleepy").response

    def handle_voice_transcript(self, transcription_result: VoiceTranscriptionResult) -> FibiResponse:
        routed = self.voice_transcript_router.route(
            transcription_result,
            self.voice_settings.settings,
            quiet_active=self.boundary.quiet.active,
        )
        if not routed.should_route_to_core:
            return self._local_response(routed.response_text or "say again?", "thinking").response
        if self.voice_settings.settings.save_transcripts_to_journal:
            self._journal_record(
                "voice_transcript",
                self.life.mood,
                self.life.presence.value,
                routed.transcript[:120],
                emotional_weight=0.15,
                source="voice_command_router",
            )
        return self.respond(routed.transcript)

    def get_voice_status(self) -> str:
        return self.voice_health.status_line(self.voice_settings.settings)

    def update_voice_settings(self, **values):
        return self.voice_settings.update(**values)

    def add_context_text(self, text: str, source: str = "manual_selected_text", title: str = "selected text") -> FibiResponse:
        item = self.context_engine.add_text(text, source=source, title=title, user_initiated=True)
        return self._local_response(f"context crumb held: {item.title}.", "thinking").response

    def handle_dropped_file(self, path: str) -> FibiResponse:
        from pathlib import Path

        dropped = Path(path)
        if dropped.is_dir():
            self._pending_project_path = str(dropped)
            return self._local_response("project nest? say confirm project.", "thinking").response
        result = self.file_reader.read_user_file(path, source="dropped_file")
        if not result.ok:
            return self._local_response(result.message or "can't chew that file yet.", "sleepy").response
        return self._local_response(f"tiny file acquired: {result.item.title}.", "happy").response

    def context_status(self) -> str:
        session = self.context_engine.session()
        if not session.items:
            return "no context crumbs."
        last = session.items[-1]
        return f"context: {last.title}. temporary. not remembering it unless you say so."

    def handle_local_command(self, command: str) -> LocalCommandResult:
        return self._handle_local_command(command)

    def get_status(self) -> str:
        nest = "nest ok" if self.life.nest.position else "no nest"
        memory = "memory learning on" if self.privacy.settings.allow_memory_learning else "memory learning off"
        warmup = "warmup done" if self.warmup.status.completed else "warming"
        return f"{self.life.mood}. {nest}. {self.boundary.status()}. {memory}. {warmup}. {self.relationship.state.interaction_style}."

    def get_gui_health_snapshot(self) -> str:
        project = self.project_workspace.current()
        session = self.session_status_chip() or "none"
        try:
            rag = self.memory_router.rag_memory.health_check()
            rag_ok = getattr(rag, "healthy", False)
            rag_line = "rag ok" if rag_ok else "rag needs help"
        except Exception as exc:
            rag_line = f"rag sleepy: {exc}"
        uptime_seconds = int(max(0, time.monotonic() - self._started_monotonic))
        voice_skin = self.rvc_voice_skin.status(self.voice_skin_settings.settings)
        pieces = [
            version_line(),
            f"uptime: {uptime_seconds}s",
            f"beta mode: {'on' if self.app_settings.settings.beta_mode else 'off'}",
            f"mood: {self.life.mood}",
            f"session: {session}",
            f"project: {project.name if project else 'none'}",
            rag_line,
            f"voice input: {'on' if self.voice_settings.settings.allow_voice_input else 'off'}",
            f"rvc: {'on' if voice_skin.get('rvc_enabled') else 'off'}",
            self.get_model_status(),
            self._memory_health_short_line(),
            f"commands: {len(self.command_registry.all())} mapped.",
            self.workflow_recipes.status_line(),
            self.browser_helper.status_line(),
            self.browser_helper.last_safety_line(),
            self.action_settings.summary_line(),
            self.data_health.check().message,
            "workers: " + ("warmup done" if self.warmup.status.completed else "warming"),
            "last error: " + (self._last_error_summary or "none"),
        ]
        return "\n".join(pieces)

    def _first_run_status(self) -> str:
        info = runtime_info()
        settings_ok = self.app_settings.settings_path.exists()
        memory_exists = Path(self.memory.database_path).exists()
        try:
            rag = self.memory_router.rag_memory.health_check()
            rag_line = "rag ok" if getattr(rag, "healthy", False) else "rag sleepy"
        except Exception:
            rag_line = "rag sleepy"
        privacy_safe = (
            not self.privacy.settings.allow_cloud_model
            and not self.privacy.settings.allow_nvidia_api
            and not self.privacy.settings.allow_clipboard_observation
            and not self.action_settings.settings.allow_screenshot
            and not self.action_settings.settings.allow_autonomous_actions
        )
        pieces = [
            "first nest ok." if info.user_data_dir.exists() and settings_ok else "first nest needs crumbs.",
            "cloud off." if not self.privacy.settings.allow_cloud_model and not self.privacy.settings.allow_nvidia_api else "cloud on.",
            "voice off." if not self.voice_settings.settings.allow_voice_input else "voice on.",
            "rvc off." if not self.voice_skin_settings.settings.rvc_enabled else "rvc on.",
            "privacy safe." if privacy_safe else "privacy check needed.",
            "memory db exists." if memory_exists else "memory db not created yet.",
            rag_line + ".",
            self.action_settings.summary_line(),
            "packaged." if info.packaged else "dev mode.",
            "crumbs local.",
        ]
        return " ".join(pieces)

    def _limitations_line(self) -> str:
        return (
            "limits: RVC needs setup. Ollama optional. mic deps optional. "
            "installer later. wake word off. browser helper manual only. "
            "workflow recipes guide only. autonomy off. cloud off."
        )

    def _self_test_line(self) -> str:
        checks: list[tuple[str, bool]] = []
        info = runtime_info()
        checks.append(("version", bool(version_line())))
        checks.append(("runtime_paths", info.user_data_dir.exists()))
        checks.append(("settings", self.app_settings.settings_path.exists()))
        try:
            probe = info.user_data_dir / ".self_test_write"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            checks.append(("data_writable", True))
        except OSError:
            checks.append(("data_writable", False))
        checks.append(("health_snapshot", bool(self.get_gui_health_snapshot())))
        checks.append(("actions", self.action_settings.settings is not None))
        checks.append(("voice", self.voice_settings.settings is not None))
        checks.append(("rvc", self.voice_skin_settings.settings is not None))
        checks.append(("project_workspace", self.project_workspace.store_path.exists() or self.project_workspace.store_path.parent.exists()))
        checks.append(("workflow_recipes", bool(self.workflow_recipes.recipes())))
        checks.append(("command_registry", bool(self.command_registry.all())))
        checks.append(("capability_registry", bool(self.capability_registry.all())))
        checks.append(("cloud_call", not self.privacy.settings.allow_cloud_model and not self.privacy.settings.allow_nvidia_api))
        checks.append(("model_call", True))
        failed = [name for name, ok in checks if not ok]
        if failed:
            details = ", ".join(failed[:4])
            result = f"self test found crumbs: {details}."
            self.release_health.last_self_test_result = result
            return result
        self.release_health.last_self_test_result = "self test survived."
        return "self test survived."

    def _last_route_summary(self) -> str:
        try:
            return self.route_decisions.last_line()
        except Exception:
            return "route: unknown."

    def _safe_health_snapshot(self) -> str:
        return mask_secrets(self.get_gui_health_snapshot())

    def _latest_support_bundle(self) -> Path | None:
        reports = sorted(logs_dir().parent.joinpath("reports").glob("fibi_error_report_*.zip"), key=lambda path: path.stat().st_mtime if path.exists() else 0)
        return reports[-1] if reports else None

    def _feedback_for_issue(self, issue_id: str) -> list[dict[str, object]]:
        return [asdict(item) for item in self.feedback.list(limit=200) if item.linked_issue_id.upper() == issue_id.upper()]

    def _issue_line(self, issue: IssueRecord) -> str:
        return f"{issue.issue_id} [{issue.status}/{issue.severity}/{issue.category}] {issue.title}"

    def _handle_issue_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/issue new":
            return self._local_response("bug jar opened. tell me what squeaked.", "thinking", tts_priority="silent")
        if lowered.startswith("/issue new "):
            payload = self.secret_sanitizer.sanitize(text[len("/issue new "):].strip())
            title, description = _split_title_description(payload)
            issue = self.issues.create(
                title,
                description,
                category=_guess_issue_category(payload),
                severity=_guess_issue_severity(payload),
                tags=["beta"],
                last_route_decision_summary=self._last_route_summary(),
                health_snapshot_summary=self._safe_health_snapshot(),
            )
            return self._local_response(f"issue saved. tiny detective mode. {issue.issue_id}.", "thinking", tts_priority="silent")
        if lowered == "/issue list":
            issues = self.issues.list(limit=8)
            if not issues:
                return self._local_response("no bug jars yet.", "sleepy", tts_priority="silent")
            return self._local_response("issues: " + "; ".join(self._issue_line(issue) for issue in issues[-5:]), "thinking", tts_priority="silent")
        if lowered == "/issue last":
            issue = self.issues.last()
            return self._local_response(self._issue_line(issue) if issue else "no bug jars yet.", "thinking", tts_priority="silent")
        if lowered.startswith("/issue show "):
            issue_id = text[len("/issue show "):].strip()
            issue = self.issues.get(issue_id)
            if issue is None:
                return self._local_response("can't find that bug jar.", "sleepy", tts_priority="silent")
            line = f"{self._issue_line(issue)}. {issue.description or 'no details yet.'}"
            return self._local_response(line, "thinking", tts_priority="silent")
        if lowered.startswith("/issue close "):
            issue = self.issues.update_status(text[len("/issue close "):].strip(), "closed")
            return self._local_response(f"closed {issue.issue_id}." if issue else "can't find that bug jar.", "sleepy", tts_priority="silent")
        if lowered.startswith("/issue reopen "):
            issue = self.issues.update_status(text[len("/issue reopen "):].strip(), "open")
            return self._local_response(f"reopened {issue.issue_id}." if issue else "can't find that bug jar.", "thinking", tts_priority="silent")
        if lowered == "/issue export all":
            path = self.issues.export_all()
            return self._local_response(f"packed all issue crumbs: {path}", "thinking", tts_priority="silent")
        if lowered.startswith("/issue export "):
            path = self.issues.export(text[len("/issue export "):].strip())
            return self._local_response(f"packed issue crumb: {path}" if path else "can't find that bug jar.", "thinking", tts_priority="silent")
        if lowered == "/issue link support last":
            issue = self.issues.last()
            bundle = self._latest_support_bundle()
            if issue is None:
                return self._local_response("no issue to link.", "sleepy", tts_priority="silent")
            if bundle is None:
                return self._local_response("no support bundle yet. use /support bundle.", "sleepy", tts_priority="silent")
            linked = self.issues.link_support_bundle(issue.issue_id, bundle)
            return self._local_response(f"linked safe crumbs to {linked.issue_id}." if linked else "link squeaked.", "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _export_support_bundle_for_issue(self, issue_id: str) -> LocalCommandResult:
        issue = self.issues.get(issue_id)
        if issue is None:
            return self._local_response("can't find that bug jar.", "sleepy", tts_priority="silent")
        path = self.error_reports.export(
            self._safe_health_snapshot(),
            self._last_route_summary(),
            [self._last_error_summary] if self._last_error_summary else [],
            beta_mode=self.app_settings.settings.beta_mode,
            issue_metadata=asdict(issue),
            feedback_metadata=self._feedback_for_issue(issue.issue_id),
        )
        self.issues.link_support_bundle(issue.issue_id, path)
        return self._local_response(f"packed the safe crumbs for {issue.issue_id}: {path}", "thinking", tts_priority="silent")

    def _handle_feedback_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered in {"/feedback", "/feedback new"}:
            return self._local_response("feedback jar opened. tell me the tiny note.", "thinking", tts_priority="silent")
        if lowered.startswith("/feedback new "):
            payload = self.secret_sanitizer.sanitize(text[len("/feedback new "):].strip())
            record = self.feedback.create(payload, feedback_type=_guess_feedback_type(payload), tags=["beta"])
            return self._local_response(f"feedback saved. {record.feedback_id}.", "happy", tts_priority="silent")
        if lowered == "/feedback list":
            records = self.feedback.list(limit=8)
            if not records:
                return self._local_response("no feedback crumbs yet.", "sleepy", tts_priority="silent")
            bits = [f"{record.feedback_id} [{record.feedback_type}] {record.message[:48]}" for record in records[-5:]]
            return self._local_response("feedback: " + "; ".join(bits), "thinking", tts_priority="silent")
        if lowered == "/feedback export":
            path = self.feedback.export()
            return self._local_response(f"packed feedback crumbs: {path}", "thinking", tts_priority="silent")
        if lowered == "/feedback clear exported confirm":
            count = self.feedback.clear_exported(confirm=True)
            return self._local_response(f"cleared {count} exported feedback crumb(s).", "sleepy", tts_priority="silent")
        return LocalCommandResult(False)

    def _handle_update_command(self, lowered: str) -> LocalCommandResult:
        if lowered in {"/update status", "/update check local"}:
            return self._local_response(self.updates.status_line(), "thinking", tts_priority="silent")
        if lowered == "/update notes":
            return self._local_response(self.updates.notes_line(), "thinking", tts_priority="silent")
        if lowered == "/update safety":
            return self._local_response(self.updates.safety_line(), "sleepy", tts_priority="silent")
        return LocalCommandResult(False)

    def _handle_debug_command(self, lowered: str) -> LocalCommandResult:
        if lowered == "/debug summary":
            return self._local_response(mask_secrets(self.get_gui_health_snapshot()), "thinking", tts_priority="silent")
        if lowered == "/debug recent errors":
            return self._local_response(mask_secrets(self._last_error_summary or "no recent errors."), "thinking", tts_priority="silent")
        if lowered == "/debug last route":
            return self._local_response(mask_secrets(self._last_route_summary()), "thinking", tts_priority="silent")
        if lowered == "/debug paths":
            info = runtime_info()
            line = f"paths: data={info.user_data_dir}; logs={logs_dir()}; reports={logs_dir().parent / 'reports'}"
            return self._local_response(mask_secrets(line), "thinking", tts_priority="silent")
        if lowered == "/debug workers":
            line = "workers: " + ("warmup done" if self.warmup.status.completed else "warming") + f"; cancel={self._cancel_requested}"
            return self._local_response(line, "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _handle_browser_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/browser safety":
            return self._local_response(self.browser_safety.status_line(), "thinking", tts_priority="silent")
        if lowered == "/browser pending":
            pending = self.browser_helper.pending_action
            if pending is None:
                return self._local_response("no browser doorway waiting.", "sleepy", tts_priority="silent")
            return self._local_response(f"pending browser open: {pending.domain}. say: browser confirm", "thinking", tts_priority="silent")
        if lowered in {"/browser confirm", "browser confirm"}:
            ok, message, url = self.browser_helper.confirm_pending()
            if ok:
                self._record_action(ActionIntent("open_website", target=url), True, False, False, True, message)
            return self._local_response(message, "happy" if ok else "sleepy", tts_priority="silent")
        if lowered in {"/browser cancel", "browser cancel"}:
            had_pending = self.browser_helper.cancel_pending()
            return self._local_response("browser doorway canceled." if had_pending else "no browser doorway waiting.", "sleepy", tts_priority="silent")
        if lowered.startswith("/browser open "):
            return self._browser_request_open(text[len("/browser open "):].strip())
        if lowered.startswith("/browser start "):
            session = self.browser_helper.start_session(text[len("/browser start "):].strip())
            return self._local_response(f"browser session started: {session.task_goal}.", "thinking", tts_priority="silent")
        if lowered == "/browser current":
            return self._local_response(self.browser_helper.status_line(), "thinking", tts_priority="silent")
        if lowered.startswith("/browser note "):
            payload = text[len("/browser note "):].strip()
            url = _extract_first_url(payload)
            if not url:
                return self._local_response("note needs a http/https link crumb.", "thinking", tts_priority="silent")
            note_text = payload.replace(url, "").strip()
            note = self.browser_helper.save_url_note(url, self.secret_sanitizer.sanitize(note_text))
            return self._local_response(f"saved link crumb: {note.title}." if note else self.browser_helper.last_safety_result.fibi_reply, "thinking", tts_priority="silent")
        if lowered == "/browser summarize":
            return self._browser_summarize_last_context()
        if lowered == "/browser save page":
            last = self.context_engine.last()
            if last is None:
                return self._local_response("paste page text first. i won't read pages sneaky.", "sleepy", tts_priority="silent")
            note = self.browser_helper.save_page_text_note(last.content_text, title=last.title)
            return self._local_response(f"saved page note: {note.note_id}.", "happy", tts_priority="silent")
        if lowered == "/browser plan":
            plan = self.browser_helper.plan()
            return self._local_response("browser checklist: " + "; ".join(plan.steps[:5]) + ".", "thinking", tts_priority="silent")
        if lowered == "/browser history":
            sessions = self.browser_helper.sessions(limit=5)
            if not sessions:
                return self._local_response("no browser session crumbs.", "sleepy", tts_priority="silent")
            return self._local_response("browser sessions: " + "; ".join(session.task_goal[:40] for session in sessions[-5:]), "thinking", tts_priority="silent")
        if lowered == "/browser clear session":
            return self._local_response("browser session cleared." if self.browser_helper.clear_session() else "no browser session.", "sleepy", tts_priority="silent")
        if lowered == "/browser remember note":
            notes = self.browser_helper.notes(limit=1)
            if not notes:
                return self._local_response("no browser note to remember.", "sleepy", tts_priority="silent")
            note = notes[-1]
            content = "Browser note: " + note.summary[:700]
            risk = self._memory_write_risk(content, source="browser_note_confirmed", user_requested=True)
            if risk is None:
                return self._local_response("memory paused.", "sleepy", tts_priority="silent")
            self.memory_router.rag_memory.remember_event(
                content,
                importance=0.4,
                confidence=0.6,
                source="browser_note_confirmed",
                metadata={"remembered_summary_only": True, "url": note.url, "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary}},
                provenance={"route": "browser_helper", "user_confirmed": True},
            )
            return self._local_response("remembered the note summary, not the whole page.", "happy", tts_priority="silent")
        return LocalCommandResult(False)

    def _handle_workflow_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered in {"/recipes", "/workflow list"}:
            recipes = self.workflow_recipes.recipes()
            names = "; ".join(recipe.name for recipe in recipes)
            return self._local_response("recipes: " + names + ".", "thinking", tts_priority="silent")
        if lowered == "/workflow safety":
            return self._local_response(self.workflow_safety.status_line(), "thinking", tts_priority="silent")
        if lowered.startswith("/workflow show "):
            return self._workflow_show(text[len("/workflow show "):].strip())
        if lowered.startswith("/workflow start "):
            return self._workflow_start(text[len("/workflow start "):].strip())
        if lowered == "/workflow current":
            return self._local_response(self._workflow_current_line(), "thinking", tts_priority="silent")
        if lowered in {"/workflow next", "/workflow continue"}:
            return LocalCommandResult(True, self._workflow_continue())
        if lowered == "/workflow pause":
            run = self.workflow_recipes.pause()
            return self._local_response("workflow curled up." if run else "no workflow ritual.", "sleepy", tts_priority="silent")
        if lowered == "/workflow resume":
            run = self.workflow_recipes.resume()
            return self._local_response("workflow awake-ish." if run else "no workflow ritual.", "thinking", tts_priority="silent")
        if lowered == "/workflow cancel":
            run = self.workflow_recipes.cancel()
            return self._local_response("workflow cancelled. tiny clipboard closed." if run else "no workflow ritual.", "sleepy", tts_priority="silent")
        if lowered == "/workflow history":
            runs = self.workflow_recipes.history(limit=5)
            if not runs:
                return self._local_response("no recipe footprints yet.", "sleepy", tts_priority="silent")
            bits = [f"{run.status}: {run.recipe_name} ({len(run.completed_steps)}/{len(run.steps)})" for run in runs[-4:]]
            return self._local_response("workflow footprints: " + "; ".join(bits) + ".", "thinking", tts_priority="silent")
        if lowered == "/workflow export last":
            return self._workflow_export_last()
        return LocalCommandResult(False)

    def _workflow_show(self, name: str) -> LocalCommandResult:
        recipe = self.workflow_recipes.get_recipe(name)
        if recipe is None:
            return self._local_response("can't find that recipe crumb.", "sleepy", tts_priority="silent")
        summary = self.workflow_recipes.recipe_summary(recipe)
        steps = "; ".join(f"{index + 1}. {step.title}" for index, step in enumerate(recipe.steps[:8]))
        return self._local_response(summary + "\nsteps: " + steps, "thinking", tts_priority="silent")

    def _workflow_start(self, name: str) -> LocalCommandResult:
        recipe = self.workflow_recipes.get_recipe(name)
        if recipe is None:
            return self._local_response("can't find that recipe crumb. use /workflow list.", "sleepy", tts_priority="silent")
        safety = self.workflow_safety.validate(recipe)
        if safety.blocked:
            return self._local_response("recipe blocked: " + safety.reason, "sleepy", tts_priority="silent")
        project = self.project_workspace.current()
        linked_project_id = project.project_id if project else ""
        linked_session_id = self._create_work_session_for_recipe(recipe.name, linked_project_id, recipe.steps)
        run = self.workflow_recipes.start(
            recipe.recipe_id,
            linked_session_id=linked_session_id,
            linked_project_id=linked_project_id,
        )
        if run is None:
            return self._local_response("recipe refused to start. safety squeak.", "sleepy", tts_priority="silent")
        first = self.workflow_recipes.current_step(run)
        return self._local_response(
            f"recipe started: {run.recipe_name}.\nstep 1: {first.title if first else 'done'}.\nsay: /workflow next",
            "thinking",
            tts_priority="silent",
        )

    def _workflow_continue(self) -> FibiResponse:
        active_before = self.workflow_recipes.active()
        result = self.workflow_recipes.continue_run()
        active_after = self.workflow_recipes.active()
        if result.ok and active_before is not None and active_after is None:
            completed = self.workflow_recipes.get_run(active_before.run_id)
            if completed:
                self._remember_workflow_event(completed)
        suffix = ""
        if active_after is not None:
            next_step = self.workflow_recipes.current_step(active_after)
            if next_step:
                suffix = f"\nnext recipe crumb: {next_step.title}.\nsay: /workflow next"
        mood = "happy" if active_after is None and result.ok else "thinking"
        return self._local_response(result.message + suffix, mood, tts_priority="silent").response

    def _workflow_current_line(self) -> str:
        run = self.workflow_recipes.active()
        if run is None:
            return "no workflow ritual."
        step = self.workflow_recipes.current_step(run)
        return f"workflow: {run.recipe_name}. {len(run.completed_steps)}/{len(run.steps)} done. next: {step.title if step else 'done'}."

    def _workflow_export_last(self) -> LocalCommandResult:
        run = self.workflow_recipes.active()
        if run is None:
            history = self.workflow_recipes.history(limit=1)
            run = history[-1] if history else None
        if run is None:
            return self._local_response("no workflow to export.", "sleepy", tts_priority="silent")
        exported = self.workflow_export.export(run)
        if "release" in run.recipe_id:
            run.linked_release_artifacts.extend([exported.markdown_path, exported.json_path])
        return self._local_response(
            f"workflow exported: {exported.markdown_path}",
            "happy",
            tts_priority="silent",
        )

    def _create_work_session_for_recipe(self, recipe_name: str, project_id: str, steps) -> str:
        plan_steps = [
            WorkSessionStep(
                step_id=uuid.uuid4().hex[:8],
                title=step.title,
                description=step.instruction,
                step_type=step.step_type,
                requires_confirmation=step.requires_confirmation,
                allowed_to_run_automatically=False,
            )
            for step in steps
        ]
        plan = WorkSessionPlan(
            user_goal=f"workflow: {recipe_name}",
            steps=plan_steps,
            risk_level="medium",
            notes=["Linked workflow recipe. Existing safety systems still apply."],
        )
        session = self.work_sessions.create_session(project_id, f"workflow: {recipe_name}", plan)
        return session.session_id

    def _remember_workflow_event(self, run: WorkflowRun) -> None:
        content = f"Completed {run.recipe_name} workflow for Fibi v{APP_VERSION}."
        risk = self._memory_write_risk(content, source="workflow_recipe_engine")
        if risk is None:
            return
        try:
            self.memory_router.rag_memory.remember_event(
                content,
                importance=0.45,
                confidence=0.75,
                source="workflow_recipe_engine",
                source_id=f"workflow:{run.run_id}",
                metadata={"recipe_id": run.recipe_id, "summary_only": True, "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary}},
                provenance={"route": "workflow_recipe_engine", "full_logs_stored": False},
                allow_duplicate=True,
            )
        except Exception:
            LOGGER.exception("Failed to remember workflow completion")

    def _handle_help_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered in {"/help", "/beginner guide", "/what can you do"}:
            return self._local_response(self._beginner_help_text(), "happy", tts_priority="silent")
        if lowered in {"/help commands", "/commands"}:
            categories = ", ".join(self.command_registry.categories())
            return self._local_response("command shelves: " + categories + ". try /help search browser.", "thinking", tts_priority="silent")
        if lowered.startswith("/commands "):
            category = text[len("/commands "):].strip()
            commands = self.command_registry.by_category(category)
            return self._local_response(self.command_registry.format_results(commands), "thinking", tts_priority="silent")
        if lowered.startswith("/help search "):
            term = text[len("/help search "):].strip()
            return self._local_response(self.command_registry.format_results(self.command_registry.search(term)), "thinking", tts_priority="silent")
        if lowered.startswith("/help "):
            topic = text[len("/help "):].strip()
            command = self.command_registry.find(topic)
            if command:
                return self._local_response(self.command_registry.format_command(command), "thinking", tts_priority="silent")
            cap = self.capability_registry.find(topic, self._capability_status_overrides())
            if cap:
                return self._local_response(self.capability_registry.format_one(cap), "thinking", tts_priority="silent")
            return self._local_response("no help crumb for that. try /help search <word>.", "sleepy", tts_priority="silent")
        if lowered == "/capabilities":
            return self._local_response(self.capability_registry.format_list(self._capability_status_overrides()), "thinking", tts_priority="silent")
        if lowered.startswith("/capability "):
            cap = self.capability_registry.find(text[len("/capability "):].strip(), self._capability_status_overrides())
            return self._local_response(self.capability_registry.format_one(cap) if cap else "can't find that capability crumb.", "thinking", tts_priority="silent")
        if lowered == "/safety":
            return self._local_response(self.safety_explainer.safety_overview(), "sleepy", tts_priority="silent")
        if lowered == "/refusals":
            return self._local_response(self.safety_explainer.refusals(), "sleepy", tts_priority="silent")
        if lowered == "/confirmations":
            return self._local_response(self.safety_explainer.confirmations(), "thinking", tts_priority="silent")
        if lowered == "/permissions":
            return self._local_response(self._permissions_text(), "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _beginner_help_text(self) -> str:
        return (
            self.safety_explainer.what_can_you_do()
            + "\n"
            + self.command_registry.beginner_line()
        )

    def _permissions_text(self) -> str:
        overview = PermissionOverview(
            desktop_actions=self.action_settings.settings.allow_desktop_actions,
            project_checks=self.app_settings.settings.allow_project_checks,
            patch_apply=self.action_settings.settings.allow_file_modification,
            browser_helper=True,
            voice_input=self.voice_settings.settings.allow_voice_input,
            rvc_voice_skin=self.voice_skin_settings.settings.rvc_enabled,
            cloud=self.privacy.settings.allow_cloud_model or self.privacy.settings.allow_nvidia_api,
            memory_learning=self.privacy.settings.allow_memory_learning,
            beta_mode=self.app_settings.settings.beta_mode,
        )
        return self.permission_overview.format(overview)

    def _memory_health_short_line(self) -> str:
        try:
            health = self.memory_review.health(learning_status=self.memory_consent.status().summary)
        except Exception as exc:
            return f"memory review sleepy: {exc}"
        return (
            f"memory review: {health['total_memories']} total, "
            f"{health['approved_count']} approved, "
            f"{health['pending_sensitive_count']} pending."
        )

    def _capability_status_overrides(self) -> dict[str, dict[str, object]]:
        memory_health = self._memory_health_short_line()
        consent = self.memory_consent.summary_line()
        return {
            "chat": {"enabled": True, "status_summary": self.get_model_status()},
            "memory": {"enabled": self.memory_consent.state.memory_learning_enabled, "status_summary": consent},
            "memory_review": {"enabled": True, "status_summary": memory_health},
            "memory_consent": {"enabled": True, "status_summary": consent},
            "sensitive_memory_guard": {"enabled": True, "status_summary": "secrets blocked; sensitive notes require approval"},
            "rag_memory": {"enabled": True, "status_summary": memory_health},
            "voice_output": {"enabled": self.privacy.settings.allow_tts, "status_summary": "tts " + ("on" if self.privacy.settings.allow_tts else "off")},
            "voice_input": {"enabled": self.voice_settings.settings.allow_voice_input, "status_summary": "push-to-talk " + ("on" if self.voice_settings.settings.allow_voice_input else "off")},
            "rvc_voice_skin": {"enabled": self.voice_skin_settings.settings.rvc_enabled, "status_summary": "rvc " + ("on" if self.voice_skin_settings.settings.rvc_enabled else "off")},
            "desktop_actions": {"enabled": self.action_settings.settings.allow_desktop_actions, "status_summary": self.action_settings.summary_line()},
            "project_workspace": {"enabled": True, "status_summary": "project " + (self.project_workspace.current().name if self.project_workspace.current() else "none")},
            "patch_apply": {"enabled": True, "status_summary": "review required"},
            "project_checks": {"enabled": self.app_settings.settings.allow_project_checks, "status_summary": "checks " + ("on" if self.app_settings.settings.allow_project_checks else "off")},
            "browser_helper": {"enabled": True, "status_summary": self.browser_helper.status_line()},
            "workflow_recipes": {"enabled": True, "status_summary": self.workflow_recipes.status_line()},
            "issue_tracker": {"enabled": True, "status_summary": f"{self.issues.summary().get('open', 0)} open"},
            "feedback_capture": {"enabled": True, "status_summary": "local feedback"},
            "support_bundle": {"enabled": True, "status_summary": "masked local export"},
            "release_health": {"enabled": True, "status_summary": self.release_health.summary_line()},
            "update_manifest": {"enabled": True, "status_summary": self.updates.status_line()},
            "packaging_build_tools": {"enabled": True, "status_summary": "manual scripts only"},
        }

    def _browser_request_open(self, url: str) -> LocalCommandResult:
        request = self.browser_helper.request_open(url)
        if request is None:
            return self._local_response(self.browser_helper.last_safety_result.fibi_reply, "sleepy", tts_priority="silent")
        return self._local_response(f"browser doorway ready for {request.domain}. say: browser confirm", "thinking", tts_priority="silent")

    def _browser_summarize_last_context(self) -> LocalCommandResult:
        last = self.context_engine.last()
        if last is None:
            return self._local_response("paste page text first. i can't read a URL by staring at it.", "sleepy", tts_priority="silent")
        if _looks_like_url_only(last.content_text):
            return self._local_response("i only have the link, not the page. paste page text and i'll summarize.", "sleepy", tts_priority="silent")
        summary = self.browser_helper.summarize_user_text(last.content_text, last.title)
        return self._local_response("page crumbs: " + summary.summary, "thinking", tts_priority="silent")

    def _browser_research_from_context(self) -> LocalCommandResult:
        last = self.context_engine.last()
        if last is None:
            return LocalCommandResult(False)
        if _looks_like_url_only(last.content_text):
            return self._local_response("i only have the link. paste public page text for research notes.", "sleepy", tts_priority="silent")
        note = self.browser_helper.research_note(last.content_text, title=last.title)
        return self._local_response("research note: " + note.summary, "thinking", tts_priority="silent")

    def _install_status_line(self) -> str:
        info = runtime_info()
        mode = "packaged" if info.packaged else "dev"
        portable = "portable" if info.portable else "normal"
        return f"install status: {mode}. {portable}. data: {info.user_data_dir}."

    def _open_runtime_folder(self, folder: Path) -> str:
        result = self.desktop_actions.execute(ActionIntent("open_folder", target=str(folder)))
        return result.message if result.ok else f"couldn't open folder: {result.error or result.message}"

    def record_ui_error(self, where: str, error: Exception) -> None:
        self._last_error_summary = f"{where}: {error}"
        LOGGER.exception("gui_event_error", extra={"where": where})

    def get_model_status(self) -> str:
        cloud = "cloud on" if self.privacy.settings.allow_cloud_model and self.privacy.settings.allow_nvidia_api else "cloud off"
        return f"model {self.model_router.mode}. {cloud}. {self.health.status_line()}"

    def get_privacy_status(self) -> str:
        return self.privacy.summary_line()

    def get_settings(self):
        return self.app_settings.settings

    def update_settings(self, **values):
        return self.app_settings.update(**values)

    def nap(self) -> CreatureReaction:
        text, expression = self.life.start_nap()
        self._journal_record("nap_manual", self.life.mood, self.life.presence.value, text, emotional_weight=0.2, source="ui")
        return self._decorate_reaction(CreatureReaction(text, expression, "nap"), "nap")

    def wake(self) -> CreatureReaction | None:
        return self.handle_wake("manual")

    def health_check(self) -> str:
        data = self.data_health.check()
        assets = self.asset_health.check()
        return data.message if data.ok and assets.ok else f"{data.message} {assets.message}"

    def _start_warmup(self) -> None:
        self.warmup.start(
            [
                ("memory_db", lambda: self.memory.retrieve("", limit=1)),
                ("journal_db", lambda: self.journal.recent(limit=1)),
                ("state_save", lambda: self.life.save_state()),
                ("tts_probe", lambda: __import__("fibi.voice.speak").voice.speak.is_voice_available()),
            ]
        )

    def _mark_running(self) -> None:
        self.life._saved_state["clean_shutdown"] = False
        self.life._saved_state["unclean_shutdown_detected"] = self._unclean_shutdown_detected
        self.life.save_state()

    def _observe(self) -> Observation:
        observed = self.observation.observe(
            include_clipboard=self.privacy.settings.allow_clipboard_observation
        )
        return self.privacy.filter_observation(observed)

    def _journal_record(self, *args, **kwargs):
        if not self.privacy.settings.allow_journal:
            return None
        return self.journal.record(*args, **kwargs)

    def _local_response(
        self,
        text: str,
        mood: str = "idle",
        referenced_memory_id: int | None = None,
        tts_priority: str = "low",
    ) -> LocalCommandResult:
        if referenced_memory_id is not None:
            self._last_referenced_memory_id = referenced_memory_id
        timing = self.timing.select(event="reply", mood=mood, local=True)
        motion = self.motion.select(
            mood=mood,
            presence_state=self.life.presence.value,
            event="reply",
            time_of_day=self._observe().time_of_day,
        )
        print(f"TTS_PRIORITY: {tts_priority}")
        return LocalCommandResult(
            True,
            FibiResponse(text, tts_safe_text(text), mood, "local-command", False, timing, motion, tts_priority),
            referenced_memory_id,
        )

    @staticmethod
    def _log_reply_choice(
        event_source: str,
        fast_category: str,
        route_selected: str,
        thought_bubble_allowed: bool,
        provider_used: str,
        final_reply: str,
        local_brain_confidence: str = "n/a",
        local_brain_handled: bool | None = None,
        model_router_used: bool = False,
    ) -> None:
        LOGGER.info(
            "route_decision.reply_chosen",
            extra={
                "event_source": event_source,
                "fast_category": fast_category,
                "route_selected": route_selected,
                "thought_bubble_allowed": thought_bubble_allowed,
                "provider_used": provider_used,
                "model_router_used": model_router_used,
            },
        )
        print(f"EVENT_SOURCE: {event_source}")
        print(f"FAST_CATEGORY: {fast_category}")
        print(f"LOCAL_BRAIN_CONFIDENCE: {local_brain_confidence}")
        print(
            "LOCAL_BRAIN_HANDLED: "
            + ("n/a" if local_brain_handled is None else str(local_brain_handled).lower())
        )
        print(f"ROUTE_SELECTED: {route_selected}")
        print(f"MODEL_ROUTER_USED: {str(model_router_used).lower()}")
        print(f"THOUGHT_BUBBLE_ALLOWED: {str(thought_bubble_allowed).lower()}")
        print(f"PROVIDER_USED: {provider_used}")
        print(f"FINAL_REPLY: {final_reply}")

    @staticmethod
    def _log_route_decision(decision) -> None:
        LOGGER.info(
            "route_decision",
            extra={
                "route_name": decision.route_name,
                "reason": decision.reason,
                "provider_allowed": decision.provider_allowed,
                "model_router_allowed": decision.model_router_allowed,
                "local_action_allowed": decision.local_action_allowed,
                "expected_budget_ms": decision.expected_budget_ms,
            },
        )
        print(f"ROUTE_DECISION: {decision.route_name}")
        print(f"ROUTE_REASON: {decision.reason}")

    def _fast_greeting_response(self, user_message: str) -> FibiResponse:
        start = time.perf_counter()
        result = self.chat_router.local_reply("greeting", mood=self.life.mood, relationship=self.relationship.state)
        line = result.text or random.choice(FAST_GREETING_LINES)
        self.life.last_user_message = user_message
        self.life.interaction_count += 1
        self.life.total_interactions += 1
        self.life.last_interaction_time = time.monotonic()
        self.life.next_idle_reaction_time = self.life._next_idle_time()
        self.life.mark_seen(save=False)
        self.life.save_state()
        self.relationship.cool_down_annoyance(kind=True)
        self._journal_record(
            "fast_greeting",
            self.life.mood,
            self.life.presence.value,
            user_message[:80],
            emotional_weight=0.15,
            source="fast_reply_router",
        )
        duration = (time.perf_counter() - start) * 1000
        print("FAST_PATH_USED: true")
        print("PROVIDER_USED: local")
        print("MODEL_USED: local-greeting")
        print("FALLBACK_USED: false")
        print(f"FINAL_REPLY_TIME_MS: {duration:.1f}")
        print("TTS_PRIORITY: high")
        decision = self.route_decisions.decide(
            user_message,
            fast_category=self.chat_router.classify(user_message),
        )
        self._log_route_decision(decision)
        self._log_reply_choice(
            "user_message",
            "greeting",
            "fast-greeting",
            False,
            "local",
            line,
        )
        self.health.record_reply(duration, "local", fast_path=True, slowest_step="fast_greeting")
        return FibiResponse(
            line,
            tts_safe_text(line),
            "happy" if line in {"hi.", "back?"} else "idle",
            "local-greeting",
            False,
            self.timing.select(event="greeting", mood="happy", local=True),
            None,
            "high",
        )

    def _micro_response(self, category: str, user_message: str, time_of_day: str = "") -> FibiResponse:
        start = time.perf_counter()
        result = self.micro_brain.reply(category, self.life.mood, time_of_day, self.relationship.state, user_message)
        self.life.last_user_message = user_message
        self.life.interaction_count += 1
        self.life.total_interactions += 1
        self.life.last_interaction_time = time.monotonic()
        self.life.next_idle_reaction_time = self.life._next_idle_time()
        self.life.mark_seen(save=False)
        self.life.save_state()
        elapsed = (time.perf_counter() - start) * 1000
        print("FAST_PATH_USED: true")
        print("PROVIDER_USED: local")
        print("MODEL_USED: local-micro-brain")
        print("FALLBACK_USED: false")
        print(f"FINAL_REPLY_TIME_MS: {elapsed:.1f}")
        print("TTS_PRIORITY: high")
        decision = self.route_decisions.decide(
            user_message,
            fast_category=self.classifier.classify(user_message),
            local_micro_brain_result=result,
        )
        self._log_route_decision(decision)
        self._log_reply_choice(
            "user_message",
            category,
            "local-micro-brain",
            False,
            "local",
            result.text or "",
            result.confidence,
            result.handled,
            False,
        )
        self.health.record_reply(elapsed, "local", fast_path=True, slowest_step=category)
        return FibiResponse(
            result.text or "",
            tts_safe_text(result.text or ""),
            result.mood,
            "local-micro-brain",
            False,
            self.timing.select(event="reply", mood=result.mood, local=True),
            None,
            "high",
        )

    @staticmethod
    def _is_fast_greeting(user_message: str) -> bool:
        cleaned = re.sub(r"[.!?]+$", "", user_message.strip().lower())
        return cleaned in FAST_GREETINGS

    def _handle_local_command(self, user_message: str) -> LocalCommandResult:
        text = user_message.strip()
        lowered = text.lower()

        if lowered == "confirm project" and self._pending_project_path:
            return self._handle_project_command(text, lowered)

        if lowered in {"apply that", "apply it", "apply patch", "confirm apply patch", "apply patch confirm"}:
            return self._handle_patch_command(text, lowered)

        if lowered in {"run check confirm", "confirm run check"}:
            return self._handle_check_command(text, lowered)

        if lowered in {"browser confirm", "browser cancel"}:
            return self._handle_browser_command(text, lowered)

        if lowered in {"memory edit confirm", "memory delete confirm"}:
            return self._handle_memory_review_command(text, lowered)

        if lowered in {"workflow next", "workflow continue"}:
            return LocalCommandResult(True, self._workflow_continue())

        help_prompt = self._maybe_handle_help_prompt(text, lowered)
        if help_prompt.handled:
            return help_prompt

        beta_report = self._maybe_handle_beta_report_intent(text, lowered)
        if beta_report.handled:
            return beta_report

        browser_intent = self._maybe_handle_browser_prompt(text, lowered)
        if browser_intent.handled:
            return browser_intent

        workflow_intent = self._maybe_handle_workflow_prompt(text, lowered)
        if workflow_intent.handled:
            return workflow_intent

        session_response = self._maybe_handle_work_session_intent(text)
        if session_response is not None:
            return LocalCommandResult(True, session_response)

        if lowered.startswith("/"):
            return self._handle_slash_command(text)

        memory_prompt = self._maybe_handle_memory_prompt(text, lowered)
        if memory_prompt.handled:
            return memory_prompt

        if lowered in {"what do you remember about me?", "what do you remember about me"}:
            items = self.memory_review.list_memories(limit=8)
            if not items:
                return self._local_response("not much yet. tiny blank notebook.", "sleepy")
            categories = sorted({item.category for item in items})
            return self._local_response(
                "i remember " + ", ".join(categories[:3]).replace("_", " ") + ".",
                "thinking",
                items[0].memory_id if items else None,
            )

        if lowered.startswith("what do you remember about "):
            query = text.split("about", 1)[1].strip(" ?.")
            results = self.memory_review.search_memories(query, top_k=3)
            if not results:
                legacy = self.memory_care.search_memories(query, limit=3)
                if not legacy.entries:
                    return self._local_response("no crumb for that yet.", "sleepy")
                entry = legacy.entries[0]
                return self._local_response(
                    f"{query}: {entry.title}.",
                    "thinking",
                    int(entry.entry_id) if isinstance(entry.entry_id, int) else None,
                )
            entry = results[0].item
            return self._local_response(
                f"{query}: {entry.summary}.",
                "thinking",
                entry.memory_id,
            )

        if lowered in {"forget that", "forget it"}:
            if self._last_referenced_memory_id is None:
                return self._local_response("which crumb?", "thinking")
            self._pending_memory_delete = MemoryDeleteRequest(memory_id=self._last_referenced_memory_id, reason="natural_forget_that")
            return self._local_response("forget staged. say: memory delete confirm", "thinking")

        check_response = self.project_router.maybe_handle_check_intent(text)
        if check_response is not None:
            return LocalCommandResult(True, check_response)

        fix_response = self._maybe_handle_check_fix_intent(text)
        if fix_response is not None:
            return LocalCommandResult(True, fix_response)

        return LocalCommandResult(False)

    def _maybe_handle_help_prompt(self, text: str, lowered: str) -> LocalCommandResult:
        normalized = re.sub(r"\s+", " ", lowered.replace("\u2019", "'")).strip(" .!?")
        if normalized == "show commands":
            return self._local_response("command shelves: " + ", ".join(self.command_registry.categories()) + ". try /help search browser.", "thinking", tts_priority="silent")
        if normalized == "what can you do":
            return self._local_response(self._beginner_help_text(), "happy", tts_priority="silent")
        if normalized == "help me use fibi":
            return self._local_response(self.safety_explainer.beginner_guide(), "happy", tts_priority="silent")
        if normalized == "what is safe":
            return self._local_response(self.safety_explainer.safety_overview(), "sleepy", tts_priority="silent")
        if normalized == "what needs confirmation":
            return self._local_response(self.safety_explainer.confirmations(), "thinking", tts_priority="silent")
        if normalized == "what can you not do":
            return self._local_response(self.safety_explainer.refusals(), "sleepy", tts_priority="silent")
        return LocalCommandResult(False)

    def _maybe_handle_memory_prompt(self, text: str, lowered: str) -> LocalCommandResult:
        normalized = re.sub(r"\s+", " ", lowered.replace("\u2019", "'")).strip(" .!?")
        if normalized == "what do you remember":
            return self._handle_memory_review_command("/memories", "/memories")
        if normalized.startswith("search your memory for "):
            query = text.split("for", 1)[1].strip()
            return self._handle_memory_review_command(f"/memory search {query}", f"/memory search {query.lower()}")
        if normalized in {"pause memory", "stop memory", "memory off"}:
            return self._handle_memory_review_command("/memory learning off", "/memory learning off")
        if normalized in {"resume memory", "memory on", "start memory"}:
            return self._handle_memory_review_command("/memory learning on", "/memory learning on")
        if normalized == "export my memories":
            return self._handle_memory_review_command("/memory export", "/memory export")
        if normalized in {"is memory safe", "memory safety", "is your memory safe"}:
            return self._handle_memory_review_command("/memory safety", "/memory safety")
        if normalized == "forget this project note":
            self._pending_memory_delete = MemoryDeleteRequest(category="project", broad_delete=True, reason="natural_forget_project_note")
            return self._local_response("project memory delete staged. say: memory delete confirm", "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _maybe_handle_workflow_prompt(self, text: str, lowered: str) -> LocalCommandResult:
        normalized = re.sub(r"\s+", " ", lowered.replace("\u2019", "'")).strip(" .!?")
        prompt_map = {
            "start debug workflow": "Debug Failed Project",
            "guide me through release": "Safe Release Build",
            "do beta qa": "Beta QA Pass",
            "help me review this website": "Website Review / Outreach Research",
            "make a bug report workflow": "Bug Report Support Bundle",
            "daily startup check": "Daily Fibi Startup Check",
        }
        recipe_name = prompt_map.get(normalized)
        if recipe_name is None:
            return LocalCommandResult(False)
        recipe = self.workflow_recipes.get_recipe(recipe_name)
        if recipe is None:
            return self._local_response("recipe crumb missing.", "sleepy", tts_priority="silent")
        return self._local_response(
            self.workflow_recipes.recipe_summary(recipe) + f"\nsay: /workflow start {recipe.name}",
            "thinking",
            tts_priority="silent",
        )

    def _maybe_handle_beta_report_intent(self, text: str, lowered: str) -> LocalCommandResult:
        normalized = re.sub(r"\s+", " ", lowered.replace("\u2019", "'")).strip(" .!?")
        if normalized in {"report a bug", "make a bug report"}:
            return self._local_response("bug jar opened. tell me what squeaked.", "thinking", tts_priority="silent")
        if normalized == "beta feedback":
            return self._local_response("feedback jar opened. use /feedback new <note>.", "thinking", tts_priority="silent")
        triggers = (
            "something broke",
            "fibi crashed",
            "voice is broken",
            "rvc is not working",
            "rvc isn't working",
        )
        if not any(trigger in normalized for trigger in triggers):
            return LocalCommandResult(False)
        payload = self.secret_sanitizer.sanitize(text)
        issue = self.issues.create(
            payload[:120] or "beta issue",
            payload,
            category=_guess_issue_category(payload),
            severity=_guess_issue_severity(payload),
            tags=["beta", "natural_language"],
            last_route_decision_summary=self._last_route_summary(),
            health_snapshot_summary=self._safe_health_snapshot(),
        )
        return self._local_response(f"issue saved. tiny detective mode. {issue.issue_id}.", "thinking", tts_priority="silent")

    def _maybe_handle_browser_prompt(self, text: str, lowered: str) -> LocalCommandResult:
        normalized = re.sub(r"\s+", " ", lowered.replace("\u2019", "'")).strip(" .!?")
        safety = self.browser_safety.classify_request(normalized)
        self.browser_helper.last_safety_result = safety
        if safety.blocked:
            return self._local_response(safety.fibi_reply, "sleepy", tts_priority="silent")
        if normalized in {"summarize this page", "summarise this page"}:
            return self._browser_summarize_last_context()
        if normalized.startswith("open this website") or normalized.startswith("open this link"):
            url = _extract_first_url(text)
            if not url:
                return self._local_response("give me the link crumb with it.", "thinking", tts_priority="silent")
            return self._browser_request_open(url)
        if normalized.startswith("save this link"):
            url = _extract_first_url(text)
            if not url:
                return self._local_response("give me the link crumb and note.", "thinking", tts_priority="silent")
            note_text = text.replace(url, "").strip() or "saved link"
            saved = self.browser_helper.save_url_note(url, note_text)
            return self._local_response(f"saved link crumb: {saved.title}." if saved else self.browser_helper.last_safety_result.fibi_reply, "thinking", tts_priority="silent")
        if normalized in {"help me research this", "make a browser checklist", "plan what to do on this site", "help me contact this business"}:
            if "contact" in normalized or "research" in normalized:
                result = self._browser_research_from_context()
                if result.handled:
                    return result
            plan = self.browser_helper.plan(text)
            return self._local_response("browser checklist: " + "; ".join(plan.steps[:5]) + ".", "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _handle_session_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered.startswith("/session start "):
            goal = text[len("/session start "):].strip()
            return self._local_response(self._start_work_session(goal), "thinking")
        if lowered in {"/session current", "/session summary"}:
            return self._local_response(self._format_work_session_current(), "thinking", tts_priority="silent")
        if lowered in {"/session continue", "/session next"}:
            return LocalCommandResult(True, self._continue_work_session())
        if lowered == "/session pause":
            session = self.work_sessions.pause()
            return self._local_response("paused. tiny clipboard brain closed." if session else "no session crumb.", "sleepy", tts_priority="silent")
        if lowered == "/session resume":
            session = self.work_sessions.resume()
            return self._local_response("session awake-ish." if session else "no session crumb.", "thinking", tts_priority="silent")
        if lowered == "/session cancel":
            session = self.work_sessions.cancel()
            return self._local_response("session sleeping." if session else "no session crumb.", "sleepy", tts_priority="silent")
        if lowered == "/session history":
            rows = self.work_sessions.summaries(limit=5)
            if not rows:
                return self._local_response("no session footprints yet.", "sleepy", tts_priority="silent")
            bits = [f"{row.status}: {row.user_goal[:32]} ({row.completed_count}/{row.total_steps})" for row in rows[-3:]]
            return self._local_response("session footprints. " + "; ".join(bits) + ".", "thinking", tts_priority="silent")
        if lowered == "/session clear completed":
            count = self.work_sessions.clear_completed()
            return self._local_response(f"cleared {count} done-ish session crumb(s).", "sleepy", tts_priority="silent")
        return LocalCommandResult(False)

    def _maybe_handle_work_session_intent(self, text: str) -> FibiResponse | None:
        lowered = " ".join(text.lower().strip().split())
        if lowered in {"continue", "what's next?", "whats next", "what's next", "resume the task"}:
            return self._continue_work_session()
        if lowered in {"stop this task", "cancel this task"}:
            session = self.work_sessions.cancel()
            return self._local_response("session sleeping." if session else "no session crumb.", "sleepy").response
        starts = ("help me fix this", "guide me through this", "make a plan", "help me fix this project")
        if lowered.startswith(starts):
            return self._local_response(self._start_work_session(text), "thinking").response
        return None

    def _start_work_session(self, goal: str) -> str:
        project = self.project_workspace.current()
        plan = self.work_planner.plan(goal, project)
        project_id = project.project_id if project else ""
        session = self.work_sessions.create_session(project_id, goal, plan)
        first = self.work_sessions.current_step(session)
        title = first.title if first else "done"
        return f"tiny plan made.\nstep 1: {title}.\nsay: continue"

    def _continue_work_session(self) -> FibiResponse:
        session = self.work_sessions.active()
        if session is None:
            return self._local_response("no session crumb. use /session start <goal>.", "sleepy").response
        if session.status == "paused":
            return self._local_response("session sleeping. say /session resume.", "sleepy").response
        step = self.work_sessions.current_step(session)
        if step is None:
            completed = self.work_sessions.complete("Guided session completed.")
            if completed:
                self._remember_session_event(completed)
            return self._local_response("done-ish.", "happy").response
        decision = self.work_step_runner.run(step)
        if decision.allowed and not decision.waiting_for_user:
            self.work_sessions.mark_step(step, "completed", decision.message)
            if step.step_type == "done":
                completed = self.work_sessions.complete(decision.message)
                if completed:
                    self._remember_session_event(completed)
            return self._local_response(decision.message + self._next_step_suffix(), "thinking").response
        if decision.allowed and decision.waiting_for_user:
            self.work_sessions.mark_step(step, "completed", decision.message)
            return self._local_response(decision.message + self._next_step_suffix(), "thinking").response
        step.status = "blocked"
        step.result_summary = decision.message
        session.pending_action_type = step.step_type
        session.pending_confirmation = decision.message
        self.work_sessions.mark_step(step, "blocked", decision.message)
        return self._local_response(decision.message, "thinking").response

    def _format_work_session_current(self) -> str:
        progress = self.work_sessions.progress()
        if progress is None:
            return "no session crumb."
        current = progress.current_step.title if progress.current_step else "done"
        return f"session: {progress.summary} next crumb: {current}."

    def session_status_chip(self) -> str:
        progress = self.work_sessions.progress()
        if progress is None or progress.status not in {"active", "paused"}:
            return ""
        current = progress.current_step.title if progress.current_step else "done"
        return f"{progress.status}: {current}"

    def _next_step_suffix(self) -> str:
        progress = self.work_sessions.progress()
        if progress is None or progress.current_step is None:
            return ""
        return f"\nnext crumb: {progress.current_step.title}.\nsay: continue"

    def _session_project_summary(self) -> str:
        summary = self.project_workspace.summary()
        if summary is None:
            return "no project nest."
        stack = ", ".join(summary.detected_stack) if summary.detected_stack else "unknown stack"
        files = ", ".join(summary.important_files[:5]) if summary.important_files else "no obvious important files"
        return f"project crumb: {summary.name}. stack: {stack}. important: {files}."

    def _session_check_analysis(self) -> str:
        analysis = self._analyze_last_failed_check()
        if analysis is None:
            return "no failed check crumb yet."
        return self._format_failure_analysis(analysis)

    def _session_suggest_fix(self) -> str:
        return "need permission. say: /check suggest fix"

    def _remember_session_event(self, session) -> None:
        project = self.project_workspace.current()
        project_name = project.name if project else "project"
        summary = f"Worked on {project_name} task: {session.user_goal[:120]}. {len(session.completed_steps)}/{len(session.steps)} steps completed."
        risk = self._memory_write_risk(summary, source="work_session_engine")
        if risk is None:
            return
        try:
            self.memory_router.rag_memory.remember_event(
                summary,
                importance=0.45,
                confidence=0.7,
                source="work_session_engine",
                source_id=f"session:{session.session_id}",
                metadata={"project_id": session.project_id, "project_name": project_name, "status": session.status, "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary}},
                provenance={"route": "ProjectRouter", "full_code_stored": False, "full_output_stored": False},
                allow_duplicate=True,
            )
        except Exception:
            LOGGER.exception("Failed to remember work session event")

    def _handle_action_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered in {"/actions", "/actions status"}:
            return self._local_response(self.action_settings.summary_line(), "thinking")
        if lowered == "/actions on":
            self.action_settings.update(allow_desktop_actions=True)
            return self._local_response("safe hands on.", "happy")
        if lowered == "/actions off":
            self.action_settings.update(allow_desktop_actions=False)
            return self._local_response("hands tucked away.", "sleepy")
        if lowered == "/apps refresh":
            count = self.app_index.refresh()
            return self._local_response(f"app crumbs refreshed. found {count} creatures.", "thinking")
        if lowered == "/apps count":
            return self._local_response(f"found {self.app_index.count()} app creatures.", "thinking")
        if lowered.startswith("/apps search "):
            query = text[len("/apps search "):].strip()
            result = self.app_index.search(query)
            if not result.matches:
                return self._local_response("couldn't find that creature.", "sleepy")
            return self._local_response("i know " + ", ".join(entry.display_name for entry in result.matches[:3]) + ".", "happy")
        if lowered == "/pending action":
            pending = self.action_confirmations.pending()
            if pending is None:
                return self._local_response("no danger button waiting.", "sleepy")
            return self._local_response(f"pending {pending.action_type}. say: {pending.required_confirmation_phrase}", "thinking")
        if lowered == "/cancel action":
            cancelled = self.action_confirmations.cancel()
            return self._local_response("danger button canceled." if cancelled else "nothing scary pending.", "sleepy")
        if lowered == "/screenshots status":
            return self._local_response("screenshots on." if self.action_settings.settings.allow_screenshot else "screenshots off.", "thinking")
        if lowered == "/screenshots on confirm":
            self.action_settings.update(allow_screenshot=True)
            return self._local_response("screenshots armed. still asks first.", "thinking")
        if lowered == "/screenshots off":
            self.action_settings.update(allow_screenshot=False)
            return self._local_response("screenshots off.", "sleepy")
        if lowered == "/shutdown actions status":
            return self._local_response("shutdown armed." if self.action_settings.settings.allow_shutdown else "shutdown off.", "thinking")
        if lowered == "/shutdown actions on confirm":
            self.action_settings.update(allow_shutdown=True)
            return self._local_response("shutdown armed. still asks first.", "thinking")
        if lowered == "/shutdown actions off":
            self.action_settings.update(allow_shutdown=False)
            return self._local_response("shutdown off.", "sleepy")
        return LocalCommandResult(False)

    def _handle_voice_command(self, text: str, lowered: str) -> LocalCommandResult:
        skin = self._handle_voice_skin_command(text, lowered)
        if skin.handled:
            return skin
        if lowered == "/voice input on confirm":
            self.voice_settings.update(allow_voice_input=True, push_to_talk_enabled=True, wake_word_enabled=False)
            return self._local_response("ears enabled. push-to-talk only.", "happy")
        if lowered == "/voice input off":
            self.voice_settings.update(allow_voice_input=False)
            return self._local_response("ears tucked away.", "sleepy")
        if lowered == "/voice status":
            return self._local_response(self.get_voice_status(), "thinking")
        if lowered == "/listen":
            return LocalCommandResult(True, self.start_voice_listen(source="slash_command"))
        if lowered == "/mic devices":
            devices = self.speech_recognition.devices()
            if not devices:
                return self._local_response("mic creature missing.", "sleepy")
            names = ", ".join(device.name for device in devices[:3])
            return self._local_response(f"mic creatures: {names}.", "thinking")
        if lowered == "/mic test":
            return self._local_response(self.voice_health.mic_test(self.voice_settings.settings), "thinking")
        if lowered in {"/wake word status", "/wake word off"}:
            if lowered == "/wake word off":
                self.voice_settings.update(wake_word_enabled=False)
            return self._local_response("wake word sleeping.", "sleepy")
        return LocalCommandResult(False)

    def _handle_voice_skin_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/voice skin status":
            return self._local_response(self._voice_skin_status_text(), "thinking", tts_priority="silent")
        if lowered == "/voice skin on confirm":
            self.voice_skin_settings.update(allow_rvc_voice_skin=True, rvc_enabled=True)
            validation = self.rvc_voice_skin.validate(self.voice_skin_settings.settings)
            return self._local_response("voice skin ready." if validation.ok else f"voice skin tripped. {validation.message}.", "thinking")
        if lowered == "/voice skin off":
            self.voice_skin_settings.update(rvc_enabled=False, allow_rvc_voice_skin=False)
            return self._local_response("voice skin off.", "sleepy", tts_priority="silent")
        if lowered.startswith("/voice skin model "):
            path = text[len("/voice skin model "):].strip().strip('"')
            resolved = VoiceSkinSettingsEngine.resolve_path(path)
            self.voice_skin_settings.update(rvc_model_path=str(resolved))
            ok = resolved.exists() and resolved.suffix.lower() == ".pth"
            return self._local_response("model crumb found." if ok else "model crumb missing.", "thinking")
        if lowered.startswith("/voice skin index "):
            path = text[len("/voice skin index "):].strip().strip('"')
            resolved = VoiceSkinSettingsEngine.resolve_path(path)
            self.voice_skin_settings.update(rvc_index_path=str(resolved))
            ok = resolved.exists() and resolved.suffix.lower() == ".index"
            return self._local_response("index crumb found." if ok else "index crumb missing.", "thinking")
        if lowered.startswith("/voice skin pitch "):
            raw = text[len("/voice skin pitch "):].strip()
            try:
                value = int(raw)
            except ValueError:
                return self._local_response("pitch needs a number.", "thinking")
            self.voice_skin_settings.update(rvc_pitch_shift=max(-24, min(24, value)))
            return self._local_response(f"pitch crumb {self.voice_skin_settings.settings.rvc_pitch_shift}.", "thinking")
        if lowered.startswith("/voice skin backend "):
            backend = lowered[len("/voice skin backend "):].strip()
            self.voice_skin_settings.update(rvc_backend=backend)
            return self._local_response(f"voice skin backend {self.voice_skin_settings.settings.rvc_backend}.", "thinking")
        if lowered == "/voice skin test":
            return self._local_response(self._run_voice_skin_test(), "thinking", tts_priority="silent")
        if lowered == "/voice cache clear":
            count = self.voice_cache.clear()
            return self._local_response(f"voice cache cleared {count} crumbs.", "sleepy", tts_priority="silent")
        if lowered == "/voice cache status":
            return self._local_response(self.voice_cache.status_line(), "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _voice_skin_status_text(self) -> str:
        status = self.rvc_voice_skin.status(self.voice_skin_settings.settings)
        return (
            "voice skin status:\n"
            f"rvc_enabled: {str(status['rvc_enabled']).lower()}\n"
            f"backend: {status['backend']}\n"
            f"model path exists: {str(status['model_path_exists']).lower()}\n"
            f"index path exists: {str(status['index_path_exists']).lower()}\n"
            f"backend available: {str(status['backend_available']).lower()}\n"
            f"last RVC error: {status['last_rvc_error']}\n"
            f"fallback reason: {status['fallback_reason']}\n"
            f"next step: {status['backend_hint']}"
        )

    def _run_voice_skin_test(self) -> str:
        from fibi.voice.speak import is_voice_available, play_audio, prepare_voice_output

        if not is_voice_available():
            self.rvc_voice_skin.last_fallback_reason = "edge-tts or pygame unavailable"
            return "voice test fallback: edge-tts or pygame unavailable."

        output = prepare_voice_output(
            "eepy voice test.",
            self.voice_skin_settings.settings,
            self.rvc_voice_skin,
            self.voice_cache,
        )
        if output.final_audio_path:
            print(f"FINAL_AUDIO_PLAYED_PATH: {output.final_audio_path}")
            play_audio(output.final_audio_path)
        if output.base_audio_path:
            try:
                output.base_audio_path.unlink()
            except OSError:
                pass
        if output.converted:
            return "voice skin test converted. tiny new voice used."
        reason = output.fallback_reason or self.rvc_voice_skin.last_fallback_reason or "unknown"
        return f"voice skin test used fallback. reason: {reason}."

    def _handle_context_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/context":
            return self._local_response(self.context_status(), "thinking")
        if lowered == "/context privacy":
            return self._local_response("only what you hand me. no clipboard sneaking. no screen eyes.", "sleepy")
        if lowered == "/context clear":
            self.context_engine.clear()
            return self._local_response("cleared the crumbs.", "sleepy")
        if lowered == "/context last":
            last = self.context_engine.last()
            if last is None:
                return self._local_response("no context crumbs.", "sleepy")
            return self._local_response(f"{last.title}: {last.content_preview[:180]}", "thinking")
        if lowered == "/context forget last":
            return self._local_response("forgot the last crumb." if self.context_engine.forget_last() else "no context crumbs.", "sleepy")
        if lowered == "/context remember last confirm":
            decision = self.context_engine.remember_last()
            if not decision.should_remember:
                return self._local_response("no crumb to remember.", "sleepy")
            content = "User-provided context summary: " + decision.summary[:700]
            risk = self._memory_write_risk(content, source="context_confirmed", user_requested=True)
            if risk is None:
                return self._local_response("memory paused.", "sleepy", tts_priority="silent")
            self.memory_router.rag_memory.remember_event(
                content,
                importance=0.45,
                confidence=0.6,
                source="context_confirmed",
                metadata={"remembered_summary_only": True, "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary}},
                provenance={"route": "context_router", "user_confirmed": True},
            )
            # Compatibility during the RAG cutover: older memory-care tests and
            # commands still inspect the legacy memories table directly.
            self.memory.save(
                MemoryCategory.EVENT,
                content,
                importance=0.45,
                source="context_confirmed",
                metadata={"remembered_summary_only": True, "compatibility_write": True},
            )
            return self._local_response("saved a tiny summary, not the whole thing.", "happy")
        if lowered.startswith("/context add "):
            content = text[len("/context add "):].strip()
            if not content:
                return self._local_response("give me the crumb after /context add.", "thinking")
            self.context_engine.add_text(content, "manual_selected_text", "selected text")
            return self._local_response("context crumb held.", "thinking")
        return LocalCommandResult(False)

    def _handle_route_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/route last":
            return self._local_response(self.route_decisions.last_line(), "thinking", tts_priority="silent")
        if lowered.startswith("/route test "):
            message = text[len("/route test "):].strip()
            if not message:
                return self._local_response("route test needs words.", "thinking", tts_priority="silent")
            intent = self.action_intents.detect(message, direct_user_initiated=True)
            category = self.chat_router.classify(message)
            decision = self.route_decisions.test_message(
                message,
                intent,
                category,
                self.health.provider_allowed("ollama"),
            )
            suffix = f"/{decision.action_type}" if decision.action_type else ""
            return self._local_response(
                f"would route: {decision.route_name}{suffix}. model: {'yes' if decision.model_router_allowed else 'no'}.",
                "thinking",
                tts_priority="silent",
            )
        return LocalCommandResult(False)

    def _handle_project_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "confirm project" and self._pending_project_path:
            path = self._pending_project_path
            self._pending_project_path = None
            result = self.project_workspace.add_workspace(path)
            if not result.ok:
                return self._local_response(result.message or "project nest resisted.", "sleepy")
            return self._local_response("project nest added.", "happy")
        if lowered.startswith("/project add "):
            path = text[len("/project add "):].strip().strip('"')
            result = self.project_workspace.add_workspace(path)
            if not result.ok:
                return self._local_response(result.message or "project nest resisted.", "sleepy")
            stack = " + ".join(result.workspace.detected_stack) if result.workspace else "unknown"
            return self._local_response(f"project nest added. this one smells like {stack}.", "happy")
        if lowered == "/project list":
            projects = self.project_workspace.list_workspaces()
            if not projects:
                return self._local_response("no project nests yet.", "sleepy")
            return self._local_response("project nests: " + ", ".join(project.name for project in projects[:6]) + ".", "thinking")
        if lowered == "/project current":
            project = self.project_workspace.current()
            return self._local_response(f"current nest: {project.name}." if project else "no project nest.", "thinking")
        if lowered.startswith("/project switch "):
            project = self.project_workspace.switch(text[len("/project switch "):].strip())
            return self._local_response(f"nest switched: {project.name}." if project else "couldn't find that nest.", "thinking")
        if lowered == "/project scan":
            result = self.project_workspace.scan_current()
            if not result.ok:
                return self._local_response(result.message or "scan failed.", "sleepy")
            stack = " + ".join(result.workspace.detected_stack) if result.workspace else "unknown"
            return self._local_response(f"found code crumbs. {stack}.", "thinking")
        if lowered == "/project files":
            files = [entry.relative_path for entry in self.project_workspace.files() if entry.safe_to_read][:10]
            return self._local_response("files: " + ", ".join(files) + "." if files else "no safe file crumbs.", "thinking")
        if lowered.startswith("/project search "):
            matches = self.project_workspace.search(text[len("/project search "):].strip())
            return self._local_response("matches: " + ", ".join(entry.relative_path for entry in matches[:8]) + "." if matches else "no matching crumbs.", "thinking")
        if lowered.startswith("/project read "):
            rel = text[len("/project read "):].strip()
            result = self.project_workspace.read_file(rel)
            if not result.ok:
                return self._local_response(result.message or "can't chew that file yet.", "sleepy")
            return self._local_response(f"reading that file crumb: {rel}.", "thinking")
        if lowered == "/project summary":
            summary = self.project_workspace.summary()
            if summary is None:
                return self._local_response("no project nest.", "sleepy")
            return self._local_response(summary.summary, "thinking")
        if lowered.startswith("/project forget ") and lowered.endswith(" confirm"):
            name = text[len("/project forget "):-len(" confirm")].strip()
            return self._local_response("project nest forgotten." if self.project_workspace.forget(name) else "couldn't find that nest.", "sleepy")
        if lowered.startswith("/project forget "):
            return self._local_response("project forget needs confirm.", "thinking")
        if lowered.startswith("/project note "):
            note = text[len("/project note "):].strip()
            if not note:
                return self._local_response("note crumb empty.", "thinking")
            ok = self.project_workspace.note(note)
            if ok:
                project = self.project_workspace.current()
                self.memory.save(
                    MemoryCategory.PROJECT,
                    f"Project note for {project.name if project else 'project'}: {note[:500]}",
                    importance=0.5,
                    source="project_workspace_note",
                    metadata={"summary_only": True},
                )
            return self._local_response("project note tucked away." if ok else "no project nest.", "happy" if ok else "sleepy")
        if lowered == "/project open vscode":
            project = self.project_workspace.current()
            if project is None:
                return self._local_response("no project nest.", "sleepy")
            result = self.desktop_actions.execute(ActionIntent("open_app", target="code", raw_text=text))
            if not result.ok:
                result = self.desktop_actions.execute(ActionIntent("open_app", target="vscode", raw_text=text))
            return self._local_response("opening the project nest." if result.ok else "couldn't find VS Code creature.", "happy" if result.ok else "sleepy")
        if lowered == "/project privacy":
            return self._local_response("registered nests only. no edits without exact confirm. low/medium patches only. no terminal. no secret crumbs.", "sleepy")
        return LocalCommandResult(False)

    def _handle_edit_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/edit safety":
            return self._local_response(
                "edit paws can suggest. patch paws need backup and exact confirm. no terminal, no secret crumbs.",
                "sleepy",
            )
        if lowered == "/edit clear":
            self.project_edit_planner.clear_last()
            return self._local_response("edit crumb cleared.", "sleepy")
        if lowered == "/edit explain last":
            return self._local_response(self.project_edit_planner.explain_last(), "thinking")
        if lowered == "/edit copy last":
            return self._local_response(self.project_edit_planner.copy_last(), "thinking")
        if lowered.startswith("/edit plan "):
            request = text[len("/edit plan "):].strip()
            if not request:
                return self._local_response("what edit crumb?", "thinking")
            result = self.project_edit_planner.plan(request, source="slash_command")
            return self._local_response(self._maybe_prepare_patch(result), "thinking" if result.ok else "sleepy")
        if lowered.startswith("/edit file "):
            rest = text[len("/edit file "):].strip()
            parts = rest.split(maxsplit=1)
            if len(parts) < 2:
                return self._local_response("use /edit file path request.", "thinking")
            relative_path, request = parts[0].strip().replace("\\", "/"), parts[1].strip()
            result = self.project_edit_planner.plan(request, [relative_path], source="slash_command")
            return self._local_response(self._maybe_prepare_patch(result), "thinking" if result.ok else "sleepy")
        return LocalCommandResult(False)

    def _handle_patch_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/patch safety":
            return self._local_response(
                "patch paws: low/medium only, backup first, exact confirm. high risk is manual only.",
                "sleepy",
                tts_priority="silent",
            )
        if lowered in {"/patch pending", "apply patch", "apply that", "apply it"}:
            pending = self.patch_confirmations.pending()
            if pending is None:
                return self._local_response("no patch crumb waiting.", "sleepy", tts_priority="silent")
            return self._local_response(self._format_patch_summary(pending.patch), "thinking", tts_priority="silent")
        if lowered in {"/patch apply confirm", "confirm apply patch", "apply patch confirm"}:
            pending = self.patch_confirmations.pending()
            if pending is None:
                return self._local_response("no patch crumb waiting.", "sleepy")
            result = self.patch_engine.apply(pending.patch)
            self.patch_history.record_apply(pending.patch, result)
            if result.ok:
                self._last_applied_patch = pending.patch
                self.patch_confirmations.cancel()
                self._remember_patch_event(pending.patch, result.applied_files)
            message = result.message
            if result.ok and self.app_settings.settings.auto_suggest_check_after_patch:
                message += " want me to run a safe check?"
            return self._local_response(message, "happy" if result.ok else "sleepy")
        if lowered == "/patch cancel":
            cancelled = self.patch_confirmations.cancel()
            return self._local_response("patch crumb canceled." if cancelled else "no patch crumb waiting.", "sleepy", tts_priority="silent")
        if lowered == "/patch rollback last":
            patch = getattr(self, "_last_applied_patch", None)
            if patch is None:
                return self._local_response("no rollback crumb in this session.", "sleepy", tts_priority="silent")
            result = self.patch_engine.rollback(patch)
            self.patch_history.record_rollback(patch, result)
            return self._local_response(result.message, "happy" if result.ok else "sleepy")
        if lowered == "/patch history":
            rows = self.patch_history.recent(limit=5)
            if not rows:
                return self._local_response("no patch footprints yet.", "sleepy", tts_priority="silent")
            bits = [f"{row.get('event')}: {', '.join(row.get('patch', {}).get('files', [])[:2])}" for row in rows[-3:]]
            return self._local_response("patch footprints. " + "; ".join(bits) + ".", "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    def _handle_check_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered == "/check safety":
            return self._local_response(
                "check paws are whitelisted. shell off. no install, git, delete, deploy, or migrations.",
                "sleepy",
                tts_priority="silent",
            )
        if lowered == "/check presets":
            project = self.project_workspace.current()
            if project is None:
                return self._local_response("no project nest for checks.", "sleepy", tts_priority="silent")
            presets = self.check_presets.presets_for(project)
            if not presets:
                return self._local_response("no safe check crumbs found.", "sleepy", tts_priority="silent")
            names = ", ".join(preset.command_key for preset in presets[:8])
            return self._local_response(f"safe checks: {names}.", "thinking", tts_priority="silent")
        if lowered.startswith("/check run "):
            project = self.project_workspace.current()
            if project is None:
                return self._local_response("no project nest for checks.", "sleepy")
            preset_name = text[len("/check run "):].strip()
            preset = self.check_presets.find(project, preset_name)
            if preset is None:
                return self._local_response("unknown check crumb. use /check presets.", "sleepy")
            return self._local_response(self._create_pending_check(preset), "thinking")
        if lowered == "/check pending":
            pending = self.check_confirmations.pending()
            if pending is None:
                return self._local_response("no check crumb waiting.", "sleepy", tts_priority="silent")
            return self._local_response(self._format_check_pending(pending), "thinking", tts_priority="silent")
        if lowered in {"/check confirm", "run check confirm", "confirm run check"}:
            return LocalCommandResult(True, self._run_pending_check())
        if lowered == "/check cancel":
            cancelled = self.check_confirmations.cancel()
            return self._local_response("check crumb canceled." if cancelled else "no check crumb waiting.", "sleepy", tts_priority="silent")
        if lowered == "/check last":
            result = getattr(self, "_last_check_result", None)
            if result is None:
                return self._local_response("no check footprints this session.", "sleepy", tts_priority="silent")
            return self._local_response(self._format_check_result(result), "thinking", tts_priority="silent")
        if lowered == "/check history":
            rows = self.check_history.recent(limit=5)
            if not rows:
                return self._local_response("no check footprints yet.", "sleepy", tts_priority="silent")
            bits = [f"{row.get('command_key')}: exit {row.get('exit_code')} - {row.get('summary')}" for row in rows[-3:]]
            return self._local_response("check footprints. " + "; ".join(bits) + ".", "thinking", tts_priority="silent")
        if lowered == "/check output last":
            result = getattr(self, "_last_check_result", None)
            if result is None or not result.output_path:
                return self._local_response("no output crumb yet.", "sleepy", tts_priority="silent")
            output_dir = Path(result.output_path)
            stdout = self._read_check_output_preview(output_dir / "stdout.txt")
            stderr = self._read_check_output_preview(output_dir / "stderr.txt")
            preview = "\n".join(part for part in [stdout, stderr] if part).strip()
            return self._local_response(preview or "output crumb was empty.", "thinking", tts_priority="silent")
        if lowered in {"/check analyze last", "/fix explain"}:
            analysis = self._analyze_last_failed_check()
            if analysis is None:
                return self._local_response("no failed check crumb to analyze.", "sleepy", tts_priority="silent")
            if lowered == "/fix explain" and self._last_check_fix_plan is not None:
                return self._local_response(self._format_fix_plan(self._last_check_fix_plan), "thinking", tts_priority="silent")
            return self._local_response(self._format_failure_analysis(analysis), "thinking", tts_priority="silent")
        if lowered in {"/check suggest fix", "/check fix last", "/fix last check"}:
            return LocalCommandResult(True, self._suggest_fix_for_last_check())
        if lowered == "/fix clear":
            self._last_check_fix_plan = None
            self._pending_fix_suggestion = None
            return self._local_response("fix crumb cleared.", "sleepy", tts_priority="silent")
        return LocalCommandResult(False)

    def _maybe_handle_project_check_intent(self, user_message: str) -> FibiResponse | None:
        if not self.app_settings.settings.allow_project_checks:
            return None
        project = self.project_workspace.current()
        if project is None:
            return None
        preset = self.check_presets.detect_intent(user_message, project)
        if preset is None:
            return None
        response = self._local_response(self._create_pending_check(preset), "thinking", tts_priority="silent").response
        if response is not None:
            self._log_reply_choice(
                "user_message",
                "local_project_check",
                "project-check-pending",
                False,
                "local",
                response.display_text,
                "high",
                True,
                False,
            )
        return response

    def _maybe_handle_check_fix_intent(self, user_message: str) -> FibiResponse | None:
        lowered = " ".join(user_message.lower().strip().split())
        triggers = {
            "fix the check",
            "why did it fail",
            "why did it fail?",
            "suggest a fix",
            "can you fix the build",
            "can you fix the build?",
            "fix the tests",
            "fix last check",
        }
        if lowered in triggers:
            return self._suggest_fix_for_last_check()
        return None

    def _analyze_last_failed_check(self):
        result = getattr(self, "_last_check_result", None)
        if result is None or result.exit_code == 0:
            return None
        output_result = self._hydrate_check_result_output(result)
        analysis = self.check_failure_analyzer.analyze(output_result)
        self._last_check_failure_analysis = analysis
        return analysis

    def _suggest_fix_for_last_check(self) -> FibiResponse:
        analysis = self._analyze_last_failed_check()
        if analysis is None:
            return self._local_response("no failed check crumb to fix.", "sleepy").response
        resolver = RelatedFileResolver(self.project_workspace)
        candidates = resolver.resolve(analysis)
        plan = self.check_fix_planner.plan(analysis, candidates, "fix last check")
        self._last_check_fix_plan = plan
        if plan.refused_reason:
            return self._local_response(self._format_fix_plan(plan), "thinking").response
        if plan.edit_suggestion is None:
            return self._local_response("i see the scream, not the source.", "sleepy").response
        patch, risk = self.patch_engine.create_plan_from_suggestion(plan.edit_suggestion)
        if patch is None:
            plan.refused_reason = risk.fibi_reply or "too sharp. manual review."
            plan.risk_level = risk.risk_level
            LOGGER.info("fix_suggestion_refused", extra={"check_id": analysis.check_id, "risk_level": risk.risk_level, "reason": risk.reason})
            return self._local_response(self._format_fix_plan(plan), "thinking").response
        plan.suggested_patch_id = patch.patch_id
        plan.risk_level = patch.risk_level
        self.patch_confirmations.create(patch)
        self.patch_history.record_created(patch)
        self._last_check_fix_plan = plan
        self._pending_fix_suggestion = PendingFixSuggestion(
            plan.check_id,
            plan.project_id,
            plan.error_type,
            plan.error_message,
            plan.related_files,
            plan.suspected_file,
            plan.suspected_line,
            plan.confidence,
            plan.fix_summary,
            plan.risk_level,
            plan.suggested_patch_id,
            True,
            "",
            datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        LOGGER.info("pending_fix_created", extra={"check_id": plan.check_id, "patch_id": patch.patch_id, "risk_level": patch.risk_level})
        LOGGER.info("fix_patch_created", extra={"check_id": plan.check_id, "patch_id": patch.patch_id})
        self._remember_fix_suggestion_event(plan)
        return self._local_response(
            (
                "tests screamed.\n"
                f"likely file: {plan.suspected_file}:{plan.suspected_line or '?'}\n"
                "tiny fix ready.\n"
                "say: apply patch confirm"
            ),
            "thinking",
        ).response

    def _hydrate_check_result_output(self, result):
        if not result.output_path:
            return result
        output_dir = Path(result.output_path)
        stdout = self._read_check_output_preview(output_dir / "stdout.txt", max_chars=self.app_settings.settings.max_check_output_chars)
        stderr = self._read_check_output_preview(output_dir / "stderr.txt", max_chars=self.app_settings.settings.max_check_output_chars)
        result.stdout_preview = stdout or result.stdout_preview
        result.stderr_preview = stderr or result.stderr_preview
        return result

    @staticmethod
    def _format_failure_analysis(analysis) -> str:
        location = analysis.suspected_file or "unknown file"
        line = f":{analysis.suspected_line}" if analysis.suspected_line else ""
        return f"{analysis.error_type}. likely file: {location}{line}. {analysis.error_message}"

    @staticmethod
    def _format_fix_plan(plan: CheckFixPlan) -> str:
        if plan.refused_reason:
            location = plan.suspected_file or "unknown file"
            return f"{plan.refused_reason} likely file: {location}. error: {plan.error_type}."
        location = plan.suspected_file or "unknown file"
        return f"tiny fix plan: {plan.fix_summary} file: {location}. risk: {plan.risk_level}."

    def _create_pending_check(self, preset) -> str:
        project = self.project_workspace.current()
        if project is None:
            return "no project nest for checks."
        check_id = uuid.uuid4().hex[:12]
        request = ProjectCheckRequest(
            check_id,
            project.project_id,
            preset.command_key,
            list(preset.command_args),
            project.root_path,
            int(self.app_settings.settings.check_timeout_seconds),
            False,
            True,
            preset.risk_level,
        )
        safety = self.check_safety.assess(
            request,
            project,
            preset,
            require_confirmation=self.app_settings.settings.require_check_confirmation,
        )
        print("CHECK_SAFETY_ALLOWED:", str(safety.allowed).lower())
        print("CHECK_SAFETY_REASON:", safety.reason)
        if not safety.allowed:
            return safety.error or "that check is too sharp."
        request.allowed = True
        request.requires_confirmation = (
            safety.requires_confirmation
            or not self.app_settings.settings.allow_low_risk_checks_without_confirmation
        )
        if request.requires_confirmation:
            self.check_confirmations.create(request)
            return (
                f"check creature ready: {preset.display}.\n"
                f"risk: {preset.risk_level}.\n"
                "no running yet. say: run check confirm"
            )
        result = self.check_runner.run(request)
        self._last_check_result = result
        self.check_history.record(result)
        self._remember_check_event(result)
        return self._format_check_result(result)

    def _run_pending_check(self) -> FibiResponse:
        pending = self.check_confirmations.pending()
        if pending is None:
            return self._local_response("no check crumb waiting.", "sleepy").response
        project = self.project_workspace.current()
        if project is None:
            return self._local_response("no project nest for checks.", "sleepy").response
        preset = self.check_presets.find(project, pending.request.command_key)
        safety = self.check_safety.assess(
            pending.request,
            project,
            preset,
            require_confirmation=self.app_settings.settings.require_check_confirmation,
        )
        print("CHECK_CONFIRMATION_ACCEPTED:", str(safety.allowed).lower())
        print("CHECK_SAFETY_REASON:", safety.reason)
        if not safety.allowed:
            return self._local_response(safety.error or "that check is too sharp.", "sleepy").response
        start = time.perf_counter()
        result = self.check_runner.run(pending.request)
        duration_ms = (time.perf_counter() - start) * 1000
        self._last_check_result = result
        self.check_confirmations.cancel()
        self.check_history.record(result, duration_ms)
        self._remember_check_event(result)
        print("PROJECT_CHECK_DURATION_MS:", f"{duration_ms:.1f}")
        return self._local_response(self._format_check_result(result), "happy" if result.exit_code == 0 else "thinking").response

    @staticmethod
    def _format_check_pending(pending) -> str:
        return (
            f"check waiting: {pending.request.command_key}.\n"
            f"risk: {pending.request.risk_level}.\n"
            "say: run check confirm"
        )

    @staticmethod
    def _format_check_result(result) -> str:
        if result.timed_out:
            return f"check timed out: {result.command_key}. {result.summary}"
        if result.exit_code == 0:
            return f"check survived: {result.command_key}. {result.summary}"
        return f"check found crumbs: {result.command_key}. {result.summary}"

    @staticmethod
    def _read_check_output_preview(path: Path, max_chars: int = 3000) -> str:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        if not text.strip():
            return ""
        return text[:max_chars]

    def _remember_check_event(self, result) -> None:
        project = self.project_workspace.current()
        project_name = project.name if project else "project"
        status = "passed" if result.exit_code == 0 else "failed"
        if result.timed_out:
            status = "timed out"
        summary = f"Project check {result.command_key} {status} for {project_name}: {result.summary}"
        risk = self._memory_write_risk(summary, source="project_check_runner")
        if risk is None:
            return
        try:
            self.memory_router.rag_memory.remember_event(
                summary,
                importance=0.45,
                confidence=0.8,
                source="project_check_runner",
                source_id=f"check:{result.check_id}",
                metadata={
                    "project_id": result.project_id,
                    "project_name": project_name,
                    "command_key": result.command_key,
                    "exit_code": result.exit_code,
                    "risk_level": result.risk_level,
                    "timed_out": result.timed_out,
                    "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary},
                },
                provenance={"route": "ProjectRouter", "full_output_stored": False},
            )
        except Exception:
            LOGGER.exception("Failed to remember project check event")

    def _remember_fix_suggestion_event(self, plan: CheckFixPlan) -> None:
        project = self.project_workspace.current()
        project_name = project.name if project else "project"
        file_label = plan.suspected_file or "unknown file"
        summary = f"Fibi analyzed failed build and suggested patch for {file_label} in {project_name}."
        risk = self._memory_write_risk(summary, source="check_fix_planner")
        if risk is None:
            return
        try:
            self.memory_router.rag_memory.remember_event(
                summary,
                importance=0.5,
                confidence=0.75,
                source="check_fix_planner",
                source_id=f"check-fix:{plan.check_id}:{plan.suggested_patch_id}",
                metadata={
                    "project_id": plan.project_id,
                    "project_name": project_name,
                    "check_id": plan.check_id,
                    "error_type": plan.error_type,
                    "suspected_file": plan.suspected_file,
                    "risk_level": plan.risk_level,
                    "patch_id": plan.suggested_patch_id,
                    "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary},
                },
                provenance={"route": "ProjectRouter", "full_output_stored": False, "full_code_stored": False},
                allow_duplicate=True,
            )
        except Exception:
            LOGGER.exception("Failed to remember fix suggestion event")

    def _maybe_prepare_patch(self, result) -> str:
        if not result.ok:
            return result.display_text
        patch, risk = self.patch_engine.create_plan_from_suggestion(result)
        if patch is None:
            return risk.fibi_reply or f"manual only. risk: {risk.risk_level}."
        self.patch_confirmations.create(patch)
        self.patch_history.record_created(patch)
        return self._format_patch_summary(patch)

    @staticmethod
    def _format_patch_summary(patch) -> str:
        files = ", ".join(patch.target_files[:4])
        return (
            "manual edit suggestion ready. tiny edit ready.\n"
            f"files: {files}\n"
            f"risk: {patch.risk_level}\n"
            "diff held.\n"
            "no auto-apply. review first. say: apply patch confirm"
        )

    def _remember_patch_event(self, patch, applied_files: list[str]) -> None:
        project = self.project_workspace.current()
        project_name = project.name if project else "project"
        summary = f"Applied a {patch.risk_level}-risk patch to {project_name}: {', '.join(applied_files[:4])}."
        risk = self._memory_write_risk(summary, source="patch_engine")
        if risk is None:
            return
        try:
            self.memory_router.rag_memory.remember_event(
                summary,
                importance=0.55,
                confidence=0.75,
                source="patch_engine",
                source_id=f"patch:{patch.patch_id}",
                metadata={
                    "project_id": patch.project_id,
                    "project_name": project_name,
                    "files": applied_files,
                    "risk_level": patch.risk_level,
                    "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary},
                },
                provenance={"route": "ProjectRouter", "full_code_stored": False},
            )
        except Exception:
            LOGGER.exception("Failed to remember patch event")

    def _maybe_handle_project_edit_intent(self, user_message: str) -> FibiResponse | None:
        if self.project_workspace.current() is None:
            return None
        if not self.project_edit_planner.detects_edit_intent(user_message):
            return None
        result = self.project_edit_planner.plan(user_message, source="user_message")
        mood = "thinking" if result.ok else "sleepy"
        display_text = self._maybe_prepare_patch(result)
        response = self._local_response(display_text, mood).response
        self._log_reply_choice(
            "user_message",
            getattr(self, "_active_fast_category", "unknown"),
            "project-edit-suggestion",
            False,
            "local",
            response.display_text if response else display_text,
            getattr(self, "_active_local_brain_confidence", "n/a"),
            getattr(self, "_active_local_brain_handled", None),
            False,
        )
        return response

    def _prepare_context_command_for_model(self, user_message: str) -> str:
        stripped = user_message.strip()
        lowered = stripped.lower()
        for command, replacement in (
            ("/explain ", "explain the provided context"),
            ("/summarize ", "summarize the provided context"),
        ):
            if lowered.startswith(command):
                content = stripped[len(command):].strip()
                if content:
                    self.context_engine.add_text(content, "manual_selected_text", command.strip("/ "), mime_type="text/plain")
                    return replacement
        return user_message

    def _maybe_capture_pasted_context(self, user_message: str) -> FibiResponse | None:
        if not self.context_engine.looks_like_context(user_message):
            return None
        if self.html_extractor.looks_like_html(user_message):
            title = "pasted page text"
            source = "browser_page_text"
        else:
            title = "pasted code" if "```" in user_message else "pasted text"
            source = "pasted_text"
        self.context_engine.add_text(user_message, source, title, user_initiated=True)
        if self.context_engine.has_question_or_task(user_message):
            return None
        return self._local_response("page text crumb held." if title == "pasted page text" else "code crumb received." if title == "pasted code" else "context crumb held.", "thinking").response

    @staticmethod
    def _looks_like_project_question(user_message: str) -> bool:
        lowered = user_message.lower()
        return any(
            phrase in lowered
            for phrase in (
                "this project",
                "project",
                "codebase",
                "where is",
                "entry",
                "structure",
                "what kind of project",
                "what does this app",
                "fix the bug",
            )
        )

    def _handle_pending_action_confirmation(self, user_message: str) -> FibiResponse | None:
        pending = self.action_confirmations.consume_if_confirmed(user_message)
        if pending is None:
            return None
        intent = ActionIntent(
            pending.action_type,
            target=pending.target,
            query=pending.query,
            raw_text=user_message,
            direct_user_initiated=True,
        )
        permission = self.permissions.check(
            intent,
            self.action_settings.settings,
            self.privacy.settings,
            direct_user_initiated=True,
            quiet_active=False,
            boundary_active=False,
            confirmed=True,
        )
        if not permission.allowed:
            self._record_action(intent, False, permission.blocked, permission.requires_confirmation, True, permission.fibi_reply)
            return self._action_response(permission.fibi_reply, "sleepy", "action-blocked", True)
        # v0.12 keeps shutdown/restart/screenshot stubbed even after confirmation.
        reply = "confirmed, but tiny hands still refuse that in v0.12."
        self._record_action(intent, False, True, False, True, reply)
        return self._action_response(reply, "sleepy", "action-confirmation-stub", True)

    def _handle_action_intent(self, user_message: str) -> FibiResponse | None:
        print("ACTION_INTENT_CHECKED: true")
        intent = self.action_intents.detect(user_message, direct_user_initiated=True)
        if intent is None:
            print("ACTION_INTENT_DETECTED: false")
            print("ACTION_TYPE: none")
            print("ACTION_ROUTE_USED: false")
            return None
        print("ACTION_INTENT_DETECTED: true")
        print(f"ACTION_TYPE: {intent.action_type}")
        print("ACTION_ROUTE_USED: true")
        permission = self.permissions.check(
            intent,
            self.action_settings.settings,
            self.privacy.settings,
            direct_user_initiated=True,
            quiet_active=self.boundary.quiet.active,
            boundary_active=self.boundary.boundary.active,
        )
        if permission.requires_confirmation:
            self.action_confirmations.create(intent)
            self._record_action(intent, False, False, True, False, permission.fibi_reply)
            return self._action_response(permission.fibi_reply, "thinking", "action-confirmation", False, intent.action_type)
        if permission.blocked or not permission.allowed:
            self._record_action(intent, False, True, False, False, permission.fibi_reply)
            return self._action_response(permission.fibi_reply, "sleepy", "action-blocked", True, intent.action_type)
        result = self.desktop_actions.execute(intent)
        self._record_action(intent, result.ok, not result.ok, False, False, result.message)
        return self._action_response(
            result.message,
            "happy" if result.ok else "sleepy",
            result.provider_used,
            not result.ok,
            intent.action_type,
        )

    def _record_action(
        self,
        intent: ActionIntent,
        allowed: bool,
        blocked: bool,
        required_confirmation: bool,
        confirmed: bool,
        result_summary: str,
    ) -> None:
        definition = get_action_definition(intent.action_type)
        risk = definition.risk_level.value if definition else "unknown"
        target = intent.target or intent.query
        self.action_journal.record(
            intent.action_type,
            target,
            risk,
            allowed,
            blocked,
            required_confirmation,
            confirmed,
            result_summary,
            intent.direct_user_initiated,
        )

    def _action_response(
        self,
        text: str,
        mood: str,
        model_used: str,
        used_fallback: bool,
        action_type: str = "action_intent",
    ) -> FibiResponse:
        started = time.perf_counter()
        timing = self.timing.select(event="reply", mood=mood, local=True)
        motion = self.motion.select(
            mood=mood,
            presence_state=self.life.presence.value,
            event="reply",
            time_of_day=self._observe().time_of_day,
        )
        decision = self.route_decisions.decide(
            text,
            "user_message",
            action_intent=ActionIntent(action_type, raw_text=text) if action_type != "action_intent" else None,
        )
        self._log_route_decision(decision)
        # Do not save LifeEngine state here; pending action confirmations share
        # the state file and must survive this immediate response.
        self._log_reply_choice(
            "user_message",
            "local_utility" if action_type in {"tell_date", "tell_time"} else "action_intent",
            model_used,
            False,
            "local-action",
            text,
            "high",
            True,
            False,
        )
        print(f"FINAL_REPLY_TIME_MS: {(time.perf_counter() - started) * 1000:.1f}")
        priority = "low" if action_type in {"tell_date", "tell_time"} or model_used.startswith("local-action") else "medium"
        print(f"TTS_PRIORITY: {priority}")
        return FibiResponse(text, tts_safe_text(text), mood, model_used, used_fallback, timing, motion, priority)

    def _handle_memory_review_command(self, text: str, lowered: str) -> LocalCommandResult:
        if lowered in {"/memories", "/memory list"}:
            items = self.memory_review.list_memories(limit=10)
            first_id = items[0].memory_id if items else None
            if not items:
                legacy = self.memory_care.list_memories(limit=10)
                if legacy.entries:
                    entry = legacy.entries[0]
                    return self._local_response(
                        "tiny memory pile. " + "; ".join(item.title for item in legacy.entries[:5]),
                        "thinking",
                        int(entry.entry_id) if isinstance(entry.entry_id, int) else None,
                        tts_priority="silent",
                    )
            return self._local_response(self.memory_review.format_list(items), "thinking", first_id, tts_priority="silent")
        if lowered.startswith("/memory search "):
            query = text[len("/memory search "):].strip()
            results = self.memory_review.search_memories(query, top_k=10)
            first_id = results[0].item.memory_id if results else None
            if not results:
                legacy = self.memory_care.search_memories(query, limit=10)
                if legacy.entries:
                    entry = legacy.entries[0]
                    return self._local_response(
                        "found crumbs. " + "; ".join(item.title for item in legacy.entries[:5]),
                        "thinking",
                        int(entry.entry_id) if isinstance(entry.entry_id, int) else None,
                        tts_priority="silent",
                    )
            return self._local_response(self.memory_review.format_search(results), "thinking", first_id, tts_priority="silent")
        if lowered.startswith("/memory show "):
            memory_id = self._parse_memory_id(text[len("/memory show "):].strip())
            item = self.memory_review.get_memory(memory_id) if memory_id else None
            return self._local_response(self.memory_review.format_item(item), "thinking", memory_id, tts_priority="silent")
        if lowered.startswith("/memory approve "):
            memory_id = self._parse_memory_id(text[len("/memory approve "):].strip())
            result = self.memory_review.approve_memory(memory_id) if memory_id else None
            return self._local_response(result.message if result else "which memory crumb?", "happy" if result and result.ok else "thinking", memory_id, tts_priority="silent")
        if lowered.startswith("/memory pin "):
            memory_id = self._parse_memory_id(text[len("/memory pin "):].strip())
            result = self.memory_review.pin_memory(memory_id, True) if memory_id else None
            return self._local_response(result.message if result else "which memory crumb?", "happy" if result and result.ok else "thinking", memory_id, tts_priority="silent")
        if lowered.startswith("/memory unpin "):
            memory_id = self._parse_memory_id(text[len("/memory unpin "):].strip())
            result = self.memory_review.pin_memory(memory_id, False) if memory_id else None
            return self._local_response(result.message if result else "which memory crumb?", "sleepy" if result and result.ok else "thinking", memory_id, tts_priority="silent")
        if lowered.startswith("/memory archive "):
            memory_id = self._parse_memory_id(text[len("/memory archive "):].strip())
            result = self.memory_review.archive_memory(memory_id, True) if memory_id else None
            return self._local_response(result.message if result else "which memory crumb?", "sleepy" if result and result.ok else "thinking", memory_id, tts_priority="silent")
        if lowered.startswith("/memory edit "):
            payload = text[len("/memory edit "):].strip()
            memory_id, new_text = self._parse_memory_edit_payload(payload)
            if memory_id is None or not new_text:
                return self._local_response("use /memory edit <id> <new text>.", "thinking", tts_priority="silent")
            self._pending_memory_edit = MemoryEditRequest(memory_id, new_text, False)
            return self._local_response("edit staged. say: memory edit confirm", "thinking", memory_id, tts_priority="silent")
        if lowered in {"memory edit confirm", "/memory edit confirm"}:
            if self._pending_memory_edit is None:
                return self._local_response("no memory edit waiting.", "sleepy", tts_priority="silent")
            request = MemoryEditRequest(self._pending_memory_edit.memory_id, self._pending_memory_edit.new_text, True)
            result = self.memory_review.edit_memory(request)
            self._pending_memory_edit = None
            return self._local_response(result.message, "happy" if result.ok else "thinking", request.memory_id, tts_priority="silent")
        if lowered.startswith("/memory delete category "):
            category = text[len("/memory delete category "):].strip()
            self._pending_memory_delete = MemoryDeleteRequest(category=category, broad_delete=True, reason=f"delete_category:{category}")
            return self._local_response("category delete staged. say: memory delete confirm", "thinking", tts_priority="silent")
        if lowered.startswith("/memory delete "):
            memory_id = self._parse_memory_id(text[len("/memory delete "):].strip())
            if memory_id is None:
                return self._local_response("which memory crumb?", "thinking", tts_priority="silent")
            self._pending_memory_delete = MemoryDeleteRequest(memory_id=memory_id, reason="user_delete")
            return self._local_response("delete staged. say: memory delete confirm", "thinking", memory_id, tts_priority="silent")
        if lowered in {"memory delete confirm", "/memory delete confirm"}:
            if self._pending_memory_delete is None:
                return self._local_response("no memory delete waiting.", "sleepy", tts_priority="silent")
            pending = self._pending_memory_delete
            self._pending_memory_delete = None
            if pending.broad_delete:
                request = MemoryDeleteRequest(category=pending.category, user_confirmed=True, broad_delete=True, reason=pending.reason)
                result = self.memory_review.delete_by_category(request)
            else:
                request = MemoryDeleteRequest(memory_id=pending.memory_id, user_confirmed=True, reason=pending.reason)
                result = self.memory_review.delete_memory(request)
                if not result.ok and pending.memory_id is not None:
                    legacy = self.memory_care.delete_memory(pending.memory_id, confirm=True)
                    if legacy.ok and legacy.changed_count:
                        self._last_referenced_memory_id = None
                        return self._local_response(legacy.message, "sleepy", pending.memory_id, tts_priority="silent")
            return self._local_response(result.message, "sleepy", pending.memory_id, tts_priority="silent")
        if lowered == "/memory export":
            json_path, md_path = self.memory_review.export_memories(MemoryExportRequest())
            return self._local_response(f"memory export packed locally: {json_path}; {md_path}", "happy", tts_priority="silent")
        if lowered == "/memory health":
            return self._local_response(self.memory_review.format_health(self.memory_consent.status().summary), "thinking", tts_priority="silent")
        if lowered == "/memory safety":
            return self._local_response("memory safety: secrets never stored. sensitive notes need approval. exports skip secrets and raw private text.", "sleepy", tts_priority="silent")
        if lowered == "/memory consent":
            return self._local_response(self.memory_consent.summary_line(), "thinking", tts_priority="silent")
        if lowered == "/memory consent reset":
            self.memory_consent.reset()
            self.privacy.update(allow_memory_learning=True)
            return self._local_response("memory consent reset. safe learning on.", "happy", tts_priority="silent")
        if lowered == "/memory learning on":
            self.memory_consent.update(memory_learning_enabled=True)
            self.privacy.update(allow_memory_learning=True)
            return self._local_response("memory learning on.", "happy", tts_priority="silent")
        if lowered == "/memory learning off":
            self.memory_consent.update(memory_learning_enabled=False)
            self.privacy.update(allow_memory_learning=False)
            return self._local_response("memory paused.", "sleepy", tts_priority="silent")
        if lowered == "/memory approval required on":
            self.memory_consent.update(require_approval_for_sensitive_memory=True)
            return self._local_response("sensitive memory approval on.", "thinking", tts_priority="silent")
        if lowered == "/memory approval required off":
            self.memory_consent.update(require_approval_for_sensitive_memory=False)
            return self._local_response("sensitive approval off. secrets still blocked.", "thinking", tts_priority="silent")
        return LocalCommandResult(False)

    @staticmethod
    def _parse_memory_id(text: str) -> int | None:
        match = re.search(r"\d+", text)
        if not match:
            return None
        return int(match.group(0))

    @staticmethod
    def _parse_memory_edit_payload(payload: str) -> tuple[int | None, str]:
        parts = payload.split(maxsplit=1)
        if not parts:
            return None, ""
        try:
            memory_id = int(parts[0])
        except ValueError:
            return None, ""
        return memory_id, parts[1].strip() if len(parts) > 1 else ""

    def _handle_slash_command(self, text: str) -> LocalCommandResult:
        lowered = text.lower().strip()
        parts = text.split(maxsplit=2)

        help_command = self._handle_help_command(text, lowered)
        if help_command.handled:
            return help_command
        memory_command = self._handle_memory_review_command(text, lowered)
        if memory_command.handled:
            return memory_command
        workflow_command = self._handle_workflow_command(text, lowered)
        if workflow_command.handled:
            return workflow_command
        session_command = self._handle_session_command(text, lowered)
        if session_command.handled:
            return session_command
        action_command = self._handle_action_command(text, lowered)
        if action_command.handled:
            return action_command
        voice_command = self._handle_voice_command(text, lowered)
        if voice_command.handled:
            return voice_command
        context_command = self.context_router.route_command(text, lowered)
        if context_command.handled:
            return context_command
        route_command = self._handle_route_command(text, lowered)
        if route_command.handled:
            return route_command
        check_command = self.project_router.route_check_command(text, lowered)
        if check_command.handled:
            return check_command
        patch_command = self.project_router.route_patch_command(text, lowered)
        if patch_command.handled:
            return patch_command
        edit_command = self._handle_edit_command(text, lowered)
        if edit_command.handled:
            return edit_command
        project_command = self.project_router.route_command(text, lowered)
        if project_command.handled:
            return project_command
        issue_command = self._handle_issue_command(text, lowered)
        if issue_command.handled:
            return issue_command
        feedback_command = self._handle_feedback_command(text, lowered)
        if feedback_command.handled:
            return feedback_command
        update_command = self._handle_update_command(lowered)
        if update_command.handled:
            return update_command
        debug_command = self._handle_debug_command(lowered)
        if debug_command.handled:
            return debug_command
        browser_command = self._handle_browser_command(text, lowered)
        if browser_command.handled:
            return browser_command

        if lowered == "/settings":
            return self._local_response("settings opened.", "thinking")
        if lowered == "/tray":
            return self._local_response("tray creature ready if Windows allows it.", "idle")
        if lowered == "/hide":
            return self._local_response("hiding.", "sleepy")
        if lowered == "/show":
            return self._local_response("showing.", "happy")
        if lowered == "/nap":
            self.life.start_nap()
            return self._local_response("tiny nap.", "sleepy")
        if lowered == "/wake":
            self.life.wake("command")
            return self._local_response("awake-ish.", "happy")
        if lowered == "/voice on":
            self.privacy.update(allow_tts=True)
            return self._local_response("voice unboxed.", "happy")
        if lowered == "/voice output on":
            self.privacy.update(allow_tts=True)
            return self._local_response("voice output on.", "happy")
        if lowered == "/voice off":
            self.privacy.update(allow_tts=False)
            return self._local_response("voice tucked away.", "sleepy")
        if lowered == "/voice output off":
            self.privacy.update(allow_tts=False)
            return self._local_response("voice output off.", "sleepy", tts_priority="silent")
        if lowered == "/tts stop":
            return self._local_response(self.tts_manager.stop(), "sleepy", tts_priority="silent")
        if lowered == "/tts status":
            return self._local_response(self.tts_manager.status_line(), "thinking", tts_priority="silent")
        if lowered == "/utility tts on":
            self.tts_manager.speak_utility_replies = True
            return self._local_response("utility voice on.", "thinking", tts_priority="silent")
        if lowered == "/utility tts off":
            self.tts_manager.speak_utility_replies = False
            return self._local_response("utility voice off.", "sleepy", tts_priority="silent")
        if lowered == "/project checks on":
            self.app_settings.update(allow_project_checks=True)
            return self._local_response("project checks on. still asks first.", "thinking", tts_priority="silent")
        if lowered == "/project checks off":
            self.app_settings.update(allow_project_checks=False)
            return self._local_response("project checks off.", "sleepy", tts_priority="silent")
        if lowered == "/sounds on":
            self.privacy.update(allow_sounds=True)
            return self._local_response("tiny sounds on.", "happy")
        if lowered == "/sounds off":
            self.privacy.update(allow_sounds=False)
            return self._local_response("sounds tucked away.", "sleepy")
        if lowered.startswith("/animations "):
            value = lowered.split(maxsplit=1)[1]
            self.app_settings.update(animation_intensity=value if value in {"off", "low", "normal"} else "normal")
            return self._local_response(f"animations {self.app_settings.settings.animation_intensity}.", "thinking")
        if lowered == "/autostart on confirm":
            state = self.autostart.enable(confirm=True)
            return self._local_response("i'll wake with the machine." if state.enabled else "startup folder resisted.", "thinking")
        if lowered.startswith("/autostart on"):
            return self._local_response("autostart needs confirm.", "thinking")
        if lowered == "/autostart off":
            self.autostart.disable()
            return self._local_response("no startup sneaking.", "sleepy")
        if lowered == "/startup status":
            state = self.autostart.status()
            return self._local_response("startup on." if state.enabled else "startup off.", "thinking")
        if lowered == "/startup diagnostics":
            return self._local_response(self.startup_diagnostics.status_line(), "thinking", tts_priority="silent")
        if lowered == "/first run status":
            return self._local_response(self._first_run_status(), "thinking", tts_priority="silent")
        if lowered == "/beta status":
            line = "beta mode on. safe crumbs verbose." if self.app_settings.settings.beta_mode else "beta mode off. quiet crumbs."
            return self._local_response(line, "thinking", tts_priority="silent")
        if lowered == "/beta on":
            self.app_settings.update(beta_mode=True)
            return self._local_response("beta mode on. still local. still safe.", "thinking", tts_priority="silent")
        if lowered == "/beta off":
            self.app_settings.update(beta_mode=False)
            return self._local_response("beta mode off. tiny quiet.", "sleepy", tts_priority="silent")
        if lowered == "/limitations":
            return self._local_response(self._limitations_line(), "sleepy", tts_priority="silent")
        if lowered == "/self test":
            return self._local_response(self._self_test_line(), "thinking", tts_priority="silent")
        if lowered == "/install status":
            return self._local_response(self._install_status_line(), "thinking", tts_priority="silent")
        if lowered == "/data folder":
            return self._local_response(f"data nest: {runtime_info().user_data_dir}", "thinking", tts_priority="silent")
        if lowered == "/open data folder":
            return self._local_response(self._open_runtime_folder(runtime_info().user_data_dir), "thinking", tts_priority="silent")
        if lowered == "/open logs folder":
            return self._local_response(self._open_runtime_folder(logs_dir()), "thinking", tts_priority="silent")
        if lowered == "/reset instructions":
            return self._local_response(
                "reset: close me, delete the user data folder, start me again. zip uninstall: delete the app folder. no auto-delete paws.",
                "sleepy",
                tts_priority="silent",
            )
        if lowered == "/health":
            return self._local_response(self.data_health.check().message, "thinking")
        if lowered == "/health gui":
            return self._local_response(self.get_gui_health_snapshot(), "thinking", tts_priority="silent")
        if lowered == "/version detailed":
            return self._local_response(detailed_version_line(), "happy", tts_priority="silent")
        if lowered == "/version":
            return self._local_response(version_line(), "happy", tts_priority="silent")
        if lowered == "/release health":
            return self._local_response(self.release_health.summary_line(), "thinking", tts_priority="silent")
        if lowered.startswith("/support bundle for issue "):
            return self._export_support_bundle_for_issue(text[len("/support bundle for issue "):].strip())
        if lowered.startswith("/export error report for issue "):
            return self._export_support_bundle_for_issue(text[len("/export error report for issue "):].strip())
        if lowered in {"/export error report", "/support bundle"}:
            path = self.error_reports.export(
                self.get_gui_health_snapshot(),
                getattr(self.route_decisions.last_decision, "route_name", "unknown") if hasattr(self.route_decisions, "last_decision") else "unknown",
                [self._last_error_summary] if self._last_error_summary else [],
                beta_mode=self.app_settings.settings.beta_mode,
            )
            line = f"packed the safe crumbs: {path}" if lowered == "/support bundle" else f"error report packed: {path}"
            return self._local_response(line, "thinking", tts_priority="silent")
        if lowered == "/assets":
            return self._local_response(self.asset_health.check().message, "thinking")
        if lowered == "/model status":
            provider = self.model_router.mode
            cloud = "cloud on" if self.privacy.settings.allow_cloud_model and self.privacy.settings.allow_nvidia_api else "cloud off"
            return self._local_response(f"model {provider}. {cloud}. {self.health.status_line()}", "thinking")
        if lowered == "/cancel" or lowered == "/stop":
            self._cancel_requested = True
            self.life.set_thinking(False)
            self._journal_record("cancel", self.life.mood, self.life.presence.value, "User cancelled current thought.", emotional_weight=0.2, source="fast_router")
            return self._local_response(random.choice(["stopped.", "thought escaped.", "okay."]), "sleepy")
        if lowered == "/perf":
            return self._local_response(self.health.perf_line(), "thinking")
        if lowered == "/perf reset":
            self.health.reset_perf()
            return self._local_response("speed crumbs reset.", "sleepy")
        if lowered == "/model local":
            self.model_router.set_mode("local")
            return self._local_response("local tiny brain.", "sleepy")
        if lowered == "/model ollama":
            self.model_router.set_mode("ollama")
            self.privacy.update(allow_ollama=True)
            return self._local_response("ollama local brain.", "thinking")
        if lowered == "/model nvidia":
            self.model_router.set_mode("nvidia")
            return self._local_response("nvidia selected. cloud still needs confirm.", "thinking")
        if lowered == "/model auto":
            self.model_router.set_mode("auto")
            return self._local_response("auto tiny router.", "happy")
        if lowered == "/cloud on confirm":
            self.privacy.update(allow_cloud_model=True, allow_nvidia_api=True)
            return self._local_response("nvidia cloud allowed.", "thinking")
        if lowered == "/cloud off":
            self.privacy.update(allow_cloud_model=False, allow_nvidia_api=False)
            return self._local_response("cloud off.", "sleepy")
        if lowered == "/cloud context none":
            self.privacy.update(cloud_context_level="none")
            return self._local_response("no cloud crumbs.", "sleepy")
        if lowered == "/cloud context minimal":
            self.privacy.update(cloud_context_level="minimal")
            return self._local_response("minimal cloud crumbs only.", "thinking")
        if lowered == "/cloud context memory_hint":
            self.privacy.update(cloud_context_level="memory_hint")
            return self._local_response("memory hints allowed. tiny ones.", "thinking")
        if lowered == "/quiet":
            self.boundary.enable_quiet(None, reason="manual")
            return self._local_response("quiet mode.", "sleepy")
        if lowered.startswith("/quiet ") and lowered != "/quiet off":
            minutes = self.boundary.parse_quiet_minutes(lowered) or 30
            self.boundary.enable_quiet(minutes, reason="manual")
            return self._local_response("small and silent.", "sleepy")
        if lowered == "/quiet off":
            self.boundary.disable_quiet()
            return self._local_response("noise privileges restored.", "happy")
        if lowered == "/status":
            return self._local_response(self.get_status(), "thinking")
        if lowered == "/relationship":
            return self._local_response(
                f"we are tiny roommates. currently: {self.relationship.state.interaction_style}.",
                "happy",
            )
        if lowered == "/relationship reset confirm":
            return self._local_response(self.relationship.reset(confirm=True), "sleepy")
        if lowered.startswith("/relationship reset"):
            return self._local_response("relationship reset needs confirm.", "thinking")
        if lowered == "/privacy":
            return self._local_response(self.privacy.summary_line() + "\n" + self.safety_explainer.privacy_overview(), "thinking")
        if lowered == "/memories":
            result = self.memory_care.list_memories(limit=5)
            if not result.entries:
                return self._local_response("tiny memory pile is empty.", "sleepy")
            entry = result.entries[0]
            return self._local_response(
                "tiny memory pile. " + "; ".join(item.title for item in result.entries[:3]),
                "thinking",
                int(entry.entry_id) if isinstance(entry.entry_id, int) else None,
            )
        if lowered.startswith("/memory search "):
            query = text[len("/memory search "):].strip()
            result = self.memory_care.search_memories(query, limit=5)
            if not result.entries:
                return self._local_response("no crumbs matched.", "sleepy")
            entry = result.entries[0]
            return self._local_response(
                "found crumbs. " + "; ".join(item.title for item in result.entries[:3]),
                "thinking",
                int(entry.entry_id) if isinstance(entry.entry_id, int) else None,
            )
        if lowered.startswith("/forget category "):
            category = text[len("/forget category "):].replace(" confirm", "").strip()
            result = self.memory_care.forget_category(category, confirm=lowered.endswith(" confirm"))
            return self._local_response(result.message, "sleepy")
        if lowered.startswith("/forget "):
            target = text[len("/forget "):].strip()
            result = self.memory_care.forget_matching(target, confirm=True)
            return self._local_response(result.message, "sleepy")
        if lowered == "/dreams":
            dreams = self.memory_care.notebook_entries("dreams", limit=3)
            if not dreams:
                return self._local_response("no dream crumbs.", "sleepy")
            return self._local_response("dream crumbs. " + "; ".join(item.body for item in dreams[:3]), "sleepy")
        if lowered == "/clear dreams confirm":
            return self._local_response(self.memory_care.clear_dreams(confirm=True).message, "sleepy")
        if lowered == "/clear dreams":
            return self._local_response("dream wipe needs confirm.", "thinking")
        if lowered == "/journal today":
            return self._local_response(self.journal.summarize_day(), "thinking")
        if lowered == "/summary yesterday":
            yesterday = self.journal.yesterday_reference()
            return self._local_response(yesterday or "yesterday is mostly dust.", "sleepy")
        if lowered == "/preferences":
            entries = self.memory_care.notebook_entries("preferences", limit=5)
            if not entries:
                return self._local_response("no strong preferences yet.", "sleepy")
            return self._local_response("tiny preferences. " + "; ".join(entry.title for entry in entries[:3]), "thinking")
        if lowered == "/projects":
            entries = self.memory_care.notebook_entries("projects", limit=5)
            if not entries:
                return self._local_response("no project creatures yet.", "sleepy")
            return self._local_response("project creatures. " + "; ".join(entry.title for entry in entries[:3]), "thinking")
        if lowered == "/export memories":
            result = self.memory_care.export_bundle(self.privacy.settings)
            return self._local_response(f"export packed locally: {result.export_path}", "happy")
        if lowered == "/reset fibi confirm":
            return self._local_response(self.memory_care.reset_all("reset fibi confirm").message, "sleepy")
        if lowered.startswith("/reset fibi"):
            return self._local_response("new tiny life needs exact confirm.", "thinking")

        if parts and parts[0].lower() == "/clear":
            return self._local_response("clear what? dreams, journal, or preferences.", "thinking")
        return self._local_response("unknown tiny command. /help?", "thinking")

    def respond(self, user_message: str) -> FibiResponse:
        """Generate one response using local context and optional Ollama."""
        route_started = time.perf_counter()
        user_message = self._prepare_context_command_for_model(user_message)
        event_source = "user_message" if user_message.strip() else "empty_user_message"
        normalized_text = self.route_decisions.normalize(user_message)[:180]
        print(f"NORMALIZED_TEXT: {normalized_text}")
        self._active_fast_category = "unclassified"
        self._active_local_brain_confidence = "n/a"
        self._active_local_brain_handled = None
        command = self.command_router.route(user_message)
        if command.handled and command.response:
            decision = self.route_decisions.decide(user_message, event_source, command_result_handled=True)
            self._log_route_decision(decision)
            self.health.record_reply((time.perf_counter() - route_started) * 1000, "local", fast_path=True, slowest_step="command")
            self._log_reply_choice(
                event_source,
                "slash_command" if user_message.strip().startswith("/") else "local_command",
                "local-command",
                False,
                "local",
                command.response.display_text,
            )
            return command.response

        self.boundary.refresh()
        confirmed_action = self.action_router.handle_pending_confirmation(user_message)
        if confirmed_action is not None:
            self.health.record_reply((time.perf_counter() - route_started) * 1000, "local-action", fast_path=True, slowest_step="action_confirmation")
            return confirmed_action

        action_response = self.action_router.route(user_message)
        if action_response is not None:
            self.health.record_reply((time.perf_counter() - route_started) * 1000, "local-action", fast_path=True, slowest_step="action_intent")
            return action_response

        classified = self.chat_router.classify(user_message)
        self._active_fast_category = classified.category

        context_ack = self.context_router.maybe_capture(user_message)
        if context_ack is not None:
            self.health.record_reply((time.perf_counter() - route_started) * 1000, "local", fast_path=True, slowest_step="context_capture")
            return context_ack

        edit_response = self.project_router.maybe_handle_edit_intent(user_message)
        if edit_response is not None:
            self.health.record_reply((time.perf_counter() - route_started) * 1000, "local", fast_path=True, slowest_step="project_edit_suggestion")
            return edit_response

        if self.chat_router.is_greeting(user_message, classified) or self._is_fast_greeting(user_message):
            return self._fast_greeting_response(user_message)

        social_updates = self.relationship.learn_social_preferences(user_message)
        if any(update.key == "teasing_allowed" and update.value is False for update in social_updates):
            self._journal_record(
                "social_preference",
                self.life.mood,
                self.life.presence.value,
                "User asked for less teasing.",
                emotional_weight=0.55,
                source="relationship_engine",
            )
        lowered = user_message.lower()
        if any(phrase in lowered for phrase in ("less voice", "no tts", "no voice")):
            self.privacy.update(allow_tts=False)
            return self._local_response("voice tucked away.", "sleepy").response
        boundary_signal = self.boundary.detect(user_message)
        if boundary_signal:
            self.boundary.apply_boundary(boundary_signal)
            line = self.relationship.apply_boundary(boundary_signal)
            self._journal_record(
                "boundary_signal",
                self.life.mood,
                self.life.presence.value,
                f"{boundary_signal.level} boundary: {boundary_signal.phrase}",
                emotional_weight=0.7 if boundary_signal.level == "hard" else 0.45,
                source="boundary_engine",
            )
            return self._local_response(line or random.choice(["okay.", "quiet mode.", "i'll be small."]), "sleepy").response

        local_categories = {
            "thanks",
            "goodbye",
            "success",
            "frustration",
            "tiny_status",
            "social_checkin",
            "affection_click_like",
        }
        if self.chat_router.is_local_fast_category(classified.category):
            return self._micro_response(classified.category, user_message)
        if classified.category == "simple_chat":
            local_probe = self.chat_router.local_reply(
                "simple_chat",
                mood=self.life.mood,
                relationship=self.relationship.state,
            )
            self._active_local_brain_confidence = local_probe.confidence
            self._active_local_brain_handled = local_probe.handled
            if local_probe.handled and local_probe.confidence == "high" and local_probe.text:
                return self._micro_response(classified.category, user_message)

        wake_reaction = self._wake_if_needed("message")
        self.life.set_thinking(True)
        observation = self._observe()
        self.attention.mark_reacted("message")
        self._remember_conversation_rag("user", user_message)
        learned_ids = self._learn_from_message_rag(user_message) if self.privacy.settings.allow_memory_learning else []
        memories = self._relevant_memories(user_message)
        related_project = self._related_project(memories, user_message)
        self._journal_user_message(user_message, observation, related_project)
        if learned_ids:
            self._journal_record(
                "memory_learned",
                self.life.mood,
                self.life.presence.value,
                f"Learned {len(learned_ids)} explicit memory item(s).",
                related_project=related_project,
                emotional_weight=0.55,
                source="memory_engine",
                metadata={"memory_ids": learned_ids},
            )
        if related_project and learned_ids:
            self._journal_record(
                "project_detected",
                self.life.mood,
                self.life.presence.value,
                f"Project mentioned: {related_project}",
                related_project=related_project,
                emotional_weight=0.65,
                source="memory_engine",
            )

        recent_journal = self.journal.recent(limit=80) if self.privacy.settings.allow_journal else []
        detected_patterns = self.patterns.detect(observation, recent_journal) if self.privacy.settings.allow_pattern_detection else []
        favorite_project = self.patterns.favorite_project()
        preference_updates = self.preferences.update_from_context(
            self.life.nest,
            favorite_project,
            recent_journal,
        )
        recent_preferences = self.preferences.list_preferences(limit=8)
        drift = self.life.drift_mood(
            observation.time_of_day,
            max(0.0, time.monotonic() - self.life.last_interaction_time),
            recent_successes=sum(1 for entry in recent_journal[:20] if entry.event_type == "celebration"),
            recent_frustrations=sum(1 for entry in recent_journal[:20] if entry.event_type == "error_seen"),
        )
        if drift.previous_mood != drift.new_mood:
            self._journal_record(
                "mood_drift",
                drift.new_mood,
                self.life.presence.value,
                f"Mood drifted from {drift.previous_mood} to {drift.new_mood}: {drift.reason}.",
                related_project=related_project,
                emotional_weight=min(0.65, 0.25 + drift.drift_strength),
                source="life_engine",
            )
        known_projects = self._known_projects(memories, recent_journal, favorite_project.project_name if favorite_project else None)
        if self.privacy.settings.allow_inner_thoughts:
            self.inner_life.create_thought(
                self.life.mood,
                observation.time_of_day,
                memories=memories,
                recent_journal=recent_journal,
                known_projects=known_projects,
                nest=self.life.nest,
            )
        if preference_updates:
            self._journal_record(
                "preference_update",
                self.life.mood,
                self.life.presence.value,
                f"Updated {len(preference_updates)} tiny preference(s).",
                related_project=related_project,
                emotional_weight=0.25,
                source="preference_engine",
            )
        memory_hints = self.personality.natural_memory_hints(memories)
        curve = self.life.time_personality_curve(observation.time_of_day)
        memory_hints.append(
            f"Current temperament is {curve.preferred_mood}; keep it subtle and short."
        )
        yesterday = self.journal.yesterday_reference() if self.privacy.settings.allow_journal else None
        if yesterday:
            memory_hints.append(yesterday)
        for preference in recent_preferences[:3]:
            if preference.confidence >= 0.55:
                memory_hints.append(
                    f"Fibi has a small preference: {preference.preference_key} = {preference.value}."
                )
        for stable_opinion in self.opinions.stable_opinions(limit=2):
            if stable_opinion.confidence >= 0.55:
                memory_hints.append(f"Fibi opinion: {stable_opinion.text}")
        if self.context_engine.should_use_for(user_message):
            context_hint = self.context_engine.model_context()
            if context_hint:
                memory_hints.append(context_hint)
        if self._looks_like_project_question(user_message):
            project_hint = self.project_workspace.model_context()
            if project_hint:
                memory_hints.append(project_hint)
        success = self._is_success(user_message)
        frustration = self._is_frustration(user_message)
        if related_project:
            affinity_event = "success" if success else "frustration" if frustration else "interaction"
            self.patterns.update_project_affinity(related_project, affinity_event)
        self._update_bond_from_message(user_message, observation, success, frustration)
        self.relationship.update_from_bond(self.life.bond)
        context = self.personality.prepare(
            user_message,
            self.life.mood,
            observation,
            memories,
            patterns=detected_patterns,
            memory_hints=memory_hints,
            bond=self.life.bond,
        )

        opinion_result = self.opinions.evaluate(
            user_message,
            recent_journal,
            memories,
            detected_patterns,
            recent_preferences,
            observation.time_of_day,
        )
        opinion = (opinion_result.text, opinion_result.mood) if opinion_result and opinion_result.text else None
        legacy_opinion = self.personality.opinion_reaction(
            user_message,
            observation,
            memories,
            detected_patterns,
            recent_journal,
            bond=self.life.bond,
        )
        celebration = self._celebration_reaction(
            user_message, success and not frustration, observation, related_project
        )
        comfort = self._frustration_reaction(user_message, frustration, observation, related_project)
        short_message = len(user_message.strip().split()) <= 2
        local = None
        if not classified.should_use_model:
            local = (
                celebration
                or comfort
                or opinion
                or legacy_opinion
                or (wake_reaction if wake_reaction and short_message else None)
                or self.personality.local_reaction(user_message, observation, bond=self.life.bond)
            )
        if local:
            display, expression = local
            decision = self.social.filter_reaction(
                (display, expression),
                self.relationship.state,
                self.boundary.boundary,
                self.boundary.quiet,
                direct=True,
                user_message=user_message,
                event="reply",
            )
            if decision.action == "replace":
                display = decision.text
                expression = "sleepy"
            elif decision.action == "silence":
                display = "okay."
                expression = "sleepy"
            return self._finish(
                user_message,
                display,
                expression,
                "local-personality",
                False,
                observation,
                related_project,
            )

        prompt = self.personality.build_prompt(context, user_message)
        model_budget, model_started = self.budget.start("complex_chat")
        decision = self.route_decisions.decide(
            user_message,
            fast_category=classified,
            provider_allowed=self.health.provider_allowed("ollama"),
        )
        self._log_route_decision(decision)
        if self._cancel_requested:
            self._cancel_requested = False
            return self._micro_response("model_unavailable", user_message, observation.time_of_day)
        if not decision.model_router_allowed:
            display = "Ollama is unavailable. local tiny brain can't explain that well."
            return self._finish(user_message, display, "sleepy", "health-local-fallback", True, observation, related_project)
        if self.budget.exceeded(model_started, "complex_chat"):
            display = "model brain is asleep."
            return self._finish(user_message, display, "sleepy", "budget-local-fallback", True, observation, related_project)
        router_start = time.perf_counter()
        routed = self.model_router.route(
            prompt,
            user_message,
            self.life.mood,
            self.privacy.settings,
            observation=observation,
            memory_hints=memory_hints,
            fast_category=classified.category,
            local_brain_confidence=getattr(self, "_active_local_brain_confidence", "n/a"),
            local_brain_handled=getattr(self, "_active_local_brain_handled", None),
        )
        self.budget.update(model_budget, model_started)
        if model_budget.budget_exceeded:
            routed.reply_text = random.choice(BUDGET_FALLBACKS)
            routed.provider_used = "fallback"
            routed.model_used = "budget-local-fallback"
            routed.fallback_used = True
            routed.error = "response budget exceeded"
        self.health.record_provider_result(
            routed.provider_used,
            routed.duration_ms,
            not routed.fallback_used and not routed.error,
            routed.error,
        )
        print(f"RAW AI REPLY: {routed.reply_text}")

        display, tagged_mood = self._clean_model_reply(routed.reply_text)
        if is_effectively_empty(display) and not routed.error and routed.provider_used == "ollama":
            retry_prompt = (
                f"System: {context.system_prompt}\n\n"
                "Reply with one short natural Fibi sentence. No mood-only answer.\n"
                f"User: {user_message}\nFibi:"
            )
            retry = self.model_router.route(
                retry_prompt,
                user_message,
                self.life.mood,
                self.privacy.settings,
                observation=observation,
                memory_hints=[],
                fast_category=classified.category,
                local_brain_confidence=getattr(self, "_active_local_brain_confidence", "n/a"),
                local_brain_handled=getattr(self, "_active_local_brain_handled", None),
            )
            print(f"RAW AI REPLY: {retry.reply_text}")
            display, tagged_mood = self._clean_model_reply(retry.reply_text)
            routed = retry

        used_fallback = is_effectively_empty(display)
        if used_fallback:
            display = "Ollama is unavailable. local tiny brain can't explain that well." if classified.category == "complex_chat" else random.choice(FALLBACKS)
            tagged_mood = "sleepy" if "eepy" in display else "idle"
        print(f"FINAL_REPLY_TIME_MS: {(time.perf_counter() - router_start) * 1000:.1f}")
        self.health.record_reply(
            (time.perf_counter() - route_started) * 1000,
            routed.provider_used,
            fast_path=False,
            model_latency_ms=routed.duration_ms,
            slowest_step="model_router",
        )

        return self._finish(
            user_message,
            display,
            tagged_mood,
            routed.model_used,
            used_fallback or routed.fallback_used or bool(routed.error),
            observation,
            related_project,
        )

    @staticmethod
    def _clean_model_reply(raw: str) -> tuple[str, str]:
        has_mood_tag = bool(re.search(r"\[(idle|happy|thinking|sleepy|angry|talking)\]", raw, re.IGNORECASE))
        after_mood, mood = remove_mood_tags(raw)
        print(f"AFTER MOOD CLEAN: {after_mood}")
        display = clean_response(after_mood)
        print(f"CLEANED DISPLAY: {display}")
        return display, mood if has_mood_tag else ""

    def _finish(
        self,
        user_message: str,
        display: str,
        expression: str,
        model_used: str,
        used_fallback: bool,
        observation: Observation,
        related_project: str | None,
    ) -> FibiResponse:
        display = clean_response(display)
        decision = self.social.filter_reaction(
            display,
            self.relationship.state,
            self.boundary.boundary,
            self.boundary.quiet,
            direct=True,
            user_message=user_message,
            event="reply",
        )
        if decision.action == "replace":
            display = decision.text
        elif decision.action == "silence":
            display = "okay."
        tts = tts_safe_text(display)
        print(f"TTS TEXT: {tts}")
        tts_priority = self.tts_manager.priority_for(model_used)
        print(f"TTS_PRIORITY: {tts_priority}")
        previous_mood = self.life.mood
        semantic_mood = self.life.update_mood(
            "reply",
            user_text=user_message,
            reply_text=display,
            time_of_day=observation.time_of_day,
        )
        final_expression = self._expression_for(expression, semantic_mood)
        self.life.set_thinking(False)
        self.life.remember_interaction(user_message, semantic_mood)
        self._remember_conversation_rag("fibi", display, mood=final_expression)
        weight_update = emotional_weight_for_message(
            user_message,
            observation.time_of_day,
            related_project,
        )
        moment = f"Conversation moment: {user_message}"
        risk = self._memory_write_risk(moment, source="conversation")
        if risk is not None:
            self.memory_router.rag_memory.remember_event(
                moment,
                importance=min(0.75, max(0.2, weight_update.weight - 0.15)),
                confidence=0.55,
                source="conversation",
                metadata={
                    "time_of_day": observation.time_of_day,
                    "non_factual_reply_excluded": True,
                    "emotional_reason": weight_update.reason,
                    "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary},
                },
                provenance={"route": "response_pipeline", "related_project": related_project or ""},
            )
        if previous_mood != semantic_mood:
            self._journal_record(
                "mood_change",
                semantic_mood,
                self.life.presence.value,
                f"Mood changed from {previous_mood} to {semantic_mood}.",
                related_project=related_project,
                emotional_weight=0.45,
                source="life_engine",
            )
        event_type = "fallback_reply" if used_fallback else "fibi_reply"
        self._journal_record(
            event_type,
            semantic_mood,
            self.life.presence.value,
            display,
            related_project=related_project,
            emotional_weight=0.35 if used_fallback else max(0.5, weight_update.weight),
            source="fibi_core",
            metadata={
                "model_used": model_used,
                "time_of_day": observation.time_of_day,
                "active_app": observation.active_app,
            },
        )
        presentation_event = (
            "success" if self._is_success(user_message)
            else "frustration" if self._is_frustration(user_message)
            else "greeting" if user_message.lower().strip(" .!?") in {"hey", "hi", "hello", "yo", "sup"}
            else "reply"
        )
        timing = self.timing.select(
            event=presentation_event,
            mood=semantic_mood,
            time_of_day=observation.time_of_day,
            local=model_used == "local-personality",
            fallback=used_fallback,
        )
        motion = self.motion.select(
            mood=semantic_mood,
            presence_state=self.life.presence.value,
            event=presentation_event,
            time_of_day=observation.time_of_day,
        )
        self.repetition.remember(
            line=display, category=presentation_event,
            motion=motion.motion_name if motion else "", project=related_project or "",
        )
        self._save_repetition()
        provider_used = "local" if model_used.startswith("local") or "fallback" in model_used else "model"
        route_selected = (
            "local-fallback" if model_used in {"health-local-fallback", "budget-local-fallback"}
            else "local-direct-fallback" if "fallback" in model_used
            else "local-personality" if model_used.startswith("local")
            else "model-router"
        )
        model_router_used = route_selected in {"model-router", "local-direct-fallback"}
        self._log_reply_choice(
            "user_message" if user_message.strip() else "empty_user_message",
            getattr(self, "_active_fast_category", "unknown"),
            route_selected,
            False,
            provider_used,
            display,
            getattr(self, "_active_local_brain_confidence", "n/a"),
            getattr(self, "_active_local_brain_handled", None),
            model_router_used,
        )
        return FibiResponse(display, tts, final_expression, model_used, used_fallback, timing, motion, tts_priority)

    def contextual_idle_reaction(self, event_source: str = "idle", user_text: str = "") -> tuple[str, str]:
        """Create a rare idle line from sampled context and local patterns."""
        if event_source == "user_message" or user_text.strip():
            self._log_reply_choice(
                event_source,
                "blocked_direct_message",
                "idle-thought-blocked",
                False,
                "local",
                "",
            )
            return "", self.life.expression
        self.boundary.refresh()
        if self.boundary.quiet.active or self.boundary.boundary.active:
            self._pending_idle_motion = self.motion.select(
                mood=self.life.mood,
                presence_state=self.life.presence.value,
                event="idle",
                time_of_day=self._observe().time_of_day,
            )
            return "", self.life.expression
        if self.life.nap.is_napping:
            return "", "sleepy"
        observation = self._observe()
        idle_seconds = max(0.0, time.monotonic() - self.life.last_interaction_time)
        ritual = self.rituals.ambient(
            observation.time_of_day, self.life.bond.affection, idle_seconds
        )
        if ritual.triggered and ritual.reaction:
            self.life.set_ritual_states(self.rituals.export_state())
            self._journal_record(
                "ritual", ritual.reaction.expression, self.life.presence.value,
                ritual.reaction.text, emotional_weight=0.35, source="ritual_engine",
                metadata={"ritual": ritual.name},
            )
            return ritual.reaction.text, self._expression_for(ritual.reaction.expression, self.life.mood)
        recent = self.journal.recent(limit=60) if self.privacy.settings.allow_journal else []
        detected = self.patterns.detect(observation, recent) if self.privacy.settings.allow_pattern_detection else []
        strongest = self.patterns.strongest(detected)
        attention = self.attention.evaluate(
            "idle",
            self.life.mood,
            self.life.presence.value,
            observation.time_of_day,
            observation,
            recent,
            detected,
        )
        if not attention.should_react:
            return "", self.life.expression
        thought_bubble_allowed = (
            self.life.presence.value in {"idle", "observing", "napping", "waking"}
            and not self.boundary.quiet.active
            and not self.life.is_busy()
            and attention.should_react
        )
        self.life.drift_mood(
            observation.time_of_day,
            idle_seconds,
            recent_successes=sum(1 for entry in recent[:20] if entry.event_type == "celebration"),
            recent_frustrations=sum(1 for entry in recent[:20] if entry.event_type == "error_seen"),
        )
        signature = (observation.active_app, observation.active_window_title, self.life.mood)
        focused_app = (observation.active_app or "").lower() in {"code", "vscode", "devenv"}
        if signature == self._last_ambient_signature or (focused_app and 120 <= idle_seconds < 1200):
            self._pending_idle_motion = self.motion.select(
                mood=self.life.mood, presence_state=self.life.presence.value,
                event="idle", time_of_day=observation.time_of_day, attention=attention,
            )
            return "", self.life.expression
        self._last_ambient_signature = signature
        projects = self.memory.retrieve("", categories=[MemoryCategory.PROJECT], limit=3)
        project = self._related_project(projects, "")
        habit = self.habits.select(
            self.life.mood,
            observation.time_of_day,
            observation.active_app,
            detected,
        )
        thought = None
        bubble = None
        if self.privacy.settings.allow_inner_thoughts:
            thought = self.inner_life.create_thought(
                self.life.mood,
                observation.time_of_day,
                memories=projects,
                recent_journal=recent,
                known_projects=[project] if project else [],
                nest=self.life.nest,
            )
        if (
            thought_bubble_allowed
            and self.privacy.settings.allow_idle_bubbles
            and self.privacy.settings.allow_inner_thoughts
        ):
            bubble = self.inner_life.thought_bubble_candidate(
                attention.attention_level,
                focused_app and 120 <= idle_seconds < 1200,
                self.life.is_busy(),
                self.life.mood,
                event_source=event_source,
                user_text=user_text,
            )
        if bubble and bubble.should_display and self.repetition.allows_line(bubble.text):
            motion = self.motion.select(
                mood=self.life.mood,
                presence_state=self.life.presence.value,
                event="idle",
                time_of_day=observation.time_of_day,
                attention=attention,
            )
            self._pending_idle_motion = motion
            self.repetition.remember(
                line=bubble.text,
                category="thought_bubble",
                motion=motion.motion_name if motion else "",
                idle=bubble.text,
                project=thought.related_project if thought else "",
            )
            self._save_repetition()
            self.attention.mark_reacted("idle")
            self._journal_record(
                "thought_bubble",
                self.life.mood,
                self.life.presence.value,
                bubble.text,
                related_project=thought.related_project if thought else None,
                emotional_weight=bubble.emotional_weight,
                source="inner_life_engine",
                metadata={"category": bubble.category},
            )
            self._log_reply_choice(
                event_source,
                "idle_thought",
                "thought-bubble",
                True,
                "local",
                bubble.text,
            )
            return bubble.text, bubble.expression
        line = self.life.idle_reaction(
            time_of_day=observation.time_of_day,
            active_app=observation.active_app,
            known_project=project,
            pattern_reaction=strongest.suggested_reaction if strongest else habit.line,
            idle_seconds=idle_seconds,
        )
        motion = self.motion.select(
            mood=self.life.mood, presence_state=self.life.presence.value,
            event="idle", time_of_day=observation.time_of_day,
            attention=attention, habit=habit,
        )
        if not self.repetition.allows_line(line) or not self.repetition.allows_category("idle"):
            self._pending_idle_motion = motion
            return "", self.life.expression
        if motion and not self.repetition.allows_motion(motion.motion_name):
            motion = None
        self._pending_idle_motion = motion
        self.repetition.remember(
            line=line, category="idle", motion=motion.motion_name if motion else "",
            idle=line, project=project or "",
        )
        self._save_repetition()
        self.attention.mark_reacted("idle")
        if self.habits.should_journal(habit):
            self._journal_record(
                "habit",
                self.life.mood,
                self.life.presence.value,
                habit.line,
                related_project=project,
                emotional_weight=0.15,
                source="habit_engine",
                metadata={"habit": habit.name, "times_performed": habit.times_performed},
            )
        expression = "sleepy" if observation.time_of_day in {"night", "late_night"} else self.life.expression
        self._journal_record(
            "idle_reaction",
            self.life.mood,
            self.life.presence.value,
            line,
            related_project=project,
            emotional_weight=0.2,
            source="life_engine",
            metadata={
                "time_of_day": observation.time_of_day,
                "active_app": observation.active_app,
                "idle_seconds": round(idle_seconds, 1),
                "pattern": strongest.pattern if strongest else None,
                "habit": habit.name,
            },
        )
        return line, expression

    def handle_click(self, now: float | None = None, double: bool = False) -> CreatureReaction | None:
        """Handle a pet/poke locally with spam-safe attention gating."""
        was_napping = self.life.nap.is_napping
        spammed = self.life.register_click(now)
        recent = self.journal.recent(limit=20) if self.privacy.settings.allow_journal else []
        observation = self._observe()
        attention = self.attention.evaluate(
            "click",
            self.life.mood,
            self.life.presence.value,
            observation.time_of_day,
            observation,
            recent,
            direct=True,
            important=spammed or was_napping,
            now=now,
        )
        if not attention.should_react:
            return None

        if was_napping:
            text, expression = self.life.wake("click")
            reaction_type = "wake"
            self._journal_wake("click", text)
        else:
            text, expression = self.life.click_reaction(spammed)
            reaction_type = "click"

        self.attention.mark_reacted("click", now)
        self._journal_record(
            "pet_interaction",
            self.life.mood,
            self.life.presence.value,
            text,
            emotional_weight=0.45,
            source="ui",
            metadata={
                "double": double,
                "spammed": spammed,
                "affection": self.life.bond.affection,
                "mischief": self.life.bond.mischief,
            },
        )
        return self._decorate_reaction(CreatureReaction(text, expression, reaction_type), reaction_type, observation)

    def handle_drag_start(self, now: float | None = None) -> CreatureReaction | None:
        was_napping = self.life.nap.is_napping
        self._last_drag_spammed = self.life.register_drag(now)
        if was_napping:
            wake_text, _ = self.life.wake("drag")
            self._journal_wake("drag", wake_text)
        text, expression = self.life.start_drag()
        attention = self.attention.evaluate(
            "drag_start",
            self.life.mood,
            self.life.presence.value,
            self._observe().time_of_day,
            direct=True,
            important=was_napping or self._last_drag_spammed,
            now=now,
        )
        self._journal_record(
            "drag_start",
            self.life.mood,
            self.life.presence.value,
            text,
            emotional_weight=0.35,
            source="ui",
            metadata={"spammed": self._last_drag_spammed},
        )
        if not attention.should_react:
            return None
        self.attention.mark_reacted("drag_start", now)
        return self._decorate_reaction(CreatureReaction(text, expression, "drag_start"), "drag_start")

    def handle_drag_end(self, x: int, y: int, now: float | None = None) -> CreatureReaction | None:
        text, expression = self.life.finish_drag(x, y, self._last_drag_spammed)
        attention = self.attention.evaluate(
            "drag_end",
            self.life.mood,
            self.life.presence.value,
            self._observe().time_of_day,
            direct=True,
            important=self._last_drag_spammed,
            now=now,
        )
        self._journal_record(
            "drag_end",
            self.life.mood,
            self.life.presence.value,
            text,
            emotional_weight=0.3,
            source="ui",
            metadata={"x": x, "y": y, "spammed": self._last_drag_spammed},
        )
        if not attention.should_react:
            return None
        self.attention.mark_reacted("drag_end", now)
        return self._decorate_reaction(CreatureReaction(text, expression, "drag_end"), "drag_end")

    def check_nap(self, now: float | None = None) -> CreatureReaction | None:
        self.boundary.refresh()
        if self.boundary.quiet.active:
            return None
        if self.life.nap.is_napping or self.life.is_busy():
            return None
        time_of_day = self.observation.time_of_day(datetime.now().astimezone().hour)
        idle_seconds = max(0.0, time.monotonic() - self.life.last_interaction_time)
        if not self.life.should_nap(time_of_day, idle_seconds):
            return None
        attention = self.attention.evaluate(
            "nap",
            self.life.mood,
            self.life.presence.value,
            time_of_day,
            direct=False,
            now=now,
        )
        if not attention.should_react:
            return None
        text, expression = self.life.start_nap()
        ritual = self.rituals.bedtime_nap(self.life.bond.affection, time_of_day)
        if ritual.triggered:
            self.life.set_ritual_states(self.rituals.export_state())
        recent = self.journal.recent(limit=40) if self.privacy.settings.allow_journal else []
        favorite = self.patterns.favorite_project()
        dream = None
        if self.privacy.settings.allow_dreams:
            dream = self.inner_life.create_dream(
                self.life.mood,
                recent_journal=recent,
                known_projects=[favorite.project_name] if favorite else [],
                habits=[entry.short_summary for entry in recent if entry.event_type == "habit"][:3],
                nest=self.life.nest,
                bond=self.life.bond,
            )
        self.attention.mark_reacted("nap", now)
        self._journal_record(
            "nap",
            self.life.mood,
            self.life.presence.value,
            text,
            emotional_weight=0.2,
            source="life_engine",
            metadata={
                "idle_seconds": round(idle_seconds, 1), "time_of_day": time_of_day,
                "ritual": ritual.name if ritual.triggered else None,
                "dream_id": dream.id if dream else None,
            },
        )
        return self._decorate_reaction(CreatureReaction(text, expression, "nap"), "nap")

    def handle_wake(self, reason: str = "interaction") -> CreatureReaction | None:
        if not self.life.nap.is_napping:
            return None
        text, expression = self.life.wake(reason)
        dream_line = self.inner_life.maybe_wake_dream_line() if self.privacy.settings.allow_dreams else None
        if dream_line:
            text = random.choice(["weird dream.", dream_line])
        self._journal_wake(reason, text)
        self.attention.mark_reacted("wake")
        return self._decorate_reaction(CreatureReaction(text, expression, "wake"), "wake")

    def _wake_if_needed(self, reason: str) -> tuple[str, str] | None:
        reaction = self.handle_wake(reason)
        return (reaction.text, reaction.expression) if reaction else None

    def _journal_wake(self, reason: str, text: str) -> None:
        self._journal_record(
            "wake",
            self.life.mood,
            self.life.presence.value,
            text,
            emotional_weight=0.35,
            source="life_engine",
            metadata={"reason": reason},
        )

    @staticmethod
    def _is_success(user_message: str) -> bool:
        text = user_message.lower()
        return any(signal in text for signal in SUCCESS_SIGNALS)

    @staticmethod
    def _is_frustration(user_message: str) -> bool:
        text = user_message.lower()
        return any(signal in text for signal in FRUSTRATION_SIGNALS)

    def _update_bond_from_message(
        self,
        user_message: str,
        observation: Observation,
        success: bool,
        frustration: bool,
    ) -> None:
        cleaned = user_message.lower().strip(" .!?")
        if cleaned in {"hey", "hi", "hello", "yo", "sup"}:
            self.life.update_bond("greeting")
        if any(word in cleaned for word in ("thanks", "thank you", "love", "cute", "good creature")):
            self.life.update_bond("kind_phrase")
        if success:
            self.life.update_bond("success")
        if frustration:
            self.life.update_bond("frustration")
        if observation.time_of_day == "late_night" and any(
            word in cleaned for word in ("code", "commit", "build", "working")
        ):
            self.life.update_bond("late_overwork")

    def _celebration_reaction(
        self,
        user_message: str,
        success: bool,
        observation: Observation,
        related_project: str | None,
    ) -> tuple[str, str] | None:
        if not success:
            return None
        attention = self.attention.evaluate(
            "celebration",
            self.life.mood,
            self.life.presence.value,
            observation.time_of_day,
            observation,
            direct=True,
            important=True,
        )
        if not attention.should_react:
            return None
        picked = self.reactions.select(
            "success", affection=self.life.bond.affection,
            time_of_day=observation.time_of_day, attention_level=attention.attention_level,
            guard=self.repetition, direct=True, active_app=observation.active_app,
            project_affinity=None, values={"project": related_project or ""},
        )
        if picked is None:
            return None
        line = picked.text
        self.attention.mark_reacted("celebration")
        self._journal_record(
            "celebration",
            "excited",
            self.life.presence.value,
            line,
            related_project=related_project,
            emotional_weight=0.85,
            source="personality_engine",
            metadata={"user_message": user_message[:240]},
        )
        return line, "happy"

    def _frustration_reaction(
        self,
        user_message: str,
        frustration: bool,
        observation: Observation,
        related_project: str | None,
    ) -> tuple[str, str] | None:
        if not frustration:
            return None
        attention = self.attention.evaluate(
            "frustration",
            self.life.mood,
            self.life.presence.value,
            observation.time_of_day,
            observation,
            direct=True,
            important=True,
        )
        if not attention.should_react:
            return None
        picked = self.reactions.select(
            "frustration", affection=self.life.bond.affection,
            time_of_day=observation.time_of_day, attention_level=attention.attention_level,
            guard=self.repetition, direct=True, active_app=observation.active_app,
            values={"project": related_project or ""},
        )
        if picked is None:
            return None
        line = picked.text
        expression = "sleepy" if "tired" in user_message.lower() else "thinking"
        self.attention.mark_reacted("frustration")
        self._journal_record(
            "frustration_comfort",
            "focused",
            self.life.presence.value,
            line,
            related_project=related_project,
            emotional_weight=0.75,
            source="personality_engine",
            metadata={"user_message": user_message[:240]},
        )
        return line, expression

    def shutdown(self) -> CreatureReaction | None:
        observation = self._observe()
        ritual = self.rituals.shutdown(
            self.life.bond.affection, observation.time_of_day
        )
        if self.privacy.settings.allow_journal:
            self.journal.create_daily_summary()
        self.rituals.mark_daily_summary(self.life.bond.affection, observation.time_of_day)
        self.life.set_ritual_states(self.rituals.export_state())
        self._journal_record(
            "shutdown",
            self.life.mood,
            self.life.presence.value,
            "Fibi went quiet.",
            emotional_weight=0.25,
            source="life_engine",
        )
        self.life._saved_state["clean_shutdown"] = True
        self.life._saved_state["unclean_shutdown_detected"] = False
        self.life.mark_shutdown()
        self.shutdown_manager.shutdown(
            [
                ("life_state", self.life.save_state),
                ("work_sessions", getattr(self.work_sessions, "_save", None)),
            ]
        )
        return ritual.reaction if ritual.triggered else None

    def take_pending_idle_motion(self):
        motion = self._pending_idle_motion
        self._pending_idle_motion = None
        return motion

    def _decorate_reaction(
        self,
        reaction: CreatureReaction,
        event: str,
        observation: Observation | None = None,
    ) -> CreatureReaction:
        observed = observation or self._observe()
        reaction.motion = self.motion.select(
            mood=self.life.mood, presence_state=self.life.presence.value,
            event=event, time_of_day=observed.time_of_day,
        )
        reaction.timing = self.timing.select(
            event=event, mood=self.life.mood,
            time_of_day=observed.time_of_day, local=True,
        )
        sound_events = {
            "click": "click", "wake": "wake", "nap": "sleep",
            "drag_start": "drag", "drag_end": "drag",
        }
        reaction.sound_name = sound_events.get(event)
        self.repetition.remember(
            line=reaction.text, category=event,
            motion=reaction.motion.motion_name if reaction.motion else "",
        )
        self._save_repetition()
        return reaction

    def _save_repetition(self) -> None:
        self.life.set_repetition_state(self.repetition.export_state())

    def day_summary(self) -> str:
        if not self.privacy.settings.allow_journal:
            return "journal is closed."
        return self.journal.create_daily_summary().tiny_summary

    def record_restoration_path(self, path: str) -> None:
        self._journal_record(
            "position_restored", self.life.mood, self.life.presence.value,
            f"Window restored from {path}.", emotional_weight=0.15,
            source="life_engine", metadata={"path": path},
        )

    def _remember_conversation_rag(self, role: str, content: str, mood: str | None = None) -> None:
        if role not in {"user", "fibi"} or not content.strip():
            return
        risk = self._memory_write_risk(content, source=f"conversation:{role}")
        if risk is None:
            return
        try:
            self.memory_router.rag_memory.service.add_memory(
                content,
                category="conversation",
                source=f"conversation:{role}",
                metadata={"role": role, "mood": mood or "", "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary}},
                provenance={"route": "fibi_core", "memory_write": "conversation"},
            )
            LOGGER.info("memory_retrieval.conversation_saved", extra={"role": role})
        except Exception:
            LOGGER.exception("Failed to save conversation to RAG memory")

    def _learn_from_message_rag(self, user_message: str) -> list[int]:
        if self._memory_write_risk(user_message, source="conversation") is None:
            return []
        patterns = [
            (MemoryCategory.FACT, r"\bmy name is\s+([^.!?]+)", 0.9),
            (MemoryCategory.PROJECT, r"\b(?:working on|building)\s+([^.!?]+)", 0.8),
            (MemoryCategory.GOAL, r"\b(?:i want to|my goal is)\s+([^.!?]+)", 0.8),
            (MemoryCategory.HABIT, r"\bi (?:usually|often|always)\s+([^.!?]+)", 0.7),
            (MemoryCategory.BELIEF, r"\bi believe\s+([^.!?]+)", 0.8),
        ]
        saved_ids: list[int] = []
        for category, pattern, importance in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if not match:
                continue
            risk = self._memory_write_risk(match.group(0).strip(), source=f"conversation:{category.value}")
            if risk is None:
                continue
            try:
                memory = self.memory_router.rag_memory.service.add_memory(
                    match.group(0).strip(),
                    category=category.value,
                    importance=importance,
                    confidence=importance,
                    source="conversation",
                    metadata={"learned_from": "direct_user_message", "review": {"sensitive_flag": risk.sensitive_flag, "summary": risk.safe_summary}},
                    provenance={"route": "memory_router", "pattern": pattern},
                )
            except Exception:
                LOGGER.exception("Failed to learn explicit memory through RAG")
                continue
            if memory.id is not None:
                saved_ids.append(memory.id)
        return saved_ids

    def _memory_write_risk(self, content: str, *, source: str, user_requested: bool = False):
        if not self.privacy.settings.allow_memory_learning or not self.memory_consent.state.memory_learning_enabled:
            LOGGER.info("memory_write_skipped.learning_off", extra={"source": source})
            return None
        if not self.memory_consent.can_remember_source(source):
            LOGGER.info("memory_write_skipped.consent_source", extra={"source": source})
            return None
        risk = self.sensitive_memory_guard.assess(content, source=source, user_requested=user_requested)
        if risk.blocked:
            LOGGER.info("memory_write_blocked.sensitive", extra={"source": source, "flag": risk.sensitive_flag})
            return None
        if risk.requires_approval and self.memory_consent.state.require_approval_for_sensitive_memory and not user_requested:
            LOGGER.info("memory_write_needs_approval", extra={"source": source, "flag": risk.sensitive_flag})
            return None
        return risk

    def _journal_user_message(
        self,
        user_message: str,
        observation: Observation,
        related_project: str | None,
    ) -> None:
        cleaned = user_message.strip().lower().strip(" .,!?")
        is_greeting = cleaned in {"hey", "hi", "hello", "yo", "sup"}
        metadata = {
            "time_of_day": observation.time_of_day,
            "active_app": observation.active_app,
            "is_greeting": is_greeting,
        }
        weight_update = emotional_weight_for_message(
            user_message,
            observation.time_of_day,
            related_project,
        )
        self._journal_record(
            "user_message",
            self.life.mood,
            self.life.presence.value,
            user_message[:240],
            related_project=related_project,
            emotional_weight=weight_update.weight,
            source="conversation",
            metadata={**metadata, "emotional_reason": weight_update.reason},
        )
        if any(word in user_message.lower() for word in ("error", "bug", "crash", "failed")):
            self._journal_record(
                "error_seen",
                self.life.mood,
                self.life.presence.value,
                user_message[:240],
                related_project=related_project,
                emotional_weight=0.7,
                source="conversation",
                metadata=metadata,
            )
        if (
            observation.time_of_day == "late_night"
            and (observation.active_app or "").lower() in {"code", "vscode", "devenv"}
        ):
            self._journal_record(
                "late_night_session",
                self.life.mood,
                self.life.presence.value,
                "Sampled a late-night coding session.",
                related_project=related_project,
                emotional_weight=0.55,
                source="observation_engine",
                metadata=metadata,
            )

    def _relevant_memories(self, user_message: str) -> list[Memory]:
        memories = [self._rag_result_to_memory(result) for result in self.memory_router.retrieve_relevant(user_message, top_k=6)]
        projects = [
            self._rag_result_to_memory(result)
            for result in self.memory_router.rag_memory.retrieve_relevant(
                "project",
                filters={"category": MemoryCategory.PROJECT.value},
                top_k=3,
            )
        ]
        seen: set[int | None] = set()
        combined: list[Memory] = []
        for memory in [*memories, *projects]:
            if memory.id in seen:
                continue
            seen.add(memory.id)
            combined.append(memory)
        return combined[:8]

    @staticmethod
    def _rag_result_to_memory(result) -> Memory:
        memory = result.memory
        category = memory.category if memory.category in {item.value for item in MemoryCategory} else MemoryCategory.EVENT.value
        return Memory(
            id=memory.id,
            category=MemoryCategory(category),
            content=memory.content,
            importance=memory.importance,
            source=memory.source,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            last_accessed_at=memory.last_accessed_at,
            access_count=memory.access_count,
            confidence=memory.confidence,
            emotional_weight=float(memory.metadata.get("emotional_weight", memory.importance)),
            metadata=memory.metadata,
        )

    @staticmethod
    def _related_project(memories: list[Memory], user_message: str) -> str | None:
        explicit = re.search(r"(?:working on|building)\s+([^.!?]+)", user_message, re.IGNORECASE)
        if explicit:
            return explicit.group(1).strip()[:80]

        for memory in memories:
            if memory.category != MemoryCategory.PROJECT:
                continue
            match = re.search(r"(?:working on|building)\s+(.+)", memory.content, re.IGNORECASE)
            project = (match.group(1) if match else memory.content).strip().rstrip(".")
            if project and (not user_message or project.lower() in user_message.lower()):
                return project[:80]
        return None

    @staticmethod
    def _known_projects(
        memories: list[Memory],
        journal_entries: list,
        favorite_project: str | None = None,
    ) -> list[str]:
        projects: list[str] = []
        if favorite_project:
            projects.append(favorite_project)
        for memory in memories:
            if memory.category != MemoryCategory.PROJECT:
                continue
            match = re.search(r"(?:working on|building)\s+(.+)", memory.content, re.IGNORECASE)
            project = (match.group(1) if match else memory.content).strip().rstrip(".")
            if project:
                projects.append(project[:80])
        for entry in journal_entries:
            project = getattr(entry, "related_project", None)
            if project:
                projects.append(str(project)[:80])
        unique: list[str] = []
        for project in projects:
            if project and project.lower() not in {item.lower() for item in unique}:
                unique.append(project)
        return unique[:5]

    @staticmethod
    def _expression_for(tagged_mood: str, semantic_mood: str) -> str:
        if tagged_mood in {"happy", "sleepy", "thinking", "angry", "idle"}:
            return tagged_mood
        return EXPRESSION_MAP.get(semantic_mood, "idle")


def _split_title_description(text: str) -> tuple[str, str]:
    """Allow simple `/issue new title | details` without requiring a form."""

    if "|" not in text:
        return text[:120] or "beta issue", text
    title, description = text.split("|", 1)
    return title.strip()[:120] or "beta issue", description.strip()


def _guess_issue_category(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("crash", "crashed", "traceback")):
        return "crash"
    if any(word in lowered for word in ("voice", "tts", "sound")):
        return "voice"
    if "rvc" in lowered:
        return "rvc"
    if any(word in lowered for word in ("window", "button", "gui", "screen", "ui")):
        return "gui"
    if any(word in lowered for word in ("memory", "remember", "forgot")):
        return "memory"
    if any(word in lowered for word in ("installer", "zip", "exe", "portable")):
        return "packaging"
    if any(word in lowered for word in ("slow", "freeze", "hang", "lag")):
        return "performance"
    return "other"


def _guess_issue_severity(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("critical", "data loss", "won't start", "wont start")):
        return "critical"
    if any(word in lowered for word in ("crash", "broken", "blocked")):
        return "high"
    if any(word in lowered for word in ("annoying", "confusing", "slow")):
        return "medium"
    return "low"


def _guess_feedback_type(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("bug", "broken", "crash")):
        return "bug"
    if any(word in lowered for word in ("confusing", "confused", "unclear")):
        return "confusion"
    if any(word in lowered for word in ("feature", "could you", "please add")):
        return "feature_request"
    if any(word in lowered for word in ("personality", "cute", "annoying", "sleepy")):
        return "personality"
    if any(word in lowered for word in ("slow", "lag", "performance")):
        return "performance"
    if any(word in lowered for word in ("installer", "zip", "exe")):
        return "packaging"
    return "general"


def _extract_first_url(text: str) -> str:
    match = re.search(r"\b(?:https?://)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s]*)?", text)
    return match.group(0).rstrip(".,)") if match else ""


def _looks_like_url_only(text: str) -> bool:
    stripped = text.strip()
    return bool(_extract_first_url(stripped)) and len(stripped.split()) <= 2

