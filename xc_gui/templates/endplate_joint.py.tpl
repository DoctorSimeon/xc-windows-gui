# -*- coding: utf-8 -*-
# Script generato da XC Connections GUI.
#
# ATTENZIONE: questo e' uno SCHELETRO. Legge i dati del nodo, verifica che XC
# sia importabile e stampa un riepilogo. Il modello CBFEM del collegamento
# (geometria, mesh, vincoli, carichi, verifiche) va ancora implementato
# usando come riferimento gli esempi di XC (https://github.com/xcfem/xc_examples
# e la cartella "verif" del repository xcfem/xc).
import json
import sys

INPUT = json.loads(r'''
$INPUT_JSON
''')

print("XC Connections GUI - dati di ingresso")
for key, value in INPUT.items():
    print(f"  {key}: {value}")
print()

try:
    import xc  # noqa: F401
except ImportError as exc:
    print("ERRORE: il modulo 'xc' non e' importabile in questo ambiente.")
    print(f"Dettaglio: {exc}")
    sys.exit(2)

print("Modulo xc importato correttamente.")

# --- TODO: modello CBFEM ---------------------------------------------------
# 1. creare il FEProblem e il preprocessore
# 2. modellare trave, colonna, piastra di testa (shell), bulloni e saldature
# 3. applicare N, V, M all'estremita' della trave
# 4. risolvere e leggere tensioni, plasticizzazioni, forze nei bulloni
# 5. calcolare i coefficienti di utilizzo secondo EN 1993-1-8
# ---------------------------------------------------------------------------
print("Modello CBFEM non ancora implementato: nessuna verifica eseguita.")
sys.exit(0)
