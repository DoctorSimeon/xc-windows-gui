# XC Connections GUI (prototipo)

Interfaccia grafica per Windows costruita sopra [XC](https://github.com/xcfem/xc)
(solver agli elementi finiti open source, GPL-3.0). Questo progetto e' distribuito
sotto la stessa licenza, **GPL-3.0**.

## Stato

| Parte | Stato |
|---|---|
| GUI (scheda dati nodo trave-colonna con piastra di testa, salva/apri progetto, esecuzione) | Funziona; provata solo in modalita' headless su Linux |
| Esecuzione di XC (Locale / WSL / Docker) | Implementata, **non provata con XC reale** |
| Modello CBFEM del collegamento | **Non implementato**: `templates/endplate_joint.py.tpl` e' uno scheletro |
| Eseguibile Windows (`XCConnections.exe`) | Prodotto da GitHub Actions; **non provato su Windows** |
| Compilazione nativa di XC su Windows | Sperimentale, probabilmente da correggere |

La GUI da sola non esegue nessuna verifica: serve XC. Oggi la strada piu' semplice
per averlo su Windows e' WSL2 o Docker.

## Come ottenere l'.exe

1. Crea un repository su GitHub e carica il contenuto di questa cartella
   (comprese le cartelle `.github` e `xc_gui`).
2. Vai su **Actions → Build Windows → Run workflow**.
3. A fine esecuzione scarica l'artefatto **XCConnections-gui**: dentro c'e' `XCConnections.exe`.
4. Per provare anche la compilazione nativa di XC, spunta
   *"Prova anche la compilazione nativa di XC"* prima di avviare. Il job e'
   sperimentale: se fallisce, scarica `xc-native-logs` e usa gli errori per correggere
   l'elenco dei pacchetti in `build-windows.yml`.

## Eseguire la GUI senza .exe

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python xc_gui\app.py
```

## Far girare XC

Nella GUI scegli la modalita' di esecuzione:

- **Locale**: un Python con il modulo `xc` installato (campo "Comando Python").
- **WSL**: usa `wsl.exe python3 -`. XC deve essere installato dentro la distribuzione WSL.
- **Docker**: usa `docker run --rm -i <immagine> python3 -`. Le istruzioni per
  l'immagine sono nel repository di XC (`install/docker_install.md`).
  Controlla il nome dell'immagine e correggilo nel campo apposito.

Lo script viene passato allo stdin del processo, quindi non servono percorsi condivisi.

## Prossimi passi

1. Provare XC in Docker/WSL2 con gli esempi di `xcfem/xc_examples`.
2. Studiare gli esempi CBFEM di `xcfem/xc` (cartella `verif`) e scrivere il modello vero
   nel template.
3. Validare i risultati contro esempi di riferimento (ad esempio i casi del libro
   *Component-based finite element design of steel connections*) prima di usarli.
4. Aggiungere altre tipologie di nodo e la relazione di calcolo.
