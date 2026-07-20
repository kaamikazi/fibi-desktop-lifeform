# Fibi v0.30 Recording Checklist

## Before Recording

- Close notifications and chat apps.
- Hide taskbar personal items if needed.
- Close private browser windows and unrelated projects.
- Use the isolated demo profile only.
- Run `python tools\reset_demo_profile.py --confirm-demo-reset`.
- Set `$env:FIBI_DATA_DIR="E:\Fibi chubi\demo_runtime"` in the recording terminal.
- Verify Fibi starts with `python app.py`.
- Verify fallback command with `python app.py --gui-smoke`.
- Verify `/memories`, `/memory search local-first`, `/permissions`, `/safety`, and `/workflow list`.
- Test microphone level and room noise.
- Set display scaling so text is readable.
- Disable pop-ups and system notification banners.
- Keep the repository page ready only if it contains no private account overlays.
- Keep terminal font readable.
- Rehearse the route once with a timer.

## Recording

- Record at 1920x1080.
- Use 30 or 60 FPS.
- Keep cursor visible.
- Do not use copyrighted background music.
- Do not show personal notifications.
- Do not include dead time or long loading waits.
- Pause briefly between narration sections.
- Capture one clean take plus one backup.
- Do not record private browser history, Gmail, contacts, passwords, cookies, or unrelated documents.
- Do not depend on network availability.

## After Recording

- Verify audio is clear.
- Verify no private information appears.
- Verify runtime is under 3 minutes.
- Verify Fibi text is readable.
- Verify Codex and language-provider roles are explained accurately.
- Verify no claim of consciousness, AGI, production readiness, or perfect security.
- Export with common H.264 settings.
- Watch the final export end to end before uploading.
- Do not upload until manually reviewed.
