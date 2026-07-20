# Fibi v0.27 Browser Helper

Fibi can help with browser work, but she is not a browser automation agent.

## What Fibi Can Do

- Save a link note with `/browser note <url> <note>`.
- Start a manual browser session with `/browser start <goal>`.
- Prepare a checklist with `/browser plan`.
- Open a URL only after `/browser open <url>` and `browser confirm`.
- Summarize page text that you pasted or dropped as a text/HTML file.
- Create research/outreach notes from user-provided public page text.
- Remember an approved browser note summary with `/browser remember note`.

## What Fibi Cannot Do

- Read browser history, cookies, saved passwords, or credentials.
- Scrape pages silently.
- Read a URL's page contents unless you paste/drop the content.
- Auto-click, auto-scroll, auto-fill forms, or submit forms.
- Send messages, emails, purchases, or account actions.
- Bypass logins, site rules, or rate limits.

## URL Open Flow

```text
/browser open https://example.com
browser confirm
```

Fibi shows the domain first. Until you confirm, nothing opens.

## Page Text Flow

1. Copy public page text or drop a local `.html`/`.txt` file.
2. Ask `/browser summarize`.
3. Optionally save the summary with `/browser save page`.
4. Optionally remember only the approved note summary with `/browser remember note`.

If you only give Fibi a URL and ask for a summary, she will say she has the link
but not the page.

## Safety

Everything stays local. There is no browser extension, no hidden fetch, no
telemetry, no auto-upload, and no auto-download.
