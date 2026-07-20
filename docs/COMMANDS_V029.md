# Fibi v0.29 Commands

Fibi now has a searchable command registry.

Use:

```text
/commands
/commands browser
/help search patch
/help search voice
```

Command metadata includes:

- command
- aliases
- category
- description
- examples
- confirmation requirement
- risk level
- capability id
- packaged-mode availability
- docs path

Common categories:

- help
- safety
- health
- voice
- actions
- project
- patch
- checks
- sessions
- workflows
- browser
- issues
- feedback
- support
- release
- debug
- packaging
- models

Examples:

```text
/help search browser
/capabilities
/permissions
/workflow list
/browser safety
/issue new voice squeaked | steps here
/support bundle
/provider status
/provider use gemini
/provider context
/provider use ollama
```

Provider commands are local control commands. Model listing, testing, and
benchmarking contact Gemini only after the user configures a key and explicitly
selects Gemini. Automated tests use mocks.

The registry does not run commands. It only helps users discover commands and
understand risk.
