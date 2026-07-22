# Fibi Companion Product Direction

## Product Identity

Fibi Companion is an open-source desktop companion: a small, friendly character
that offers concise chat, safe desktop shortcuts, registered-project help, and a
small amount of user-approved memory. It is not AGI, an autonomous agent, a
self-modifying system, or a claim about consciousness.

## Product Principles

1. Reliability before novelty.
2. Useful answer before personality flavor.
3. Explicit user choice before automation.
4. Visible permissions and memory before hidden convenience.
5. Small, fast daily surface; detailed controls elsewhere.
6. Local storage and no telemetry by default.
7. Replaceable providers; stable application behavior.
8. Boring, documented interfaces that contributors can test.

## Two Product Surfaces

### Fibi Pet

- Default visible surface.
- Transparent, draggable, small, and optionally always on top.
- Character, concise bubble, transient text/push-to-talk input, and quick menu.
- Never becomes a permanent dashboard.

### Fibi Control Center

- Settings, providers, permissions, projects, memory, diagnostics, plugins, and
  developer controls.
- Opens on demand and uses the same runtime services as the Pet.
- Experimental features live behind clear labels and are disabled by default.

## Supported 0.4 Experience

Fibi launches, answers text questions concisely through the manually selected
provider, opens allowlisted apps/folders/URLs, opens registered projects, recalls
reviewed facts, accepts push-to-talk, and speaks through Edge TTS. Errors are
actionable and never trigger silent provider changes or desktop actions.

## Product Boundaries

- No unrestricted shell, autonomous clicks, sending, purchasing, deletion, or
  software installation.
- No permanent microphone recordings or background cloud audio.
- No automatic provider/RVC/wake configuration changes.
- No automatic permanent storage of every conversation.
- No personality, mood, or “identity” system may override a useful answer,
  permission decision, or explicit user setting.

## Memory Direction

Persist only user-approved facts, preferences, projects, and selected discussion
summaries. Every record is visible, editable, deletable, and exportable. SQLite
keyword/metadata retrieval is the dependable baseline. Semantic retrieval is an
optional implementation detail for larger collections, not the product story.

## Voice Direction

Push-to-talk and Edge TTS are supported. Wake word and RVC are experimental,
off by default, and must pass environment health checks before being described
as available. The UI always shows when a microphone is active.

## Extensibility Direction

Plugins will extend commands, tools, menus, settings, and integrations through a
small versioned API. They declare permissions and receive capability-limited
services, never `FibiCore`, database connections, API keys, or arbitrary runtime
objects.

## Success Measures

- A new user installs and sees the Pet in under five minutes.
- The Pet appears within three seconds on supported hardware.
- Daily actions are predictable and reversible where applicable.
- Contributors can locate a capability owner in under ten minutes.
- Memory and provider behavior can be explained without implementation jargon.
- Crashes, orphan workers, secret leaks, and silent actions are release blockers.
