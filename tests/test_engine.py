"""Test con valori calcolati a mano (kN, mm). Esegui dalla radice del repo: python -m pytest -q"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from xc_gui.ec3 import render_report, run, tstub_resistance  # noqa: E402


def load_example():
    with open(os.path.join(ROOT, "examples", "nodo.json"), encoding="utf-8") as f:
        return json.load(f)


def comp(res, name):
    return next(c for c in res["components"] if c["name"] == name)


def test_bolt_resistances_m20_88():
    res = run(load_example())
    assert comp(res, "Bullone: trazione")["rd"] == pytest.approx(0.9 * 800 * 245 / 1.25)
    assert comp(res, "Bullone: taglio")["rd"] == pytest.approx(0.6 * 800 * 245 / 1.25)


def test_row_forces_triangular_distribution():
    res = run(load_example())
    hi = [314.65, 234.65, 154.65]
    k = 120e6 / sum(h * h for h in hi)
    rows = res["intermediate"]["row_tension_N"]
    assert rows[0] == pytest.approx(k * hi[0], rel=1e-6)
    assert sum(rows) == pytest.approx(res["intermediate"]["compression_force_N"])
    assert sum(t * h for t, h in zip(rows, hi)) == pytest.approx(120e6, rel=1e-6)


def test_tstub_hand_calculation():
    ft, mode, det = tstub_resistance(150, 150, 30, 50, 50, 20, 355, 141120.0, 2, 1.0)
    mpl = 0.25 * 150 * 20**2 * 355
    assert det["modes"]["1"] == pytest.approx(4 * mpl / 30)
    assert det["modes"]["2"] == pytest.approx((2 * mpl + 37.5 * 282240) / 67.5)
    assert mode == "3" and ft == pytest.approx(282240.0)


def test_example_hand_values_ntc():
    res = run(load_example())
    # Fw,Rd flangia: fu/(sqrt3*0.9*1.25)*6*(2*150-7.1-30) = 396.7 kN
    assert comp(res, "Saldatura ala trave-piastra")["rd"] / 1e3 == pytest.approx(396.7, abs=0.2)
    # Fc,wc,Rd con gM1=1.05: 380.2/1.05 = 362.1 kN
    assert comp(res, "Anima della colonna in compressione trasversale")["rd"] / 1e3 == pytest.approx(362.1, abs=0.3)
    # Vwp,Rd con gM0=1.05: 464.5/1.05 = 442.4 kN
    assert comp(res, "Pannello d'anima della colonna a taglio")["rd"] / 1e3 == pytest.approx(442.4, abs=0.3)


def test_example_status_and_missing_components():
    res = run(load_example())
    assert res["overall"] == "NON VERIFICATO"
    assert len(res["not_implemented"]) == 4


def test_never_verified_while_components_missing():
    inp = load_example()
    inp["plate"]["weld_throat"] = 12.0
    inp["loads"]["M"] = 20.0
    inp["loads"]["V"] = 20.0
    res = run(inp)
    assert res["failed"] == []
    assert res["overall"] == "INCOMPLETO"


def test_profile_name_normalised_and_unknown_profile():
    inp = load_example()
    inp["beam"] = "ipe300"
    assert run(inp)["overall"] == "NON VERIFICATO"
    inp["beam"] = "IPE 999"
    with pytest.raises(ValueError):
        run(inp)


def test_negative_moment_rejected():
    inp = load_example()
    inp["loads"]["M"] = -10.0
    with pytest.raises(ValueError):
        run(inp)


def test_report_renders():
    inp = load_example()
    text = render_report(inp, run(inp))
    assert "NON IMPLEMENTATO" in text and "Esito" in text
