"""Dati di base: acciai, classi dei bulloni, bulloni, profili.

ATTENZIONE: i valori dei profili sono inseriti a mano e vanno verificati sui
profilati ufficiali prima di qualsiasi uso professionale.
Unita': mm, N, MPa.
"""

# Acciai da carpenteria (t <= 40 mm): fy, fu [MPa], betaw (EN 1993-1-8 Tab. 4.1)
STEELS = {
    "S235": {"fy": 235.0, "fu": 360.0, "betaw": 0.80},
    "S275": {"fy": 275.0, "fu": 430.0, "betaw": 0.85},
    "S355": {"fy": 355.0, "fu": 490.0, "betaw": 0.90},
    "S460": {"fy": 460.0, "fu": 540.0, "betaw": 1.00},
}

# Classi dei bulloni: fyb, fub [MPa]
BOLT_GRADES = {
    "4.6": {"fyb": 240.0, "fub": 400.0},
    "5.6": {"fyb": 300.0, "fub": 500.0},
    "6.8": {"fyb": 480.0, "fub": 600.0},
    "8.8": {"fyb": 640.0, "fub": 800.0},
    "10.9": {"fyb": 900.0, "fub": 1000.0},
}

# Bulloni: As = area resistente [mm2], d0 = diametro del foro [mm],
# s = apertura chiave [mm] (usata per il diametro medio della testa dm)
BOLTS = {
    "M12": {"d": 12.0, "As": 84.3, "d0": 13.0, "s": 18.0},
    "M16": {"d": 16.0, "As": 157.0, "d0": 18.0, "s": 24.0},
    "M20": {"d": 20.0, "As": 245.0, "d0": 22.0, "s": 30.0},
    "M22": {"d": 22.0, "As": 303.0, "d0": 24.0, "s": 34.0},
    "M24": {"d": 24.0, "As": 353.0, "d0": 26.0, "s": 36.0},
    "M27": {"d": 27.0, "As": 459.0, "d0": 30.0, "s": 41.0},
    "M30": {"d": 30.0, "As": 561.0, "d0": 33.0, "s": 46.0},
}

# Profili laminati: h, b, tw, tf, r [mm], A [mm2], Wpl,y [mm3]
SECTIONS = {
    "IPE 200": {"h": 200.0, "b": 100.0, "tw": 5.6, "tf": 8.5, "r": 12.0, "A": 2848.0, "Wpl": 220.6e3},
    "IPE 300": {"h": 300.0, "b": 150.0, "tw": 7.1, "tf": 10.7, "r": 15.0, "A": 5381.0, "Wpl": 628.4e3},
    "IPE 400": {"h": 400.0, "b": 180.0, "tw": 8.6, "tf": 13.5, "r": 21.0, "A": 8446.0, "Wpl": 1307.0e3},
    "HEA 200": {"h": 190.0, "b": 200.0, "tw": 6.5, "tf": 10.0, "r": 18.0, "A": 5383.0, "Wpl": 429.5e3},
    "HEA 240": {"h": 230.0, "b": 240.0, "tw": 7.5, "tf": 12.0, "r": 21.0, "A": 7684.0, "Wpl": 744.6e3},
    "HEB 240": {"h": 240.0, "b": 240.0, "tw": 10.0, "tf": 17.0, "r": 21.0, "A": 10600.0, "Wpl": 1053.0e3},
}

E_STEEL = 210000.0  # MPa

# Coefficienti parziali: (gammaM0, gammaM1, gammaM2)
PARTIAL_FACTORS = {
    "NTC": (1.05, 1.05, 1.25),
    "EC3": (1.00, 1.00, 1.25),
}
