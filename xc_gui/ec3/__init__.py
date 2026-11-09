"""Motore analitico EC3 (metodo delle componenti) per giunti con piastra di testa.

Python puro: nessuna dipendenza esterna, quindi entra nell'eseguibile senza
installare nulla. Interfaccia: `run(dict) -> dict` e `render_report(dict, dict)`.
"""
from .joint import check_endplate_joint, normalize_profile
from .report import render_report
from .tstub import tstub_resistance


def run(inp, engine="ec3"):
    """Punto d'ingresso comune per la GUI. 'xc' sara' aggiunto piu' avanti."""
    if engine == "ec3":
        return check_endplate_joint(inp)
    if engine == "xc":
        raise NotImplementedError("Motore XC non ancora disponibile.")
    raise ValueError(f"Motore sconosciuto: {engine}")


__all__ = ["run", "render_report", "check_endplate_joint",
           "tstub_resistance", "normalize_profile"]
