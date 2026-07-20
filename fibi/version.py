"""Fibi application version metadata."""

from fibi.build_info import APP_VERSION, BUILD_MODE, build_summary

APP_NAME = "Fibi Chubi"
BUILD_CHANNEL = BUILD_MODE


def version_line() -> str:
    return f"{APP_NAME} v{APP_VERSION} {BUILD_CHANNEL}. tiny build creature."


def detailed_version_line() -> str:
    summary = build_summary()
    packaged = "packaged" if summary["packaged"] else "source"
    return (
        f"{APP_NAME} v{summary['app_version']} {summary['build_mode']}. "
        f"{packaged}. commit {summary['git_commit']}. built {summary['build_date']}."
    )
