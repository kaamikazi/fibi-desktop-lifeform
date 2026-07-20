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

Examples:

```text
/help search browser
/capabilities
/permissions
/workflow list
/browser safety
/issue new voice squeaked | steps here
/support bundle
```

The registry does not run commands. It only helps users discover commands and
understand risk.
