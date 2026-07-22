# Fibi Plugin API Draft

Status: design only. No plugin loader is shipped yet.

## Goals

Allow local, explicitly installed extensions without exposing internal engines,
secrets, databases, unrestricted subprocesses, or the Qt application object.

## Manifest

```json
{
  "name": "example.notes",
  "display_name": "Example Notes",
  "version": "0.1.0",
  "api_version": "1",
  "entry_point": "example_notes.plugin:create_plugin",
  "permissions": ["commands.register", "memory.read.approved"],
  "dependencies": [],
  "fibi_version": ">=0.4,<0.5"
}
```

Required fields are name, version, API version, entry point, permissions, and
dependencies. Names are unique reverse-domain-style identifiers. Manifests are
validated before importing plugin code.

## Contract

```python
from typing import Protocol

class Plugin(Protocol):
    def activate(self, context: "PluginContext") -> None: ...
    def deactivate(self) -> None: ...

class PluginContext(Protocol):
    @property
    def api_version(self) -> str: ...
    def register_command(self, command: "CommandContribution") -> "Registration": ...
    def register_tool(self, tool: "ToolContribution") -> "Registration": ...
    def register_menu_item(self, item: "MenuContribution") -> "Registration": ...
    def register_settings_section(self, section: "SettingsContribution") -> "Registration": ...
    def services(self) -> "CapabilityServices": ...
```

Contributions are immutable data plus callbacks. Registrations are disposable
handles. Plugins do not mutate global registries directly.

## Initial Contributions

- Commands: unique slash command, help text, argument schema, callback.
- Tools: explicit user-invoked operation with typed request/result and declared
  permissions. Tools cannot be silently invoked from model output.
- Menu items: label, location, icon identifier, callback; no raw QWidget access.
- Settings sections: declarative fields with validation and plugin-owned values.
- Integrations: adapters exposed only through approved service capabilities.

## Permission Model

Example permissions:

```text
commands.register
tools.register
ui.menu.register
ui.settings.register
memory.read.approved
memory.write.request
projects.read.registered
browser.open.request
clipboard.write.request
network.connect:<hostname>
```

No permission grants arbitrary filesystem, subprocess, environment, credential,
database, microphone, keyboard, screen, or internal-runtime access. Sensitive
operations return a user-confirmation request through Fibi's permission service.

## Loading And Isolation

1. Discover manifests only in a user-controlled local plugin directory.
2. Validate schema, API compatibility, duplicate names, entry-point syntax, and
   declared permissions before import.
3. Show requested permissions and require explicit enablement.
4. Activate one plugin at a time behind an exception boundary.
5. Disable a plugin after repeated startup failures without blocking Fibi.
6. Record metadata-only health events; never record plugin secrets or payloads.
7. Load no remote code and install no dependencies automatically.

Python plugins are not a security sandbox. Permission APIs reduce accidental
and product-level access, but a locally installed Python package can execute
code. Documentation must state this clearly. Strong isolation would require a
separate process and OS sandbox in a later API version.

## Compatibility

- API versions are integers represented as strings.
- Minor Fibi releases may add optional fields but cannot remove API v1 methods.
- Incompatible plugins remain disabled with an actionable status.
- Internal module imports are unsupported and may change without notice.
- A plugin conformance suite will validate manifests and contribution behavior.

Provider adapters are not a plugin contribution in API v1. The experimental
internal provider contract is documented for core contributors, but plugins
cannot register a provider, access provider credentials, change manual
selection, or bypass cloud-context approval. A future provider contribution
would require a separate capability, manifest permissions, health isolation,
and a stable public contract.

## Error And Performance Rules

- Callbacks return structured success/error results.
- UI callbacks must complete within 100 ms or schedule work through a provided
  task service.
- Plugin shutdown is bounded; orphan work marks the plugin unhealthy.
- Errors include plugin name and category but not private payloads.

## Not In The First Version

Marketplace, remote installation, auto-update, arbitrary model tools, raw Qt
widgets, unrestricted background jobs, and direct service-container access.
