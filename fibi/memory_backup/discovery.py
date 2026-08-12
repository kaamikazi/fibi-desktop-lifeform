"""Structural discovery of the bounded assets needed for memory migration safety."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fibi.memory_backup.models import (
    AssetClassification,
    BackupAsset,
    BackupPlan,
    BackupStrategy,
)


@dataclass(frozen=True, slots=True)
class AssetSpecification:
    logical_id: str
    relative_path: str
    classification: AssetClassification
    asset_type: str
    required: bool
    strategy: BackupStrategy
    included: bool


DEFAULT_ASSET_SPECIFICATIONS: tuple[AssetSpecification, ...] = (
    AssetSpecification(
        "memory_database",
        "fibi_memory.db",
        AssetClassification.PRIMARY_PERSISTENCE,
        "sqlite_database",
        True,
        BackupStrategy.SQLITE_BACKUP_API,
        True,
    ),
    AssetSpecification(
        "memory_consent_state",
        "fibi_state.json",
        AssetClassification.MIGRATION_SUPPORT,
        "json_file",
        False,
        BackupStrategy.VERIFIED_FILE_COPY,
        True,
    ),
    AssetSpecification(
        "memory_deletion_audit",
        "memory/memory_deletion_log.jsonl",
        AssetClassification.MIGRATION_SUPPORT,
        "jsonl_file",
        False,
        BackupStrategy.VERIFIED_FILE_COPY,
        True,
    ),
    AssetSpecification(
        "rag_vector_index",
        "rag/fibi_rag.faiss",
        AssetClassification.DERIVED_REBUILDABLE,
        "derived_file",
        False,
        BackupStrategy.OMIT_DERIVED,
        False,
    ),
    AssetSpecification(
        "rag_vector_id_map",
        "rag/fibi_rag_ids.json",
        AssetClassification.DERIVED_REBUILDABLE,
        "derived_file",
        False,
        BackupStrategy.OMIT_DERIVED,
        False,
    ),
    AssetSpecification(
        "rag_vector_manifest",
        "rag/fibi_rag_manifest.json",
        AssetClassification.DERIVED_REBUILDABLE,
        "derived_file",
        False,
        BackupStrategy.OMIT_DERIVED,
        False,
    ),
    AssetSpecification(
        "memory_exports",
        "exports",
        AssetClassification.OUT_OF_SCOPE,
        "directory",
        False,
        BackupStrategy.EXCLUDED,
        False,
    ),
    AssetSpecification(
        "runtime_reports",
        "reports",
        AssetClassification.OUT_OF_SCOPE,
        "directory",
        False,
        BackupStrategy.EXCLUDED,
        False,
    ),
    AssetSpecification(
        "runtime_logs",
        "logs",
        AssetClassification.OUT_OF_SCOPE,
        "directory",
        False,
        BackupStrategy.EXCLUDED,
        False,
    ),
    AssetSpecification(
        "voice_cache",
        "voice_cache",
        AssetClassification.OUT_OF_SCOPE,
        "directory",
        False,
        BackupStrategy.EXCLUDED,
        False,
    ),
)


class PersistenceAssetDiscovery:
    """Discover known paths without opening or initializing persistence stores."""

    def __init__(
        self,
        specifications: tuple[AssetSpecification, ...] = DEFAULT_ASSET_SPECIFICATIONS,
    ) -> None:
        self._specifications = specifications

    def discover(self, data_root: Path, *, include_migration_support: bool = True) -> BackupPlan:
        root = Path(data_root)
        assets = []
        for specification in self._specifications:
            source = root.joinpath(*Path(specification.relative_path).parts)
            include = specification.included and (
                include_migration_support
                or specification.classification is not AssetClassification.MIGRATION_SUPPORT
            )
            assets.append(
                BackupAsset(
                    logical_id=specification.logical_id,
                    classification=specification.classification,
                    asset_type=specification.asset_type,
                    required=specification.required,
                    strategy=specification.strategy,
                    source_logical_path="data/" + specification.relative_path.replace("\\", "/"),
                    exists=source.exists(),
                    included=include,
                    source_path=source,
                )
            )
        return BackupPlan(tuple(assets), root)


__all__ = [
    "AssetSpecification",
    "DEFAULT_ASSET_SPECIFICATIONS",
    "PersistenceAssetDiscovery",
]
