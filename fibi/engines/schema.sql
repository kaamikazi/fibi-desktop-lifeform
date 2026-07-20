PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK (category IN (
        'fact', 'event', 'project', 'habit', 'belief', 'goal', 'important_moment'
    )),
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    confidence REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    emotional_weight REAL NOT NULL DEFAULT 0.5 CHECK (emotional_weight >= 0 AND emotional_weight <= 1),
    source TEXT NOT NULL DEFAULT 'conversation',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK (role IN ('user', 'fibi')),
    content TEXT NOT NULL,
    mood TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);

CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    mood TEXT NOT NULL DEFAULT 'idle',
    presence_state TEXT NOT NULL DEFAULT 'idle',
    short_summary TEXT NOT NULL,
    related_project TEXT,
    emotional_weight REAL NOT NULL DEFAULT 0.5
        CHECK (emotional_weight >= 0 AND emotional_weight <= 1),
    source TEXT NOT NULL DEFAULT 'engine',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_journal_timestamp ON journal_entries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_journal_event_type ON journal_entries(event_type);
CREATE INDEX IF NOT EXISTS idx_journal_project ON journal_entries(related_project);

CREATE TABLE IF NOT EXISTS daily_summaries (
    date TEXT PRIMARY KEY,
    main_mood TEXT NOT NULL DEFAULT 'idle',
    notable_project TEXT,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    tiny_summary TEXT NOT NULL DEFAULT '',
    emotional_weight INTEGER NOT NULL DEFAULT 0,
    notable_events_json TEXT NOT NULL DEFAULT '[]',
    projects_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_affinity (
    project_name TEXT PRIMARY KEY COLLATE NOCASE,
    mention_count INTEGER NOT NULL DEFAULT 0,
    last_seen_at TEXT,
    affection_weight REAL NOT NULL DEFAULT 0.5,
    frustration_weight REAL NOT NULL DEFAULT 0.0,
    success_weight REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_project_affinity_score
ON project_affinity(affection_weight DESC, mention_count DESC);

CREATE TABLE IF NOT EXISTS inner_life_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category TEXT NOT NULL CHECK (category IN (
        'idle_thought', 'sleepy_thought', 'curious_thought', 'project_thought',
        'memory_thought', 'nest_thought', 'dream_fragment', 'tiny_worry',
        'tiny_pride', 'silly_thought'
    )),
    mood TEXT NOT NULL DEFAULT 'idle',
    text TEXT NOT NULL,
    related_memory_id INTEGER,
    related_project TEXT,
    emotional_weight REAL NOT NULL DEFAULT 0.2
        CHECK (emotional_weight >= 0 AND emotional_weight <= 1),
    should_surface_to_user INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'inner_life_engine',
    FOREIGN KEY (related_memory_id) REFERENCES memories(id)
);

CREATE INDEX IF NOT EXISTS idx_inner_life_timestamp
ON inner_life_entries(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_inner_life_category
ON inner_life_entries(category);

CREATE TABLE IF NOT EXISTS fibi_dreams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dream_text TEXT NOT NULL,
    mood TEXT NOT NULL DEFAULT 'sleepy',
    related_project TEXT,
    emotional_weight REAL NOT NULL DEFAULT 0.2
        CHECK (emotional_weight >= 0 AND emotional_weight <= 1),
    surfaced_to_user INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_fibi_dreams_timestamp
ON fibi_dreams(timestamp DESC);

CREATE TABLE IF NOT EXISTS preferences (
    preference_key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.1
        CHECK (confidence >= 0 AND confidence <= 1),
    formed_from TEXT NOT NULL DEFAULT 'local_pattern',
    last_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opinions (
    opinion_key TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.1
        CHECK (confidence >= 0 AND confidence <= 1),
    evidence_count INTEGER NOT NULL DEFAULT 0,
    last_updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
