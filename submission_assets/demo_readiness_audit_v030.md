# Fibi v0.30 Demo Readiness Audit

Scope: safe under-three-minute competition demo using an isolated demo profile. Do not use real memories, private browser content, network calls, paid APIs, or personal folders during recording.

Recommended setup:

```powershell
cd "E:\Fibi chubi"
python tools\reset_demo_profile.py --confirm-demo-reset
$env:FIBI_DATA_DIR="E:\Fibi chubi\demo_runtime"
python app.py
```

| Feature | Status | Exact command or UI path | Expected output | Required setup | Possible failure points | Fallback demonstration | Privacy risk | Estimated time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Fibi desktop presence | SAFE_WITH_PREP | Run `python app.py`; show floating Fibi window | Chibi window appears with chat bubble/input and toolbar buttons | Dependencies installed; assets available | PyQt6 missing, display scaling odd, window behind another app | Run `python app.py --gui-smoke` and show `GUI_SMOKE_OK` | Low if desktop is clean | 12 sec |
| Command Center | SAFE | Click command button or use tray `Command Center`; optional `/capabilities` | Command Center lists major capabilities; `/capabilities` lists Chat, Memory, Memory Review, Safety, Workflows | App running | Dialog may cover sprite; text may be dense | Type `/capabilities` in chat | Low | 10 sec |
| Memory Review Center | SAFE_WITH_PREP | Click `Memory Review` button or tray `Memory Review`; command `/memories` | Five fictional demo memories, including two pinned memories | Run reset tool first and use `FIBI_DATA_DIR=demo_runtime` | Wrong data root shows real or empty memories | Use terminal command `/memories` inside Fibi | Medium if wrong profile; verify profile first | 18 sec |
| Memory search/list | SAFE | Type `/memory search local-first` or use search box in Memory Review Center | `Imran prefers Fibi to remain local-first.` appears | Demo profile seeded | Search typo | Use `/memories` list | Low with demo profile | 8 sec |
| Memory approve, pin, archive, delete | SAFE_WITH_PREP | Select fictional memory; click pin/archive/delete, or command `/memory delete 5` then `memory delete confirm` | Delete target is `Demo memory scheduled for deletion.`; reply says `forgot one memory crumb.` | Demo profile seeded and memory IDs visible | ID changes if extra demo data was added | Delete from UI by selecting visible row named exactly `Demo memory scheduled for deletion.` | Low with demo-only memory | 15 sec |
| Memory learning pause/resume | SAFE | `/memory learning off`, then `/memory learning on` | `memory paused.` then `memory learning on.` | None beyond demo profile | None expected | Show Memory Consent panel or `/memory consent` | Low | 8 sec |
| Sensitive-memory guard | SAFE_WITH_PREP | Type `/memory safety`; optionally show the fake manual prop `FAKE_DEMO_KEY_NOT_REAL_12345` without storing it | Fibi says `secrets never stored. sensitive notes need approval.` | Use fake value only; no real secrets on screen | Free-form `remember ...` text may route as normal chat in v0.30 | Use `/memory safety` as the primary proof and narrate the fake manual attempt | Low if fake value only | 12 sec |
| Workflow Recipes | SAFE | `/workflow list`; `/workflow start Daily Fibi Startup Check`; `/workflow next` | Recipe list, guided step, next command hint; no auto-run | Demo profile reset clears workflow state | A workflow already active | Run reset tool before take | Low | 18 sec |
| Permission overview | SAFE | `/permissions` | Shows desktop actions, project checks, patch apply, browser helper, voice, cloud, memory learning | None | Text dense | Use Command Center permissions area | Low | 10 sec |
| Safety/refusal explanation | SAFE | `/safety` and `/refusals` | Local-first, cloud off, no hidden browsing, no auto-send/buy/patch/destructive commands | None | None expected | Use README safety section | Low | 12 sec |
| GUI health/status | SAFE_WITH_PREP | `/health gui` | Version, mood, RAG ok, memory review count, commands mapped, workflow status | Demo profile seeded | Worker status may vary; uptime changes | `python app.py --gui-smoke` | Low; paths reveal local demo root only | 10 sec |
| Packaged Windows executable | SAFE_WITH_PREP | Show `dist\Fibi Chubi\Fibi Chubi.exe` in File Explorer or terminal listing | Local beta executable exists beside ignored bundle files | Existing local build output present | Build output not committed; may be absent on another machine | Show `dist\Fibi_Chubi_v0.30.0_windows_beta.zip` and test output instead | Low if no user folders visible | 8 sec |

Unreliable or excluded:

- Installer generation: DO_NOT_DEMO. Inno Setup is not required for the demo and may be unavailable.
- Voice recognition: DO_NOT_DEMO. It depends on microphone and local audio conditions.
- External websites or browser automation: DO_NOT_DEMO. Not needed for the message.
- Real memory history: DO_NOT_DEMO. Use only `demo_runtime`.
