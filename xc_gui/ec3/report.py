"""Report testuale (Markdown) dei risultati del motore."""


def _fmt(value, unit):
    if unit == "N":
        return f"{value / 1e3:,.1f} kN"
    return f"{value:,.3f}"


def render_report(inp, res):
    lines = []
    lines.append(f"# Verifica giunto trave-colonna con piastra di testa")
    lines.append("")
    lines.append(f"Motore: {res['engine']}  |  Esito: **{res['overall']}**")
    lines.append("")
    lines.append(f"Trave {inp['beam']}, colonna {inp['column']}, acciaio {inp['steel']}, "
                 f"normativa coefficienti: {inp.get('code', 'NTC')}")
    lo = inp["loads"]
    lines.append(f"Sollecitazioni: N = {lo.get('N', 0)} kN, V = {lo['V']} kN, M = {lo['M']} kNm")
    lines.append("")
    lines.append("| Componente | Ed | Rd | Ed/Rd | Esito | Riferimento |")
    lines.append("|---|---|---|---|---|---|")
    for c in res["components"]:
        lines.append(f"| {c['name']} | {_fmt(c['ed'], c['unit'])} | {_fmt(c['rd'], c['unit'])} "
                     f"| {c['ratio']:.2f} | {c['status']} | {c['ref']} |")
    for c in res["not_implemented"]:
        lines.append(f"| {c['name']} | - | - | - | {c['status']} | {c['ref']} |")
    lines.append("")
    lines.append("## Formule e note")
    for c in res["components"]:
        note = f" {c['note']}" if c["note"] else ""
        lines.append(f"- {c['name']}: {c['formula']}.{note}")
    lines.append("")
    lines.append("## Ipotesi")
    for a in res["assumptions"]:
        lines.append(f"- {a}")
    if res["warnings"]:
        lines.append("")
        lines.append("## Avvisi")
        for w in res["warnings"]:
            lines.append(f"- {w}")
    lines.append("")
    lines.append("Il risultato \"INCOMPLETO\" indica che le componenti non implementate "
                 "non sono state verificate: non equivale a una verifica superata. "
                 "Le verifiche vanno controllate da un tecnico abilitato.")
    return "\n".join(lines)
