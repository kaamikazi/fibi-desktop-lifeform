# Demo UI Polish (v0.30.2)

Fibi v0.30.2 is a presentation-only patch for the public demo. It does not
change memory, provider routing, permissions, actions, workflows, browser
safety, RAG, or voice behavior.

## Main Window

The floating companion window now has four clear zones:

1. Header with Fibi's name and the active provider badge.
2. Presence area with a larger character and speech bubble.
3. Expanding message input with fixed Mic and Send controls.
4. Compact two-row navigation for existing local destinations.

The window uses a minimum size of 580 by 620 logical pixels and a preferred
size of 680 by 660 logical pixels. Qt layouts handle resizing and Windows DPI
scaling; no chat control uses absolute positioning.

## Provider Badge

The badge is derived from existing runtime state:

- `LOCAL - Ollama`
- `CLOUD - Gemini`
- `FALLBACK - Ollama`
- `LOCAL - Fibi` when only the local direct fallback is available

The badge never displays an API key, key fragment, prompt, response, or private
context. Its tooltip describes only the active local/cloud boundary.

## Character Rendering

Expression assets are not modified. Fibi crops their shared transparent canvas
margin in memory, preserves a common padded crop for stable expression changes,
and then applies the existing aspect-ratio-preserving animation renderer.

## Verification

Focused geometry tests verify:

- input, Mic, and Send controls do not overlap
- the character remains inside its drawing area
- all footer destinations remain visible
- local, cloud, and fallback badges render from state
- visible labels do not expose provider credentials
- test data remains isolated from normal runtime data
