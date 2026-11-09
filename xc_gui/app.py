"""XC Connections GUI - prototipo.

Interfaccia grafica (PySide6) che raccoglie i dati di un nodo trave-colonna con
piastra di testa, genera uno script Python per XC (https://github.com/xcfem/xc)
e lo esegue tramite un "backend" configurabile:

  - Interno (EC3): motore analitico incluso nell'eseguibile (metodo delle
                   componenti EN 1993-1-8); non richiede Python, WSL o Docker
  - Locale : un interprete Python con XC installato (python -)
  - WSL    : wsl.exe python3 -   (XC installato dentro WSL2)
  - Docker : docker run --rm -i <immagine> python3 -

Lo script viene passato allo stdin del processo, cosi' non servono conversioni
di percorso fra Windows e Linux.

NOTA: il template dello script (templates/endplate_joint.py.tpl) e' uno
scheletro. Il modello CBFEM vero va scritto sulla base degli esempi di XC.
"""
from __future__ import annotations

import json
import shlex
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from string import Template

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


try:  # eseguito come pacchetto (python -m xc_gui.app)
    from xc_gui.ec3 import render_report, run as run_ec3
except ImportError:  # eseguito come script o da eseguibile PyInstaller
    from ec3 import render_report, run as run_ec3

INTERNAL_BACKEND = "Interno (EC3)"


def decode_output(raw: bytes) -> str:
    """Decodifica l'output di un processo: UTF-8, altrimenti la codifica della console."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    for enc in (("oem", "mbcs") if sys.platform == "win32" else ()):
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("latin-1", errors="replace")


def resource_path(relative: str) -> Path:
    """Percorso di una risorsa, anche dentro un eseguibile PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


STEEL_GRADES = ["S235", "S275", "S355", "S460"]
BOLT_CLASSES = ["4.6", "5.6", "8.8", "10.9"]
BOLT_DIAMETERS = [12, 16, 20, 24, 27, 30]


@dataclass
class JointInput:
    """Dati di ingresso del nodo (unita': mm, MPa, kN, kNm)."""

    beam_profile: str = "IPE 300"
    column_profile: str = "HEA 240"
    steel_grade: str = "S355"
    plate_thickness: float = 20.0
    plate_width: float = 200.0
    plate_height: float = 400.0
    bolt_diameter: int = 20
    bolt_class: str = "8.8"
    bolt_rows: int = 3
    bolt_gauge: float = 100.0
    bolt_pitch: float = 80.0
    weld_throat: float = 6.0
    plate_y_first: float = 30.0  # distanza 1a fila dal bordo superiore piastra [mm]
    axial_force: float = 0.0   # N  [kN], trazione positiva
    shear_force: float = 80.0  # V  [kN]
    bending_moment: float = 120.0  # M  [kNm]
    # backend
    backend: str = INTERNAL_BACKEND
    python_cmd: str = "python"
    docker_image: str = "xcfem/xc"
    extra: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = []
        if self.plate_thickness <= 0:
            errors.append("Lo spessore della piastra deve essere positivo.")
        if self.bolt_rows < 1:
            errors.append("Serve almeno una fila di bulloni.")
        if self.plate_width < 2 * 1.2 * self.bolt_diameter:
            errors.append("Piastra troppo stretta per il diametro dei bulloni.")
        needed = (self.bolt_rows - 1) * self.bolt_pitch + 2 * 1.2 * self.bolt_diameter
        if self.plate_height < needed:
            errors.append(
                f"Piastra troppo bassa: servono almeno {needed:.0f} mm per le file indicate."
            )
        if self.bolt_gauge + 2 * 1.2 * self.bolt_diameter > self.plate_width:
            errors.append("L'interasse orizzontale dei bulloni non entra nella piastra.")
        last_row = self.plate_y_first + (self.bolt_rows - 1) * self.bolt_pitch
        if last_row + 1.2 * self.bolt_diameter > self.plate_height:
            errors.append("Le file di bulloni, a partire dalla distanza indicata dal "
                          "bordo superiore, non entrano nell'altezza della piastra.")
        return errors

    def to_engine_input(self) -> dict:
        """Dati nel formato del motore interno EC3."""
        return {
            "beam": self.beam_profile,
            "column": self.column_profile,
            "steel": self.steel_grade,
            "code": "NTC",
            "plate": {
                "t": self.plate_thickness,
                "width": self.plate_width,
                "height": self.plate_height,
                "weld_throat": self.weld_throat,
                "y_first": self.plate_y_first,
            },
            "bolts": {
                "diameter": f"M{self.bolt_diameter}",
                "grade": self.bolt_class,
                "rows": self.bolt_rows,
                "p1": self.bolt_pitch,
                "p2": self.bolt_gauge,
                "per_row": 2,
            },
            "loads": {
                "N": self.axial_force,
                "V": self.shear_force,
                "M": self.bending_moment,
            },
        }


def render_script(data: JointInput) -> str:
    """Genera lo script XC a partire dal template."""
    template = Template(
        resource_path("templates/endplate_joint.py.tpl").read_text(encoding="utf-8")
    )
    payload = {k: v for k, v in asdict(data).items() if k != "extra"}
    return template.substitute(INPUT_JSON=json.dumps(payload, indent=2))


def build_command(data: JointInput) -> tuple[str, list[str]]:
    """Programma e argomenti per eseguire lo script via stdin."""
    if data.backend == "WSL":
        return "wsl.exe", ["python3", "-"]
    if data.backend == "Docker":
        return "docker", ["run", "--rm", "-i", data.docker_image, "python3", "-"]
    parts = shlex.split(data.python_cmd, posix=(sys.platform != "win32"))
    return parts[0], parts[1:] + ["-"]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XC Connections - nodo trave-colonna con piastra di testa")
        self.resize(1200, 760)
        self.process: QProcess | None = None
        self._pending_script = ""

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_input_panel())
        splitter.addWidget(self._build_output_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Pronto")

    # ---------- pannello dati ----------
    def _spin(self, value, lo, hi, step=1.0, decimals=1, suffix="") -> QDoubleSpinBox:
        w = QDoubleSpinBox()
        w.setRange(lo, hi)
        w.setDecimals(decimals)
        w.setSingleStep(step)
        w.setValue(value)
        if suffix:
            w.setSuffix(f" {suffix}")
        return w

    def _build_input_panel(self) -> QWidget:
        d = JointInput()
        panel = QWidget()
        layout = QVBoxLayout(panel)

        g_members = QGroupBox("Membrature")
        f = QFormLayout(g_members)
        self.beam = QLineEdit(d.beam_profile)
        self.column = QLineEdit(d.column_profile)
        self.grade = QComboBox()
        self.grade.addItems(STEEL_GRADES)
        self.grade.setCurrentText(d.steel_grade)
        f.addRow("Trave", self.beam)
        f.addRow("Colonna", self.column)
        f.addRow("Acciaio", self.grade)
        layout.addWidget(g_members)

        g_plate = QGroupBox("Piastra di testa")
        f = QFormLayout(g_plate)
        self.pl_t = self._spin(d.plate_thickness, 5, 60, 1, 1, "mm")
        self.pl_b = self._spin(d.plate_width, 80, 600, 5, 0, "mm")
        self.pl_h = self._spin(d.plate_height, 100, 1200, 5, 0, "mm")
        self.weld = self._spin(d.weld_throat, 3, 20, 0.5, 1, "mm")
        f.addRow("Spessore", self.pl_t)
        f.addRow("Larghezza", self.pl_b)
        f.addRow("Altezza", self.pl_h)
        f.addRow("Gola saldature", self.weld)
        layout.addWidget(g_plate)

        g_bolts = QGroupBox("Bulloni")
        f = QFormLayout(g_bolts)
        self.bd = QComboBox()
        self.bd.addItems([f"M{x}" for x in BOLT_DIAMETERS])
        self.bd.setCurrentText(f"M{d.bolt_diameter}")
        self.bc = QComboBox()
        self.bc.addItems(BOLT_CLASSES)
        self.bc.setCurrentText(d.bolt_class)
        self.rows = QSpinBox()
        self.rows.setRange(1, 8)
        self.rows.setValue(d.bolt_rows)
        self.gauge = self._spin(d.bolt_gauge, 40, 400, 5, 0, "mm")
        self.pitch = self._spin(d.bolt_pitch, 40, 300, 5, 0, "mm")
        self.y_first = self._spin(d.plate_y_first, 10, 600, 5, 0, "mm")
        f.addRow("Diametro", self.bd)
        f.addRow("Classe", self.bc)
        f.addRow("File", self.rows)
        f.addRow("Interasse orizzontale", self.gauge)
        f.addRow("Passo verticale", self.pitch)
        f.addRow("1a fila dal bordo sup.", self.y_first)
        layout.addWidget(g_bolts)

        g_loads = QGroupBox("Sollecitazioni di progetto")
        f = QFormLayout(g_loads)
        self.n = self._spin(d.axial_force, -5000, 5000, 5, 1, "kN")
        self.v = self._spin(d.shear_force, -5000, 5000, 5, 1, "kN")
        self.m = self._spin(d.bending_moment, -5000, 5000, 5, 1, "kNm")
        f.addRow("N (trazione +)", self.n)
        f.addRow("V", self.v)
        f.addRow("M", self.m)
        layout.addWidget(g_loads)

        g_backend = QGroupBox("Motore di calcolo")
        f = QFormLayout(g_backend)
        self.backend = QComboBox()
        self.backend.addItems([INTERNAL_BACKEND, "Locale", "WSL", "Docker"])
        self.backend.setCurrentText(d.backend)
        self.pycmd = QLineEdit(d.python_cmd)
        self.image = QLineEdit(d.docker_image)
        f.addRow("Modalita'", self.backend)
        f.addRow("Comando Python (Locale)", self.pycmd)
        f.addRow("Immagine Docker", self.image)
        self.backend.currentTextChanged.connect(self._backend_changed)
        self._backend_changed(self.backend.currentText())
        layout.addWidget(g_backend)

        row = QHBoxLayout()
        b_open = QPushButton("Apri progetto...")
        b_save = QPushButton("Salva progetto...")
        b_open.clicked.connect(self.open_project)
        b_save.clicked.connect(self.save_project)
        row.addWidget(b_open)
        row.addWidget(b_save)
        layout.addLayout(row)
        layout.addStretch(1)
        panel.setMinimumWidth(380)
        return panel

    # ---------- pannello output ----------
    def _build_output_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        buttons = QHBoxLayout()
        self.btn_preview = QPushButton("Genera script")
        self.btn_run = QPushButton("Esegui")
        self.btn_run.setToolTip(
            "Esegue la verifica con il motore selezionato (Interno EC3, oppure XC)")
        self.btn_stop = QPushButton("Interrompi")
        self.btn_stop.setEnabled(False)
        self.btn_preview.clicked.connect(self.preview_script)
        self.btn_run.clicked.connect(self.run_script)
        self.btn_stop.clicked.connect(self.stop_script)
        for b in (self.btn_preview, self.btn_run, self.btn_stop):
            buttons.addWidget(b)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.script_view = QPlainTextEdit()
        self.script_view.setFont(mono)
        self.log_view = QPlainTextEdit()
        self.log_view.setFont(mono)
        self.log_view.setReadOnly(True)
        tabs = QTabWidget()
        tabs.addTab(self.script_view, "Script XC")
        tabs.addTab(self.log_view, "Risultati / log")
        self.tabs = tabs
        layout.addWidget(tabs)
        return panel

    # ---------- dati <-> widget ----------
    def collect(self) -> JointInput:
        return JointInput(
            beam_profile=self.beam.text().strip(),
            column_profile=self.column.text().strip(),
            steel_grade=self.grade.currentText(),
            plate_thickness=self.pl_t.value(),
            plate_width=self.pl_b.value(),
            plate_height=self.pl_h.value(),
            bolt_diameter=int(self.bd.currentText()[1:]),
            bolt_class=self.bc.currentText(),
            bolt_rows=self.rows.value(),
            bolt_gauge=self.gauge.value(),
            bolt_pitch=self.pitch.value(),
            weld_throat=self.weld.value(),
            plate_y_first=self.y_first.value(),
            axial_force=self.n.value(),
            shear_force=self.v.value(),
            bending_moment=self.m.value(),
            backend=self.backend.currentText(),
            python_cmd=self.pycmd.text().strip() or "python",
            docker_image=self.image.text().strip() or "xcfem/xc",
        )

    def apply(self, d: JointInput) -> None:
        self.beam.setText(d.beam_profile)
        self.column.setText(d.column_profile)
        self.grade.setCurrentText(d.steel_grade)
        self.pl_t.setValue(d.plate_thickness)
        self.pl_b.setValue(d.plate_width)
        self.pl_h.setValue(d.plate_height)
        self.bd.setCurrentText(f"M{d.bolt_diameter}")
        self.bc.setCurrentText(d.bolt_class)
        self.rows.setValue(d.bolt_rows)
        self.gauge.setValue(d.bolt_gauge)
        self.pitch.setValue(d.bolt_pitch)
        self.weld.setValue(d.weld_throat)
        self.y_first.setValue(d.plate_y_first)
        self.n.setValue(d.axial_force)
        self.v.setValue(d.shear_force)
        self.m.setValue(d.bending_moment)
        self.backend.setCurrentText(d.backend)
        self.pycmd.setText(d.python_cmd)
        self.image.setText(d.docker_image)

    # ---------- azioni ----------
    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva progetto", "nodo.xcjoint.json", "Progetto (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(asdict(self.collect()), indent=2), encoding="utf-8"
            )
            self.statusBar().showMessage(f"Salvato {path}")

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Apri progetto", "", "Progetto (*.json)"
        )
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            known = JointInput.__dataclass_fields__.keys()
            self.apply(JointInput(**{k: v for k, v in raw.items() if k in known}))
            self.statusBar().showMessage(f"Aperto {path}")
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, "Errore", f"File non valido:\n{exc}")

    def _backend_changed(self, name: str) -> None:
        self.pycmd.setEnabled(name == "Locale")
        self.image.setEnabled(name == "Docker")

    def _run_internal(self) -> None:
        """Verifica con il motore EC3 incluso: nessun processo esterno."""
        data = self.collect()
        errors = data.validate()
        if errors:
            QMessageBox.warning(self, "Dati non validi", "\n".join(errors))
            return
        inp = data.to_engine_input()
        try:
            result = run_ec3(inp, "ec3")
        except (ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Verifica non eseguibile", str(exc))
            return
        self.log_view.setPlainText(render_report(inp, result))
        self.tabs.setCurrentIndex(1)
        self.statusBar().showMessage(f"Esito: {result['overall']}")

    def _checked_script(self) -> str | None:
        data = self.collect()
        errors = data.validate()
        if errors:
            QMessageBox.warning(self, "Dati non validi", "\n".join(errors))
            return None
        return render_script(data)

    def preview_script(self) -> None:
        script = self._checked_script()
        if script is not None:
            self.script_view.setPlainText(script)
            self.tabs.setCurrentIndex(0)

    def run_script(self) -> None:
        if self.process is not None:
            return
        if self.backend.currentText() == INTERNAL_BACKEND:
            self._run_internal()
            return
        script = self._checked_script()
        if script is None:
            return
        self.script_view.setPlainText(script)
        program, args = build_command(self.collect())
        self.log_view.clear()
        self.log_view.appendPlainText(f"$ {program} {' '.join(args)}\n")
        self.tabs.setCurrentIndex(1)

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._read_output)
        proc.finished.connect(self._finished)
        proc.errorOccurred.connect(self._error)
        proc.started.connect(self._send_script)
        self._pending_script = script
        self.process = proc
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.statusBar().showMessage("In esecuzione...")
        proc.start(program, args)

    def _send_script(self) -> None:
        if self.process is not None:
            self.process.write(self._pending_script.encode("utf-8"))
            self.process.closeWriteChannel()

    def _read_output(self) -> None:
        if self.process is not None:
            text = decode_output(bytes(self.process.readAllStandardOutput()))
            self.log_view.appendPlainText(text.rstrip("\n"))

    def _finished(self, code: int, _status) -> None:
        self.log_view.appendPlainText(f"\n[terminato con codice {code}]")
        self._cleanup("Completato" if code == 0 else f"Errore (codice {code})")

    def _error(self, err) -> None:
        if err == QProcess.FailedToStart:
            self.log_view.appendPlainText(
                "Impossibile avviare il programma. Controlla la modalita' di "
                "esecuzione e che Python/WSL/Docker siano installati."
            )
            self._cleanup("Avvio fallito")

    def stop_script(self) -> None:
        if self.process is not None:
            self.process.kill()

    def _cleanup(self, message: str) -> None:
        if self.process is not None:
            self.process.deleteLater()
        self.process = None
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.statusBar().showMessage(message)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
