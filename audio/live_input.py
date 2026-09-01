"""Capture the default system-output monitor for contextual analysis."""

import subprocess

from audio.input import AudioPlaybackError


def _run_pactl(command_runner, *arguments: str) -> str:
    try:
        result = command_runner(
            ["pactl", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioPlaybackError(
            "pactl não está instalado ou não está no PATH"
        ) from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "erro sem detalhes"
        raise AudioPlaybackError(
            f"Falha ao consultar o PipeWire/PulseAudio: {detail}"
        )
    return result.stdout


def discover_default_monitor(command_runner=subprocess.run) -> str:
    """Return the monitor source belonging to the current default sink."""
    sink = _run_pactl(command_runner, "get-default-sink").strip()
    if not sink:
        raise AudioPlaybackError("Não foi possível descobrir o sink padrão")

    expected = f"{sink}.monitor"
    sources = _run_pactl(command_runner, "list", "short", "sources")
    source_names = [
        fields[1]
        for line in sources.splitlines()
        if len(fields := line.split("\t")) > 1
    ]
    if expected not in source_names:
        raise AudioPlaybackError(f"Fonte monitor não encontrada para o sink {sink}")
    return expected
