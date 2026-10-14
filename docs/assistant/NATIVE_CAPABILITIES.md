# Fibi Native Capabilities

This is the model-independent map for deterministic desktop work. Direct user
text follows `ActionIntentDetector` → `PermissionEngine` →
`DesktopActionEngine`; provider output never invokes an effect. Paths and
search results are bounded to named user folders or explicitly registered
project roots.

## Supported actions

| Action ID | User-visible purpose / implementation | Permission and confirmation | Reversible | Platform | Classification | Tests and current limits |
| --- | --- | --- | --- | --- | --- | --- |
| `open_app` | Open a known app through `AppIndexEngine` and `DesktopActionEngine`. | LOW_RISK; no confirmation. | No | Windows | RELIABLE | Native reliability tests; aliases, manual registry, Start Menu, known locations, and PATH. No arbitrary executable path or arguments. |
| `open_folder` | Open a named user folder or approved folder with the OS default handler. | LOW_RISK; no confirmation. | Yes | Windows | RELIABLE | Native reliability tests; canonical approved roots only. |
| `open_file` | Open one approved file with its OS default application. | LOW_RISK; no confirmation. | Yes | Windows | RELIABLE | Native reliability tests; registered project or named user folder only, secret filenames rejected. |
| `open_project` | Resolve a registered project name/alias and open its folder. | LOW_RISK; no confirmation. | Yes | Windows | RELIABLE | Native smoke and reliability tests; registration is explicit and moved roots fail cleanly. |
| `open_project_vscode` | Resolve a registered project, resolve VS Code, and launch `[executable, project]`. | LOW_RISK; no confirmation. | Yes | Windows | RELIABLE | Mocked launch tests; real VS Code discovery remains clean-machine validation. `shell=True` is not used. |
| `open_website` | Open an allowlisted HTTP/HTTPS URL in the default browser. | LOW_RISK; no confirmation. | Yes | Windows | RELIABLE | Native smoke and URL tests; no browser automation and current host allowlist applies. |
| `web_search`, `youtube_search`, `wikipedia_search` | Open a fixed-provider search URL with an encoded query. | LOW_RISK; no confirmation. | Yes | Windows | RELIABLE | Existing action tests; fixed hosts only, no page interaction. |
| `copy_text` | Copy explicit, bounded, non-secret user text. | LOW_RISK; no confirmation. | No | Windows | RELIABLE | Native smoke and action tests; no clipboard reads, history, surveillance, or secret logging. Empty payloads fail cleanly. |
| `type_text` | Type explicit text into the active application. | LOW_RISK; confirmation required. | No | Windows | PARTIAL | Existing confirmation tests; optional `pyautogui` dependency and no autonomous typing. |
| `create_folder` | Create one child folder below an approved root. | MODIFY_LOCAL; confirmation required. | No | Windows | PARTIAL | Existing confirmation tests; parent creation and deletion remain unavailable. |
| `run_safe_command` | Run one exact tuple from `SAFE_COMMANDS`. | MODIFY_LOCAL; confirmation required. | No | Windows | PARTIAL | Existing mocked command tests; no arbitrary terminal text, shell interpolation, or remote execution. |
| `refresh_app_index` | Explicitly refresh bounded common Windows app locations. | READ_ONLY; no confirmation. | Yes | Windows | PARTIAL | Existing app tests; no continuous scan or whole-drive indexing. |
| `list_known_apps`, `search_known_apps` | Inspect the local app registry/index. | READ_ONLY; no confirmation. | Yes | Windows | RELIABLE | Existing action tests; entries are safe metadata only. |
| `search_files` | Search safe filenames and sanitized previews in the registered project. | READ_ONLY; no confirmation. | Yes | Windows | PARTIAL | Native smoke and reliability tests; bounded depth/files/time/results, cancellation-aware, ignored directories, no whole-drive index. |
| `save_note` | Save one explicit note to the current registered project. | MODIFY_LOCAL; no confirmation under current policy. | No | Windows | PARTIAL | Native smoke and reliability tests; 500-character limit, secret guard, separate project-note store, no automatic memory write. |
| `list_notes` | Show recent explicit notes from registered projects. | READ_ONLY; no confirmation. | Yes | Windows | PARTIAL | Native smoke and reliability tests; summaries only, no edit/delete UI exists in this milestone. |
| `start_work_session` | Start the existing supervised work-session planner. | LOW_RISK; no confirmation. | Yes | Windows | PARTIAL | Native smoke plus v0.21 tests; duplicate starts reuse the active session and the planner never becomes an autonomous executor. |
| `volume_up`, `volume_down`, `mute`, `unmute` | Send one media-key action. | LOW_RISK; no confirmation. | Yes | Windows | EXPERIMENTAL | Existing action tests; optional `pyautogui` dependency. |
| `tell_time`, `tell_date` | Return local system time/date. | READ_ONLY; no confirmation. | Yes | Windows | RELIABLE | Existing action tests; local-only. |

`screenshot` remains confirmation-gated and disabled by default. Destructive
power actions, deletion, unrestricted terminal commands, private clipboard
reads, messaging/email, purchases, login/password work, installation, and
autonomous clicking remain blocked by `ActionTypes` and `PermissionEngine`.

## App discovery precedence

1. A valid explicit user registry entry.
2. Centralized known-app aliases (`VS Code`, `Visual Studio Code`, `Chrome`,
   `Google Chrome`, `Teams`, and similar forms).
3. A matching Start Menu shortcut.
4. A known Windows installation location.
5. `PATH` lookup for the known executable name.

Only a successfully resolved known app is cached. Manual registration accepts
absolute `.exe` files and rejects links/reparse points. Chat text cannot supply
an executable path or command arguments.

Start Menu alias matching is exact after normalization: `code` cannot match
CodeBlocks. File opening rejects executable, script, shortcut, and installer
suffixes so it cannot bypass the application registry. Legacy compatibility
helpers require an injected permission-checked gateway; they no longer create
their own default permissions or service graph.

## Result contract

`DesktopActionResult` preserves the legacy positional fields and adds:

- `status`: `completed`, `failed`, `blocked`, or `pending_confirmation`;
- `permission_state`: `not_checked`, `allowed`, `blocked`, or
  `pending_confirmation`;
- `error_code` and `error_category`: stable non-secret diagnostics;
- `metadata`: safe counts/source labels only;
- `reversible`: an explicit conservative flag.

User-facing action responses use concise safe messages. They do not expose
stack traces, shell command output, credentials, raw clipboard data, or private
absolute paths. The action journal stores the same redacted target policy.

## Verification path

The no-side-effect smoke path is:

```powershell
python tests/smoke_native_assistant.py
python -m pytest -q tests/test_native_action_reliability.py
```

The smoke uses temporary files and injected launch/browser/clipboard/session
callbacks. It never opens a real application, folder, URL, or clipboard.
