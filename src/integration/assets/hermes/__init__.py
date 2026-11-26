"""Hermes plugin installed by Herdr to report session identity and profile labels."""

# HERDR_INTEGRATION_ID=hermes
# HERDR_INTEGRATION_VERSION=6

from __future__ import annotations

import os
import subprocess
import time

_SOURCE = "herdr:hermes"
_AGENT = "hermes"
_INTERACTIVE_PLATFORMS = {"cli", "tui", "desktop", "acp"}


def _pane_id() -> str | None:
    if os.environ.get("HERDR_ENV") != "1":
        return None
    return os.environ.get("HERDR_PANE_ID", "").strip() or None


def _send_session(session_id: str, start_source: str) -> None:
    pane_id = _pane_id()
    if pane_id is None:
        return
    command = [
        os.environ.get("HERDR_BIN_PATH") or "herdr",
        "pane",
        "report-agent-session",
        pane_id,
        "--source",
        _SOURCE,
        "--agent",
        _AGENT,
        "--seq",
        str(time.time_ns()),
        "--agent-session-id",
        session_id,
        "--session-start-source",
        start_source,
    ]
    try:
        kwargs = {"timeout": 1, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.run(command, check=False, **kwargs)
    except Exception:
        pass


def _report_session(start_source: str, **kwargs) -> None:
    if os.environ.get("HERMES_SINGLE_QUERY_SESSION") == "1":
        return
    if kwargs.get("platform") not in _INTERACTIVE_PLATFORMS:
        return
    session_id = kwargs.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return
    _send_session(session_id, start_source)


def _report_profile(**kwargs) -> None:
    if kwargs.get("platform") not in _INTERACTIVE_PLATFORMS:
        return
    pane_id = _pane_id()
    if pane_id is None or os.environ.get("HERMES_SINGLE_QUERY_SESSION") == "1":
        return
    try:
        from hermes_cli.profiles import get_active_profile_name

        profile = get_active_profile_name()
        if profile in {"default", "custom"} or not profile:
            return
        command = [
            os.environ.get("HERDR_BIN_PATH") or "herdr",
            "pane",
            "report-metadata",
            pane_id,
            "--source",
            "herdr:hermes-profile",
            "--agent",
            _AGENT,
            "--display-agent",
            profile,
        ]
        options = {"timeout": 1, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.run(command, check=False, **options)
    except Exception:
        pass


def _session_started(**kwargs) -> None:
    _report_session("startup", **kwargs)
    _report_profile(**kwargs)


def _session_reset(**kwargs) -> None:
    _report_session("new", **kwargs)


def _session_observed(**kwargs) -> None:
    if kwargs.get("platform") == "cli":
        _report_session("resume", **kwargs)


def register(ctx):
    ctx.register_hook("on_session_start", _session_started)
    ctx.register_hook("on_session_reset", _session_reset)
    ctx.register_hook("pre_llm_call", _session_observed)
