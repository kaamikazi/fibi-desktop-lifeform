"""Typed target policy for Fibi's future authoritative memory service.

These models do not replace or migrate the current stores. They make the
approved data categories, consent states, and intended owners explicit while
the compatibility migration remains read-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, TypeAlias

MetadataScalar: TypeAlias = str | int | float | bool | None


class ApprovedMemoryCategory(str, Enum):
    """Small product-memory vocabulary for the initial authoritative store."""

    FACT = "fact"
    PREFERENCE = "preference"
    PROJECT = "project"
    SUMMARY = "summary"


class ConsentStatus(str, Enum):
    """User-controlled lifecycle for a proposed long-term memory."""

    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"


class SensitivityLevel(str, Enum):
    """Privacy classification independent of any language provider."""

    NORMAL = "normal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"


class MemoryStatus(str, Enum):
    """Record lifecycle; deletion remains distinct from supersession."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    DELETED = "deleted"
    EXPIRED = "expired"


class DataClass(str, Enum):
    """Conceptual classes that must not be collapsed into one memory bucket."""

    USER_APPROVED_MEMORY = "user_approved_memory"
    USER_CREATED_INFORMATION = "user_created_information"
    COMPANION_CONFIGURATION = "companion_configuration"
    COMPANION_RELATIONSHIP_STATE = "companion_relationship_state"
    TEMPORARY_CONTEXT = "temporary_context"
    OPERATIONAL_RECORD = "operational_record"
    DERIVED_INDEX = "derived_index"


class AuthoritativeOwner(str, Enum):
    """Intended service ownership after the staged compatibility migration."""

    MEMORY_SERVICE = "MemoryService"
    NOTES_SERVICE = "NotesService"
    REMINDER_SERVICE = "ReminderService"
    COMPANION_STATE_SERVICE = "CompanionStateService"
    CONVERSATION_STORE = "ConversationStore"
    PROJECT_SERVICE = "ProjectService"
    WORK_SESSION_SERVICE = "WorkSessionService"
    PERMISSION_AUDIT_SERVICE = "PermissionAuditService"
    TASK_AUDIT_SERVICE = "TaskAuditService"
    SEARCH_INDEX = "SearchIndex"


@dataclass(frozen=True, slots=True)
class OwnershipRule:
    """Assign exactly one intended owner to one concrete persistent data type."""

    record_type: str
    data_class: DataClass
    owner: AuthoritativeOwner
    description: str


@dataclass(frozen=True, slots=True)
class ApprovedMemoryRecord:
    """Provider-neutral target record used for design and contract tests only."""

    record_id: int
    category: ApprovedMemoryCategory
    content: str
    subject_key: str
    importance: float
    confidence: float
    source: str
    consent_status: ConsentStatus
    created_at: str
    updated_at: str
    last_used_at: str = ""
    expires_at: str = ""
    sensitivity: SensitivityLevel = SensitivityLevel.NORMAL
    status: MemoryStatus = MemoryStatus.ACTIVE
    supersedes_id: int | None = None
    metadata: Mapping[str, MetadataScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.record_id < 1:
            raise ValueError("record_id must be positive")
        if not self.content.strip():
            raise ValueError("memory content cannot be empty")
        if not self.source.strip():
            raise ValueError("memory source cannot be empty")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance must be between 0 and 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if len(self.subject_key) > 160:
            raise ValueError("subject_key is too long")
        if len(self.metadata) > 16:
            raise ValueError("metadata is limited to 16 fields")
        for key, value in self.metadata.items():
            if not key or len(key) > 64:
                raise ValueError("metadata keys must contain 1-64 characters")
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise TypeError("metadata values must be scalar")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def eligible_for_model_context(self) -> bool:
        """Return whether the record may enter a provider-neutral context set."""

        return (
            self.consent_status is ConsentStatus.APPROVED
            and self.status is MemoryStatus.ACTIVE
            and self.sensitivity is SensitivityLevel.NORMAL
        )


def ownership_rules() -> tuple[OwnershipRule, ...]:
    """Return the target ownership map used by docs and architecture tests."""

    return (
        OwnershipRule("approved_fact", DataClass.USER_APPROVED_MEMORY, AuthoritativeOwner.MEMORY_SERVICE, "Approved user fact."),
        OwnershipRule("approved_preference", DataClass.USER_APPROVED_MEMORY, AuthoritativeOwner.MEMORY_SERVICE, "Approved user preference."),
        OwnershipRule("registered_project_memory", DataClass.USER_APPROVED_MEMORY, AuthoritativeOwner.MEMORY_SERVICE, "Approved project memory summary."),
        OwnershipRule("selected_discussion_summary", DataClass.USER_APPROVED_MEMORY, AuthoritativeOwner.MEMORY_SERVICE, "Explicitly selected conversation summary."),
        OwnershipRule("explicit_note", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.NOTES_SERVICE, "User-created note."),
        OwnershipRule("reminder", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.REMINDER_SERVICE, "User-created reminder or schedule item."),
        OwnershipRule("registered_project", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.PROJECT_SERVICE, "Approved project registration and project note."),
        OwnershipRule("work_session", DataClass.USER_CREATED_INFORMATION, AuthoritativeOwner.WORK_SESSION_SERVICE, "Supervised work-session state."),
        OwnershipRule("companion_configuration", DataClass.COMPANION_CONFIGURATION, AuthoritativeOwner.COMPANION_STATE_SERVICE, "Voice, theme, presentation, and interaction configuration."),
        OwnershipRule("relationship_presentation", DataClass.COMPANION_RELATIONSHIP_STATE, AuthoritativeOwner.COMPANION_STATE_SERVICE, "Bounded warmth, comfort, and interaction presentation state."),
        OwnershipRule("recent_conversation", DataClass.TEMPORARY_CONTEXT, AuthoritativeOwner.CONVERSATION_STORE, "Bounded recent turns with explicit retention."),
        OwnershipRule("memory_consent", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.PERMISSION_AUDIT_SERVICE, "Memory consent and approval history."),
        OwnershipRule("desktop_action_audit", DataClass.OPERATIONAL_RECORD, AuthoritativeOwner.TASK_AUDIT_SERVICE, "Permission-checked desktop action record."),
        OwnershipRule("semantic_index", DataClass.DERIVED_INDEX, AuthoritativeOwner.SEARCH_INDEX, "Disposable embeddings, FAISS IDs, manifests, and caches."),
    )


def duplicate_record_types(rules: tuple[OwnershipRule, ...] | None = None) -> set[str]:
    """Return record types assigned more than once."""

    counts: dict[str, int] = {}
    for rule in rules or ownership_rules():
        counts[rule.record_type] = counts.get(rule.record_type, 0) + 1
    return {record_type for record_type, count in counts.items() if count != 1}
