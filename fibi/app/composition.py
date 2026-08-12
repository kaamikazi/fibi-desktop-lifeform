"""Application composition root for Fibi.

Only this module knows how the concrete top-level engines fit together. Core
behavior and UI adapters receive the completed graph instead of rebuilding it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any, Callable

from fibi.app.contracts import (
    DesktopActionService,
    LanguageProvider,
    MemoryQueryService,
    ProjectService,
    SpeechToTextService,
    TextToSpeechService,
)
from fibi.app.runtime import ApplicationRuntime, RuntimeConfiguration
from fibi.environment import resolve_environment
from fibi.runtime_paths import is_packaged, project_root, runtime_info

if TYPE_CHECKING:
    from fibi.engines.core import FibiCore

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ApplicationServices:
    """Typed, explicit dependency graph consumed by ``FibiCore``."""

    life: Any
    memory: Any
    privacy: Any
    observation: Any
    journal: Any
    patterns: Any
    attention: Any
    habits: Any
    personality: Any
    model: LanguageProvider
    nvidia_model: LanguageProvider
    model_router: Any
    provider_registry: Any
    provider_selection: Any
    generation_service: Any
    provider_diagnostics: Any
    reactions: Any
    rituals: Any
    motion: Any
    timing: Any
    repetition: Any
    inner_life: Any
    preferences: Any
    opinions: Any
    memory_care: Any
    relationship: Any
    boundary: Any
    social: Any
    classifier: Any
    micro_brain: Any
    budget: Any
    route_decisions: Any
    health: Any
    tts_manager: TextToSpeechService
    warmup: Any
    app_settings: Any
    autostart: Any
    data_health: Any
    asset_health: Any
    action_settings: Any
    action_intents: Any
    permissions: Any
    app_index: Any
    desktop_actions: DesktopActionService
    action_confirmations: Any
    action_journal: Any
    voice_settings: Any
    speech_recognition: SpeechToTextService
    voice_router: Any
    voice_health: Any
    voice_skin_settings: Any
    rvc_voice_skin: Any
    voice_cache: Any
    secret_sanitizer: Any
    context_engine: Any
    file_reader: Any
    project_workspace: ProjectService
    project_edit_planner: Any
    memory_query: MemoryQueryService | None = field(default=None, init=False)
    context_broker_preview: Any = field(default=None, init=False)
    _partial_stopped: bool = False

    def core_arguments(self) -> dict[str, Any]:
        """Return explicit constructor arguments without exposing a locator."""

        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if not item.name.startswith("_")
            and item.name
            not in {
                "tts_manager",
                "memory_query",
                "context_broker_preview",
            }
        }

    def stop_partial(self) -> None:
        """Best-effort cleanup for a failed build or completed runtime."""

        if self._partial_stopped:
            return
        self._partial_stopped = True
        for service in (self.tts_manager, self.warmup):
            stop = getattr(service, "stop", None)
            if callable(stop):
                try:
                    stop()
                except Exception:
                    LOGGER.exception("Could not stop partially built service %s", type(service).__name__)


def resolve_runtime_configuration(*, gui_smoke: bool = False) -> RuntimeConfiguration:
    """Resolve paths and environment exactly once for one runtime build."""

    environment = resolve_environment(project_root(), packaged=is_packaged())
    return RuntimeConfiguration(runtime_info(), environment, gui_smoke=gui_smoke)


def build_services(configuration: RuntimeConfiguration) -> ApplicationServices:
    """Construct the concrete service graph in dependency order."""

    # Imports stay local so .env and packaged paths are resolved before modules
    # such as fibi.settings snapshot process configuration.
    from fibi.engines.action_confirmation_engine import ActionConfirmationEngine
    from fibi.engines.action_intent_detector import ActionIntentDetector
    from fibi.engines.action_journal_engine import ActionJournalEngine
    from fibi.engines.action_settings_engine import ActionSettingsEngine
    from fibi.engines.app_index_engine import AppIndexEngine
    from fibi.engines.app_settings_engine import AppSettingsEngine
    from fibi.engines.asset_health_engine import AssetHealthEngine
    from fibi.engines.attention_engine import AttentionEngine
    from fibi.engines.autostart_engine import AutostartEngine
    from fibi.engines.boundary_engine import BoundaryEngine
    from fibi.engines.context_engine import ContextEngine
    from fibi.engines.data_health_engine import DataHealthEngine
    from fibi.engines.desktop_action_engine import DesktopActionEngine
    from fibi.engines.fast_response_classifier import FastResponseClassifier
    from fibi.engines.file_reader_engine import FileReaderEngine
    from fibi.engines.habit_engine import HabitEngine
    from fibi.engines.inner_life_engine import InnerLifeEngine
    from fibi.engines.journal_engine import JournalEngine
    from fibi.engines.life_engine import LifeEngine
    from fibi.engines.local_micro_brain import LocalMicroBrain
    from fibi.engines.memory_care_engine import MemoryCareEngine
    from fibi.engines.memory_engine import MemoryEngine
    from fibi.engines.model_engine import ModelEngine
    from fibi.engines.model_health_engine import ModelHealthEngine
    from fibi.engines.model_router import ModelRouter
    from fibi.engines.motion_engine import MotionEngine
    from fibi.engines.nvidia_model_engine import NvidiaModelEngine
    from fibi.engines.observation_engine import ObservationEngine
    from fibi.engines.opinion_engine import OpinionEngine
    from fibi.engines.pattern_engine import PatternEngine
    from fibi.engines.permission_engine import PermissionEngine
    from fibi.engines.personality_engine import PersonalityEngine
    from fibi.engines.preference_engine import PreferenceEngine
    from fibi.engines.privacy_settings_engine import PrivacySettingsEngine
    from fibi.engines.project_edit_planner import ProjectEditPlanner
    from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
    from fibi.engines.reaction_library import ReactionLibrary
    from fibi.engines.relationship_engine import RelationshipEngine
    from fibi.engines.repetition_guard import RepetitionGuard
    from fibi.engines.response_budget_engine import ResponseBudgetEngine
    from fibi.engines.ritual_engine import RitualEngine
    from fibi.engines.route_decision_engine import RouteDecisionEngine
    from fibi.engines.rvc_voice_skin_engine import RvcVoiceSkinEngine
    from fibi.engines.secret_sanitizer import SecretSanitizer
    from fibi.engines.social_context_engine import SocialContextEngine
    from fibi.engines.speech_recognition_engine import SpeechRecognitionEngine
    from fibi.engines.timing_engine import TimingEngine
    from fibi.engines.tts_manager import TtsManager
    from fibi.engines.voice_cache_engine import VoiceCacheEngine
    from fibi.engines.voice_command_router import VoiceCommandRouter
    from fibi.engines.voice_health_engine import VoiceHealthEngine
    from fibi.engines.voice_settings_engine import VoiceSettingsEngine
    from fibi.engines.voice_skin_settings_engine import VoiceSkinSettingsEngine
    from fibi.engines.warmup_engine import WarmupEngine
    from fibi.services.providers.factory import build_provider_subsystem

    life = LifeEngine()
    memory = MemoryEngine()
    privacy = PrivacySettingsEngine(life.state_path)
    observation = ObservationEngine(allow_clipboard=privacy.settings.allow_clipboard_observation)
    journal = JournalEngine(memory.database_path)
    patterns = PatternEngine(memory, journal)
    reactions = ReactionLibrary()
    model = ModelEngine()
    nvidia_model = NvidiaModelEngine()
    model_router = ModelRouter(model, nvidia_model)
    app_settings = AppSettingsEngine()
    provider_subsystem = build_provider_subsystem(model_router, app_settings)
    app_index = AppIndexEngine()
    secret_sanitizer = SecretSanitizer()
    context_engine = ContextEngine(secret_sanitizer)
    project_workspace = ProjectWorkspaceEngine(context=context_engine, sanitizer=secret_sanitizer)
    action_intents = ActionIntentDetector()
    speech_recognition = SpeechRecognitionEngine()

    return ApplicationServices(
        life=life,
        memory=memory,
        privacy=privacy,
        observation=observation,
        journal=journal,
        patterns=patterns,
        attention=AttentionEngine(),
        habits=HabitEngine(),
        personality=PersonalityEngine(memory),
        model=model,
        nvidia_model=nvidia_model,
        model_router=model_router,
        provider_registry=provider_subsystem.registry,
        provider_selection=provider_subsystem.selection,
        generation_service=provider_subsystem.generation,
        provider_diagnostics=provider_subsystem.diagnostics,
        reactions=reactions,
        rituals=RitualEngine(reactions, life.ritual_states),
        motion=MotionEngine(),
        timing=TimingEngine(),
        repetition=RepetitionGuard(life.repetition_state),
        inner_life=InnerLifeEngine(memory.database_path),
        preferences=PreferenceEngine(memory.database_path),
        opinions=OpinionEngine(memory.database_path),
        memory_care=MemoryCareEngine(memory.database_path, life.state_path),
        relationship=RelationshipEngine(life.state_path),
        boundary=BoundaryEngine(life.state_path),
        social=SocialContextEngine(),
        classifier=FastResponseClassifier(),
        micro_brain=LocalMicroBrain(),
        budget=ResponseBudgetEngine(),
        route_decisions=RouteDecisionEngine(),
        health=ModelHealthEngine(life.state_path),
        tts_manager=TtsManager(),
        warmup=WarmupEngine(),
        app_settings=app_settings,
        autostart=AutostartEngine(),
        data_health=DataHealthEngine(memory.database_path, life.state_path, app_settings.settings_path),
        asset_health=AssetHealthEngine(),
        action_settings=ActionSettingsEngine(life.state_path),
        action_intents=action_intents,
        permissions=PermissionEngine(),
        app_index=app_index,
        desktop_actions=DesktopActionEngine(app_index),
        action_confirmations=ActionConfirmationEngine(life.state_path),
        action_journal=ActionJournalEngine(),
        voice_settings=VoiceSettingsEngine(life.state_path),
        speech_recognition=speech_recognition,
        voice_router=VoiceCommandRouter(action_intents),
        voice_health=VoiceHealthEngine(speech_recognition),
        voice_skin_settings=VoiceSkinSettingsEngine(),
        rvc_voice_skin=RvcVoiceSkinEngine(),
        voice_cache=VoiceCacheEngine(),
        secret_sanitizer=secret_sanitizer,
        context_engine=context_engine,
        file_reader=FileReaderEngine(context_engine),
        project_workspace=project_workspace,
        project_edit_planner=ProjectEditPlanner(project_workspace),
    )


def build_runtime(
    *,
    gui_smoke: bool = False,
    configuration: RuntimeConfiguration | None = None,
    services_factory: Callable[[RuntimeConfiguration], ApplicationServices] = build_services,
    core_factory: Callable[..., FibiCore] | None = None,
) -> ApplicationRuntime:
    """Build one complete runtime, cleaning services after partial failure."""

    resolved = configuration or resolve_runtime_configuration(gui_smoke=gui_smoke)
    services: ApplicationServices | None = None
    try:
        services = services_factory(resolved)
        if core_factory is None:
            from fibi.engines.core import FibiCore

            core_factory = FibiCore
        core = core_factory(services=services, tts_manager=services.tts_manager)
        _attach_memory_read_boundary(services, core)
        return ApplicationRuntime(resolved, services, core)
    except Exception:
        if services is not None:
            services.stop_partial()
        LOGGER.exception("Fibi runtime composition failed")
        raise


def _attach_memory_read_boundary(services: ApplicationServices, core: FibiCore) -> None:
    """Attach Stage 1 reads after Core has created its existing RAG owner."""

    from fibi.engines.secret_sanitizer import SecretSanitizer
    from fibi.engines.sensitive_memory_guard import SensitiveMemoryGuard
    from fibi.memory.context_preview import ContextBrokerPreview
    from fibi.memory.query_service import CompositeMemoryQueryService
    from fibi.memory.read_adapters import LegacyMemoryReadAdapter, RAGMemoryReadAdapter
    from fibi.memory.read_policy import MemoryReadPolicy

    if services.memory_query is not None:
        return
    sanitizer = getattr(services, "secret_sanitizer", None) or SecretSanitizer()
    guard = getattr(core, "sensitive_memory_guard", None) or SensitiveMemoryGuard(sanitizer)
    policy = MemoryReadPolicy(sanitizer, guard)
    router = getattr(core, "memory_router", None)
    facade = getattr(router, "rag_memory", None)
    rag_service = getattr(facade, "service", None)
    legacy_adapter = LegacyMemoryReadAdapter(services.memory, policy)
    rag_adapter = RAGMemoryReadAdapter(rag_service, policy)
    query_service = CompositeMemoryQueryService((legacy_adapter, rag_adapter))
    services.memory_query = query_service
    services.context_broker_preview = ContextBrokerPreview(sanitizer, enabled=False)
