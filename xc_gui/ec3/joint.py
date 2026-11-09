"""Giunto trave-colonna con piastra di testa: verifiche analitiche (EN 1993-1-8).

Versione 0.1: verifica le componenti elencate in `check_endplate_joint`.
Le componenti non ancora implementate sono dichiarate nel risultato con stato
"NON IMPLEMENTATO": il risultato globale non e' mai "VERIFICATO" finche'
mancano componenti.

Convenzioni: mm, N, MPa. M > 0 = trazione nella parte alta della trave.
N > 0 = trazione. V = taglio nella trave.
"""
import math

from .data import (BOLT_GRADES, BOLTS, E_STEEL, PARTIAL_FACTORS, SECTIONS,
                   STEELS)

MISSING_COMPONENTS = [
    ("Piastra di testa in flessione (T-stub)", "EN 1993-1-8, 6.2.6.5"),
    ("Ala della colonna in flessione (T-stub)", "EN 1993-1-8, 6.2.6.4"),
    ("Anima della colonna in trazione", "EN 1993-1-8, 6.2.6.3"),
    ("Resistenza a flessione Mj,Rd e rigidezza Sj,ini", "EN 1993-1-8, 6.3"),
]


def normalize_profile(name):
    """'ipe300', 'IPE  300' -> 'IPE 300'."""
    s = "".join(str(name).upper().split())
    i = next((k for k, ch in enumerate(s) if ch.isdigit()), len(s))
    return f"{s[:i]} {s[i:]}".strip()


def _section(name):
    key = normalize_profile(name)
    if key not in SECTIONS:
        raise ValueError(
            f"Profilo '{name}' non presente nel database. Disponibili: "
            + ", ".join(sorted(SECTIONS)))
    return SECTIONS[key]


def _lookup(table, key, label):
    if key not in table:
        raise ValueError(f"{label} '{key}' non previsto. Disponibili: "
                         + ", ".join(table))
    return table[key]


def _comp(name, ref, ed, rd, unit, formula, note=""):
    ratio = ed / rd if rd > 0 else float("inf")
    return {
        "name": name, "ref": ref, "ed": ed, "rd": rd, "unit": unit,
        "ratio": ratio, "status": "OK" if ratio <= 1.0 else "NON VERIFICATO",
        "formula": formula, "note": note,
    }


def _bearing_rd(fu, fub, d, d0, t, e1_alpha, p1, p2, e2, gamma_m2, n_rows):
    """Resistenza a rifollamento Fb,Rd = k1 ab fu d t / gM2 (3.6.1), versione
    conservativa: per tutti i bulloni si assume il valore piu' sfavorevole."""
    alpha_d = e1_alpha / (3.0 * d0)
    if n_rows > 1:
        alpha_d = min(alpha_d, p1 / (3.0 * d0) - 0.25)
    alpha_b = min(alpha_d, fub / fu, 1.0)
    k1 = min(2.8 * e2 / d0 - 1.7, 1.4 * p2 / d0 - 1.7, 2.5)
    return k1 * alpha_b * fu * d * t / gamma_m2, alpha_b, k1


def check_endplate_joint(inp):
    warnings, assumptions = [], []

    # ---- input -----------------------------------------------------------
    beam = _section(inp["beam"])
    col = _section(inp["column"])
    steel = _lookup(STEELS, inp["steel"], "Acciaio")
    fy, fu, betaw = steel["fy"], steel["fu"], steel["betaw"]
    g0, g1, g2 = _lookup(PARTIAL_FACTORS, inp.get("code", "NTC"), "Normativa")

    pl = inp["plate"]
    tp, bp, hp = pl["t"], pl["width"], pl["height"]
    a_w = pl["weld_throat"]
    y_first = pl.get("y_first", 30.0)

    bo = inp["bolts"]
    bolt = _lookup(BOLTS, bo["diameter"], "Bullone")
    grade = _lookup(BOLT_GRADES, bo["grade"], "Classe bulloni")
    n_rows = int(bo["rows"])
    p1, p2 = bo["p1"], bo["p2"]
    n_per_row = int(bo.get("per_row", 2))

    N = inp["loads"].get("N", 0.0) * 1e3
    V = abs(inp["loads"]["V"]) * 1e3
    M = inp["loads"]["M"] * 1e6
    if M <= 0:
        raise ValueError("Versione 0.1: M deve essere > 0 (trazione in alto).")
    sigma_com_col = inp.get("column_axial_stress", 0.0)

    d, d0, As = bolt["d"], bolt["d0"], bolt["As"]
    fub = grade["fub"]

    # ---- geometria -------------------------------------------------------
    hb, tfb, bb = beam["h"], beam["tf"], beam["b"]
    ext = (hp - hb) / 2.0
    assumptions.append(
        f"Piastra centrata sulla trave: sporgenza {ext:.0f} mm sopra e sotto.")
    assumptions.append(
        f"Prima fila di bulloni a {y_first:.0f} mm dal bordo superiore della "
        "piastra (dato non presente nella GUI); file a passo costante.")
    ys = [y_first + i * p1 for i in range(n_rows)]
    yc = hp - ext - tfb / 2.0          # centro di compressione (ala inferiore)
    y_mid = hp / 2.0                   # asse della trave
    hi = [yc - y for y in ys]
    if any(h <= 0 for h in hi):
        raise ValueError("Una fila di bulloni cade sotto il centro di compressione.")
    z = hb - tfb
    e2 = (bp - p2) / 2.0

    if y_first < 1.2 * d0:
        warnings.append("Distanza dal bordo e1 < 1,2 d0 (EN 1993-1-8, Tab. 3.3).")
    if n_rows > 1 and p1 < 2.2 * d0:
        warnings.append("Passo verticale p1 < 2,2 d0.")
    if p2 < 2.4 * d0:
        warnings.append("Interasse orizzontale p2 < 2,4 d0.")
    if e2 < 1.2 * d0:
        warnings.append("Distanza laterale e2 < 1,2 d0.")
    if max(tp, beam["tf"], col["tf"]) > 40:
        warnings.append("Spessori > 40 mm: fy e fu vanno ridotti.")

    # ---- forze nelle file di bulloni (distribuzione triangolare) --------
    e_c = yc - y_mid
    sum_h2 = sum(h * h for h in hi)
    k = (M + N * e_c) / sum_h2
    t_rows = [k * h for h in hi]            # trazione per fila [N]
    c_force = sum(t_rows) - N               # compressione [N]
    ft_ed = max(t_rows) / n_per_row         # trazione massima per bullone
    n_bolts = n_rows * n_per_row
    fv_ed = V / n_bolts

    comps = []

    # ---- bulloni ---------------------------------------------------------
    ft_rd = 0.9 * fub * As / g2
    alpha_v = 0.5 if bo["grade"] in ("4.8", "5.8", "6.8", "10.9") else 0.6
    fv_rd = alpha_v * fub * As / g2
    comps.append(_comp("Bullone: trazione", "EN 1993-1-8, Tab. 3.4",
                       ft_ed, ft_rd, "N", "Ft,Rd = 0,9 fub As / gM2",
                       "Effetto leva non incluso (sara' nel T-stub)."))
    comps.append(_comp("Bullone: taglio", "EN 1993-1-8, Tab. 3.4",
                       fv_ed, fv_rd, "N", f"Fv,Rd = {alpha_v} fub As / gM2",
                       "Taglio ripartito in parti uguali; filetto nel piano di taglio."))
    inter = fv_ed / fv_rd + ft_ed / (1.4 * ft_rd)
    comps.append(_comp("Bullone: taglio + trazione", "EN 1993-1-8, Tab. 3.4",
                       inter, 1.0, "-", "Fv,Ed/Fv,Rd + Ft,Ed/(1,4 Ft,Rd) <= 1"))

    fb_pl, ab_pl, k1_pl = _bearing_rd(fu, fub, d, d0, tp, y_first, p1, p2, e2, g2, n_rows)
    comps.append(_comp("Rifollamento sulla piastra", "EN 1993-1-8, Tab. 3.4",
                       fv_ed, fb_pl, "N", "Fb,Rd = k1 ab fu d t / gM2",
                       f"ab={ab_pl:.3f}, k1={k1_pl:.2f}; valore conservativo per tutti i bulloni."))
    e2c = (col["b"] - p2) / 2.0
    fb_col, ab_c, k1_c = _bearing_rd(fu, fub, d, d0, col["tf"], 1e9, p1, p2, e2c, g2, n_rows)
    comps.append(_comp("Rifollamento sull'ala della colonna", "EN 1993-1-8, Tab. 3.4",
                       fv_ed, fb_col, "N", "Fb,Rd = k1 ab fu d t / gM2",
                       f"ab={ab_c:.3f}, k1={k1_c:.2f}."))

    dm = 0.5 * (bolt["s"] + bolt["s"] / math.cos(math.radians(30)))
    t_min = min(tp, col["tf"])
    bp_rd = 0.6 * math.pi * dm * t_min * fu / g2
    comps.append(_comp("Punzonamento", "EN 1993-1-8, Tab. 3.4",
                       ft_ed, bp_rd, "N", "Bp,Rd = 0,6 pi dm tp fu / gM2",
                       f"dm={dm:.1f} mm, t={t_min:.1f} mm."))

    # ---- saldature trave-piastra (metodo semplificato 4.5.3.3) ----------
    fw_rd = fu / (math.sqrt(3.0) * betaw * g2)          # MPa
    lw_flange = 2.0 * beam["b"] - beam["tw"] - 2.0 * beam["r"]
    sum_t = sum(t_rows)
    f_flange = max(sum_t, c_force)
    comps.append(_comp("Saldatura ala trave-piastra", "EN 1993-1-8, 4.5.3.3",
                       f_flange, fw_rd * a_w * lw_flange, "N",
                       "Fw,Rd = fu/(sqrt3 bw gM2) a Lw",
                       f"Lw={lw_flange:.0f} mm (una faccia esterna + due interne); "
                       "forza = risultante delle file tese (prudente)."))
    lw_web = 2.0 * (hb - 2.0 * beam["tf"] - 2.0 * beam["r"])
    comps.append(_comp("Saldatura anima trave-piastra (taglio)", "EN 1993-1-8, 4.5.3.3",
                       V, fw_rd * a_w * lw_web, "N",
                       "Fw,Rd = fu/(sqrt3 bw gM2) a Lw",
                       f"Lw={lw_web:.0f} mm (due lati); stessa gola dell'ala."))

    # ---- componenti trave -----------------------------------------------
    mc_rd = beam["Wpl"] * fy / g0
    fc_fb_rd = mc_rd / z
    comps.append(_comp("Ala e anima della trave compresse", "EN 1993-1-8, 6.2.6.7",
                       c_force, fc_fb_rd, "N", "Fc,fb,Rd = Mc,Rd / (h - tf)",
                       "Assume sezione di classe 1-2 e Mc,Rd = Wpl fy / gM0."))

    # ---- componenti colonna ---------------------------------------------
    avc = col["A"] - 2.0 * col["b"] * col["tf"] + (col["tw"] + 2.0 * col["r"]) * col["tf"]
    hw_c = col["h"] - 2.0 * col["tf"]
    avc = max(avc, 1.2 * hw_c * col["tw"])
    vwp_rd = 0.9 * fy * avc / (math.sqrt(3.0) * g0)
    vwp_ed = sum_t
    comps.append(_comp("Pannello d'anima della colonna a taglio", "EN 1993-1-8, 6.2.6.1",
                       vwp_ed, vwp_rd, "N", "Vwp,Rd = 0,9 fy Avc / (sqrt3 gM0)",
                       "Giunto a un solo lato (beta=1); Vwp,Ed = risultante delle file tese; "
                       "taglio di colonna assunto nullo (a favore di sicurezza)."))

    beff = (beam["tf"] + 2.0 * math.sqrt(2.0) * a_w + 5.0 * (col["tf"] + col["r"]) + tp)
    omega = 1.0 / math.sqrt(1.0 + 1.3 * (beff * col["tw"] / avc) ** 2)
    dwc = col["h"] - 2.0 * (col["tf"] + col["r"])
    lam_p = 0.932 * math.sqrt(beff * dwc * fy / (E_STEEL * col["tw"] ** 2))
    rho = 1.0 if lam_p <= 0.72 else (lam_p - 0.2) / lam_p ** 2
    kwc = 1.0 if sigma_com_col <= 0.7 * fy else min(1.0, 1.7 - sigma_com_col / fy)
    fc_wc_rd = min(omega * kwc * beff * col["tw"] * fy / g0,
                   omega * kwc * rho * beff * col["tw"] * fy / g1)
    comps.append(_comp("Anima della colonna in compressione trasversale", "EN 1993-1-8, 6.2.6.2",
                       c_force, fc_wc_rd, "N",
                       "Fc,wc,Rd = w kwc rho beff tw fy / gM1",
                       f"beff={beff:.1f} mm, w={omega:.3f}, rho={rho:.3f}, kwc={kwc:.2f}; "
                       "sp = tp (valore prudente); giunto a un solo lato."))

    # ---- esito globale ---------------------------------------------------
    failed = [c["name"] for c in comps if c["status"] != "OK"]
    if failed:
        overall = "NON VERIFICATO"
    else:
        overall = "INCOMPLETO"   # componenti mancanti: mai "VERIFICATO" in v0.1

    return {
        "engine": "ec3-components v0.1",
        "overall": overall,
        "failed": failed,
        "components": comps,
        "not_implemented": [{"name": n, "ref": r, "status": "NON IMPLEMENTATO"}
                            for n, r in MISSING_COMPONENTS],
        "intermediate": {
            "row_positions_from_top_mm": ys,
            "lever_arms_mm": hi,
            "row_tension_N": t_rows,
            "compression_force_N": c_force,
            "bolt_tension_max_N": ft_ed,
            "bolt_shear_N": fv_ed,
        },
        "assumptions": assumptions,
        "warnings": warnings,
    }
