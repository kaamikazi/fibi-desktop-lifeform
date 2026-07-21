"""Local action intent detection for direct user commands."""

from __future__ import annotations

import re
import unicodedata

from fibi.engines.action_allowlists import KNOWN_WEBSITES, SAFE_COMMANDS, named_user_folders
from fibi.engines.types import ActionIntent

DATE_QUESTIONS = {
    "what's the date",
    "whats the date",
    "what is the date",
    "what date is it",
    "today's date",
    "todays date",
    "date today",
    "current date",
    "what day is it",
    "day today",
}

TIME_QUESTIONS = {
    "what time is it",
    "current time",
    "time now",
    "what's the time",
    "whats the time",
    "tell me the time",
}

BLOCKED_PATTERNS = (
    ("delete_file", r"\b(delete|remove|erase)\b.+\b(file|folder|this)\b"),
    ("modify_file", r"\b(modify|edit|rewrite|overwrite)\b.+\b(file|folder)\b"),
    ("run_terminal_command", r"\b(run|execute)\b.+\b(command|terminal|powershell|cmd)\b"),
    ("send_message", r"\b(send|text)\b.+\b(message|dm|chat)\b"),
    ("send_email", r"\b(send|write)\b.+\b(email|mail)\b"),
    ("read_private_messages", r"\b(read|open|check)\b.+\b(messages|dms|inbox)\b"),
    ("read_clipboard", r"\b(read|show|check)\b.+\bclipboard\b"),
    ("purchase", r"\b(buy|purchase|order)\b"),
    ("login_action", r"\b(log in|login|sign in)\b"),
    ("password_action", r"\b(password|passcode|2fa)\b"),
    ("install_software", r"\b(install|download and install|setup)\b.+\b(app|software|package|program)\b"),
    ("autonomous_clicking", r"\b(click for me|click around|auto click)\b"),
    ("autonomous_typing", r"\b(type for me|auto type)\b"),
)


class ActionIntentDetector:
    """Detect safe manual action requests before model routing."""

    def detect(self, user_message: str, direct_user_initiated: bool = True) -> ActionIntent | None:
        if not direct_user_initiated:
            return None
        text = user_message.strip()
        if not text:
            return None
        lowered = self._normalize(text)

        safe_command = re.match(r"^run\s+(.+)$", lowered)
        if safe_command and safe_command.group(1) in SAFE_COMMANDS:
            return ActionIntent("run_safe_command", target=safe_command.group(1), raw_text=text)
        if safe_command:
            return ActionIntent("run_terminal_command", target=safe_command.group(1), raw_text=text)

        project_match = re.match(r"^open\s+(?:my\s+)?(.+?)\s+project\s+in\s+(?:vs\s*code|vscode)$", lowered)
        if project_match:
            project_name = project_match.group(1).strip()
            return ActionIntent("open_project_vscode", target=project_name, raw_text=text)

        create_match = re.match(
            r"^create\s+(?:a\s+)?folder\s+(?:named\s+)?(.+?)\s+(?:on|in)\s+(desktop|downloads|documents)$",
            lowered,
        )
        if create_match:
            parent = named_user_folders()[create_match.group(2)]
            return ActionIntent("create_folder", target=str(parent / create_match.group(1).strip()), raw_text=text)

        copy_match = re.match(r"^copy\s+(?:this\s+)?text(?:\s*:\s*|\s+)?(.*)$", text, re.IGNORECASE)
        if copy_match:
            copy_target = copy_match.group(1).strip() or "this text"
            return ActionIntent("copy_text", target=copy_target, raw_text=text)

        if re.search(r"\b(type for me|auto type)\b", lowered):
            return ActionIntent("autonomous_typing", raw_text=text)
        type_match = re.match(r"^type\s+(?:this\s+)?(?:text\s*:?\s*)?(.+)$", text, re.IGNORECASE)
        if type_match:
            return ActionIntent("type_text", target=type_match.group(1).strip(), raw_text=text)

        for action_type, pattern in BLOCKED_PATTERNS:
            if re.search(pattern, lowered):
                return ActionIntent(action_type, raw_text=text, direct_user_initiated=True)

        utility_intent = self._date_time_intent(lowered)
        if utility_intent:
            return ActionIntent(utility_intent, raw_text=text)
        if lowered in TIME_QUESTIONS or lowered in {"time"}:
            return ActionIntent("tell_time", raw_text=text)
        if lowered in DATE_QUESTIONS or lowered in {"date"}:
            return ActionIntent("tell_date", raw_text=text)
        if lowered in {"volume up", "turn volume up", "raise volume"}:
            return ActionIntent("volume_up", raw_text=text)
        if lowered in {"volume down", "turn volume down", "lower volume", "lower the volume"}:
            return ActionIntent("volume_down", raw_text=text)
        if lowered in {"mute", "mute volume", "mute audio"}:
            return ActionIntent("mute", raw_text=text)
        if lowered in {"unmute", "unmute volume", "unmute audio"}:
            return ActionIntent("unmute", raw_text=text)
        if lowered in {"refresh apps", "refresh app list", "refresh app index"}:
            return ActionIntent("refresh_app_index", raw_text=text)
        if lowered in {"list apps", "list known apps", "show apps"}:
            return ActionIntent("list_known_apps", raw_text=text)

        match = re.match(r"^(find app|search apps?|app search)\s+(.+)$", lowered)
        if match:
            query = text.split(maxsplit=2)[-1].strip()
            return ActionIntent("search_known_apps", query=query, raw_text=text)

        if re.search(r"\b(take|capture)\b.+\bscreenshot\b", lowered) or lowered == "screenshot":
            return ActionIntent("screenshot", raw_text=text)
        if lowered in {"shutdown pc", "shut down pc", "shutdown computer", "turn off computer"}:
            return ActionIntent("shutdown_pc", raw_text=text)
        if lowered in {"restart pc", "restart computer", "reboot pc"}:
            return ActionIntent("restart_pc", raw_text=text)

        match = re.match(r"^(search youtube for|search youtube|youtube search|youtube)\s+(.+)$", lowered)
        if match:
            query = self._tail_from_original(text, match.group(1))
            return ActionIntent("youtube_search", query=query, raw_text=text)

        match = re.match(r"^(wiki|wikipedia|search wikipedia for|search wikipedia)\s+(.+)$", lowered)
        if match:
            query = self._tail_from_original(text, match.group(1))
            return ActionIntent("wikipedia_search", query=query, raw_text=text)

        match = re.match(r"^(search google for|google|search for|search)\s+(.+)$", lowered)
        if match:
            query = self._tail_from_original(text, match.group(1))
            return ActionIntent("web_search", query=query, raw_text=text)

        match = re.match(r"^open\s+(.+)$", lowered)
        if match:
            target = text.split(maxsplit=1)[1].strip()
            normalized = target.lower()
            if normalized in named_user_folders():
                return ActionIntent("open_folder", target=str(named_user_folders()[normalized]), raw_text=text)
            if normalized in KNOWN_WEBSITES:
                return ActionIntent("open_website", target=KNOWN_WEBSITES[normalized], raw_text=text)
            if normalized.startswith(("http://", "https://")):
                return ActionIntent("open_website", target=target, raw_text=text)
            return ActionIntent("open_app", target=target, raw_text=text)

        return None

    @staticmethod
    def _tail_from_original(original: str, matched_prefix: str) -> str:
        words = matched_prefix.split()
        return " ".join(original.split()[len(words):]).strip()

    @staticmethod
    def _date_time_intent(normalized: str) -> str:
        cleaned = unicodedata.normalize("NFKC", normalized)
        words = set(re.findall(r"[a-z0-9]+", cleaned.replace("'", "")))
        if not words:
            return ""
        asks_utility = bool(
            words
            & {
                "what",
                "whats",
                "is",
                "today",
                "todays",
                "current",
                "now",
                "tell",
                "me",
                "day",
            }
        )
        if "time" in words and (asks_utility or words == {"time"}):
            return "tell_time"
        if "date" in words and (asks_utility or words == {"date"}):
            return "tell_date"
        if "day" in words and words & {"what", "today", "todays", "current"}:
            return "tell_date"
        return ""

    @staticmethod
    def _normalize(text: str) -> str:
        cleaned = text.lower().replace("’", "'").replace("‘", "'").replace("`", "'")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return re.sub(r"[.!?]+$", "", cleaned).strip()
