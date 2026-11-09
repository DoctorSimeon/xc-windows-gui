"""T-stub equivalente (EN 1993-1-8, 6.2.4) per una fila di bulloni.

Funzione generica, gia' testata a mano. Nella versione 0.1 NON e' ancora
collegata alle verifiche del giunto: servono le lunghezze efficaci leff delle
righe interne (Tab. 6.5/6.6, Fig. 6.11), che vanno inserite dalla norma.
"""


def tstub_resistance(leff_1, leff_2, m, e, emin, t, fy, ft_rd_bolt, n_bolts, gamma_m0):
    """Resistenza a trazione Ft,Rd del T-stub (senza piastre di contrasto).

    leff_1: lunghezza efficace per il modo 1 [mm]
    leff_2: lunghezza efficace per il modo 2 [mm]
    m, e, emin: geometria del T-stub [mm]
    t: spessore dell'ala/piastra [mm]
    fy: tensione di snervamento [MPa]
    ft_rd_bolt: resistenza a trazione di un bullone [N]
    n_bolts: numero di bulloni della fila
    Restituisce (Ft_Rd [N], modo, dettagli).
    """
    n = min(emin, 1.25 * m)
    sum_ft = n_bolts * ft_rd_bolt
    mpl_1 = 0.25 * leff_1 * t**2 * fy / gamma_m0
    mpl_2 = 0.25 * leff_2 * t**2 * fy / gamma_m0
    mode1 = 4.0 * mpl_1 / m
    mode2 = (2.0 * mpl_2 + n * sum_ft) / (m + n)
    mode3 = sum_ft
    modes = {"1": mode1, "2": mode2, "3": mode3}
    mode = min(modes, key=modes.get)
    return modes[mode], mode, {"n": n, "Mpl1": mpl_1, "Mpl2": mpl_2, "modes": modes}
