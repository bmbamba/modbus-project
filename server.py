"""
Modbus Server  ─  PySide6 + pymodbus
Per-register WARN / CRIT setpoints editable live via spinboxes.
Alarms fire on both server and client when any value exceeds its setpoint.
"""

import sys
import threading
import collections
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QFrame,
    QScrollArea, QStatusBar, QSpinBox,
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui  import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from pymodbus.server    import StartTcpServer
from pymodbus.datastore import (
    ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock,
)
import setpoints as SP
from app_icons import server_icon

HOST      = "0.0.0.0"
PORT      = 5020
NUM_REGS  = SP.NUM_REGS
CHART_LEN = 80
SYNC_MS   = 250

C = {
    "bg"      : "#0a0e17",
    "surface" : "#111827",
    "card"    : "#1a2235",
    "border"  : "#1f2d45",
    "accent"  : "#3b82f6",
    "ok"      : "#22c55e",
    "warn"    : "#f59e0b",
    "crit"    : "#ef4444",
    "text"    : "#f1f5f9",
    "muted"   : "#64748b",
    "dim"     : "#1e293b",
}

REG_HUE = [
    "#3b82f6","#14b8a6","#a78bfa","#f472b6","#fb923c",
    "#34d399","#facc15","#60a5fa","#c084fc","#f87171",
]

SPIN_STYLE = f"""
    QSpinBox {{
        background:{C['dim']}; color:{C['text']};
        border:1px solid {C['border']}; border-radius:4px;
        padding:1px 3px; font-size:11px; font-weight:600;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background:{C['card']}; border:none; width:14px;
    }}
"""


# ══════════════════════════════════════════════
#  Validated DataBlock
# ══════════════════════════════════════════════
class ValidatedDataBlock(ModbusSequentialDataBlock):
    def setValues(self, address, values):
        super().setValues(address, [max(0, min(100, int(v))) for v in values])


# ══════════════════════════════════════════════
#  Sparkline  (dashed lines track live setpoints)
# ══════════════════════════════════════════════
class Sparkline(QFrame):
    def __init__(self, reg_idx: int, color: str, parent=None):
        super().__init__(parent)
        self._idx   = reg_idx
        self._buf   = collections.deque([0]*CHART_LEN, maxlen=CHART_LEN)
        self._color = QColor(color)
        self.setFixedHeight(46)
        self.setStyleSheet(f"background:{C['bg']}; border-radius:4px;")

    def push(self, v):
        self._buf.append(v); self.update()

    def set_color(self, c):
        self._color = QColor(c); self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(C["bg"]))

        for thresh, col in (
            (SP.get_warn(self._idx), C["warn"]),
            (SP.get_crit(self._idx), C["crit"]),
        ):
            y = int(h - 2 - (thresh / 100) * (h - 4))
            p.setPen(QPen(QColor(col), 1, Qt.DashLine))
            p.drawLine(0, y, w, y)

        data = list(self._buf)
        if len(data) < 2:
            return
        step = w / (len(data) - 1)
        pts  = [(int(i*step), int(h-2-(v/100)*(h-4))) for i, v in enumerate(data)]

        fill = QColor(self._color); fill.setAlpha(25)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(fill))
        p.drawPolygon(QPolygon([QPoint(x,y) for x,y in [(0,h)]+pts+[(w,h)]]))

        p.setPen(QPen(self._color, 1.6))
        for i in range(len(pts)-1):
            p.drawLine(*pts[i], *pts[i+1])


# ══════════════════════════════════════════════
#  Register row  (slider + setpoints + spark)
# ══════════════════════════════════════════════
class RegRow(QFrame):
    sig_changed = Signal(int, int)

    def __init__(self, idx: int, parent=None):
        super().__init__(parent)
        self._idx   = idx
        self._color = REG_HUE[idx % len(REG_HUE)]
        self._alarm = "ok"
        self.setObjectName("regrow")
        self._set_border(C["border"])

        tag = QLabel(f"R{idx:02d}")
        tag.setFixedWidth(32)
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(
            f"color:{self._color}; font-weight:700; font-size:12px;"
            f"background:{C['dim']}; border-radius:4px; padding:2px 0;"
        )

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setFixedHeight(20)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height:6px; background:{C['dim']}; border-radius:3px;
            }}
            QSlider::sub-page:horizontal {{
                background:{self._color}; border-radius:3px;
            }}
            QSlider::handle:horizontal {{
                width:14px; height:14px; margin:-4px 0;
                background:{self._color}; border-radius:7px;
            }}
        """)

        self.val_lbl = QLabel("  0")
        self.val_lbl.setFixedWidth(36)
        self.val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_lbl.setStyleSheet(
            f"color:{self._color}; font-weight:700; font-size:15px;"
        )

        self.alarm_dot = QLabel("●")
        self.alarm_dot.setFixedWidth(14)
        self.alarm_dot.setAlignment(Qt.AlignCenter)
        self.alarm_dot.setStyleSheet(f"color:{C['ok']}; font-size:10px;")

        # WARN spinbox
        warn_lbl = QLabel("W")
        warn_lbl.setFixedWidth(12)
        warn_lbl.setStyleSheet(f"color:{C['warn']}; font-weight:700; font-size:10px;")
        self.warn_spin = QSpinBox()
        self.warn_spin.setRange(0, 100)
        self.warn_spin.setValue(SP.get_warn(idx))
        self.warn_spin.setFixedWidth(52)
        self.warn_spin.setFixedHeight(22)
        self.warn_spin.setStyleSheet(SPIN_STYLE)
        self.warn_spin.setToolTip(f"R{idx:02d} warning setpoint (yellow alarm)")

        # CRIT spinbox
        crit_lbl = QLabel("C")
        crit_lbl.setFixedWidth(12)
        crit_lbl.setStyleSheet(f"color:{C['crit']}; font-weight:700; font-size:10px;")
        self.crit_spin = QSpinBox()
        self.crit_spin.setRange(0, 100)
        self.crit_spin.setValue(SP.get_crit(idx))
        self.crit_spin.setFixedWidth(52)
        self.crit_spin.setFixedHeight(22)
        self.crit_spin.setStyleSheet(SPIN_STYLE)
        self.crit_spin.setToolTip(f"R{idx:02d} critical setpoint (red alarm)")

        self.spark = Sparkline(idx, color=self._color)

        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(10, 6, 10, 2)
        top.addWidget(tag)
        top.addWidget(self.slider, stretch=1)
        top.addWidget(self.val_lbl)
        top.addWidget(self.alarm_dot)
        top.addSpacing(6)
        top.addWidget(warn_lbl)
        top.addWidget(self.warn_spin)
        top.addSpacing(4)
        top.addWidget(crit_lbl)
        top.addWidget(self.crit_spin)

        spark_wrap = QHBoxLayout()
        spark_wrap.setContentsMargins(10, 0, 10, 0)
        spark_wrap.addWidget(self.spark)

        root = QVBoxLayout(self)
        root.setSpacing(2)
        root.setContentsMargins(0, 0, 0, 6)
        root.addLayout(top)
        root.addLayout(spark_wrap)

        self.slider.valueChanged.connect(self._on_slider)
        self.warn_spin.valueChanged.connect(self._on_warn_sp)
        self.crit_spin.valueChanged.connect(self._on_crit_sp)

    def set_value(self, v: int):
        self.slider.blockSignals(True)
        self.slider.setValue(v)
        self.slider.blockSignals(False)
        self._refresh(v)

    def set_warn_sp(self, v: int):
        self.warn_spin.blockSignals(True)
        self.warn_spin.setValue(v)
        self.warn_spin.blockSignals(False)
        SP.set_warn(self._idx, v)
        self.spark.update()

    def set_crit_sp(self, v: int):
        self.crit_spin.blockSignals(True)
        self.crit_spin.setValue(v)
        self.crit_spin.blockSignals(False)
        SP.set_crit(self._idx, v)
        self.spark.update()

    def value(self) -> int:
        return self.slider.value()

    def _on_slider(self, v):
        self._refresh(v)
        self.sig_changed.emit(self._idx, v)

    def _on_warn_sp(self, v):
        SP.set_warn(self._idx, v); SP.save()
        self._refresh(self.slider.value())
        self.spark.update()

    def _on_crit_sp(self, v):
        SP.set_crit(self._idx, v); SP.save()
        self._refresh(self.slider.value())
        self.spark.update()

    def _refresh(self, v):
        self.val_lbl.setText(f"{v:3d}")
        self.spark.push(v)
        state = SP.alarm_state(self._idx, v)
        if state == self._alarm:
            return
        self._alarm = state
        col = {"ok": C["ok"], "warn": C["warn"], "crit": C["crit"]}[state]
        self.alarm_dot.setStyleSheet(f"color:{col}; font-size:10px;")
        self.spark.set_color(col if state != "ok" else self._color)
        self._set_border(col if state != "ok" else C["border"])

    def _set_border(self, color):
        self.setStyleSheet(f"""
            QFrame#regrow {{
                background:{C['card']};
                border:1px solid {color};
                border-radius:8px;
            }}
        """)


# ══════════════════════════════════════════════
#  Alarm panel
# ══════════════════════════════════════════════
class AlarmPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setStyleSheet(f"""
            background:{C['surface']};
            border:1px solid {C['border']};
            border-radius:8px;
        """)

        title = QLabel("ALARMS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color:{C['muted']}; font-size:11px; font-weight:700; letter-spacing:2px;"
            f"border-bottom:1px solid {C['border']}; padding:8px 0; background:transparent;"
        )

        grid = QGridLayout()
        grid.setSpacing(5)
        grid.setContentsMargins(10, 8, 10, 8)

        self._badges: list[QLabel] = []
        for i in range(NUM_REGS):
            name = QLabel(f"R{i:02d}")
            name.setStyleSheet(
                f"color:{C['muted']}; font-size:11px; font-weight:600; background:transparent;"
            )
            badge = QLabel("OK")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedWidth(88)
            badge.setStyleSheet(self._bs("ok"))
            grid.addWidget(name,  i, 0)
            grid.addWidget(badge, i, 1)
            self._badges.append(badge)

        self.summary = QLabel("All registers normal")
        self.summary.setWordWrap(True)
        self.summary.setAlignment(Qt.AlignCenter)
        self.summary.setStyleSheet(
            f"color:{C['ok']}; font-size:11px; font-weight:600; background:transparent;"
            f"border-top:1px solid {C['border']}; padding:8px 4px;"
        )

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(title)
        root.addLayout(grid)
        root.addStretch()
        root.addWidget(self.summary)

    def refresh(self, values: list):
        warn_list, crit_list = [], []
        for i, v in enumerate(values):
            state = SP.alarm_state(i, v)
            if state == "crit":
                self._badges[i].setText("CRITICAL")
                self._badges[i].setStyleSheet(self._bs("crit"))
                crit_list.append(f"R{i:02d}")
            elif state == "warn":
                self._badges[i].setText("HIGH")
                self._badges[i].setStyleSheet(self._bs("warn"))
                warn_list.append(f"R{i:02d}")
            else:
                self._badges[i].setText("OK")
                self._badges[i].setStyleSheet(self._bs("ok"))

        if crit_list:
            self.summary.setText(f"🔴 CRITICAL\n{', '.join(crit_list)}")
            self.summary.setStyleSheet(
                f"color:{C['crit']}; font-size:11px; font-weight:700; background:transparent;"
                f"border-top:1px solid {C['border']}; padding:8px 4px;"
            )
        elif warn_list:
            self.summary.setText(f"⚠ HIGH\n{', '.join(warn_list)}")
            self.summary.setStyleSheet(
                f"color:{C['warn']}; font-size:11px; font-weight:700; background:transparent;"
                f"border-top:1px solid {C['border']}; padding:8px 4px;"
            )
        else:
            self.summary.setText("All registers normal")
            self.summary.setStyleSheet(
                f"color:{C['ok']}; font-size:11px; font-weight:600; background:transparent;"
                f"border-top:1px solid {C['border']}; padding:8px 4px;"
            )

    @staticmethod
    def _bs(state):
        fg = {"ok": C["ok"], "warn": C["warn"], "crit": C["crit"]}[state]
        bg = {"ok": "#14532d33", "warn": "#78350f33", "crit": "#7f1d1d33"}[state]
        return (
            f"color:{fg}; background:{bg}; border:1px solid {fg};"
            f"border-radius:4px; font-size:10px; font-weight:700; padding:2px 0;"
        )


# ══════════════════════════════════════════════
#  Main window
# ══════════════════════════════════════════════
class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modbus Server")
        self.setWindowIcon(server_icon())
        self.resize(1060, 740)
        self._build_context()
        self._build_ui()
        self._wire()
        QTimer(self, timeout=self._sync, interval=SYNC_MS).start()

    def _build_context(self):
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(1, [0]*100),
            co=ModbusSequentialDataBlock(1, [0]*100),
            ir=ModbusSequentialDataBlock(1, [0]*100),
            hr=ValidatedDataBlock(1, [0]*100),
        )
        self.ctx = ModbusServerContext(slaves=store, single=True)

    def _build_ui(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background:{C['bg']}; color:{C['text']}; }}
            QStatusBar {{ background:{C['surface']}; color:{C['muted']}; font-size:11px; }}
            QScrollBar:vertical {{
                background:{C['bg']}; width:6px; border-radius:3px;
            }}
            QScrollBar::handle:vertical {{
                background:{C['border']}; border-radius:3px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 8)
        root.setSpacing(10)

        # header
        hdr = QHBoxLayout()
        dot = QLabel("◆")
        dot.setStyleSheet(f"color:{C['accent']}; font-size:16px;")
        title = QLabel("MODBUS SERVER")
        title.setStyleSheet(
            f"color:{C['text']}; font-size:16px; font-weight:700; letter-spacing:3px;"
        )
        legend = QLabel("  ·  W = warn setpoint   C = crit setpoint   (per register)")
        legend.setStyleSheet(f"color:{C['muted']}; font-size:10px;")

        self._srv_badge = QLabel("● STOPPED")
        self._srv_badge.setStyleSheet(
            f"color:{C['crit']}; font-size:12px; font-weight:600;"
            f"background:#2a0a0a; border:1px solid {C['crit']};"
            f"border-radius:12px; padding:3px 12px;"
        )
        self._start_btn = QPushButton("▶  Start Server")
        self._start_btn.setFixedHeight(32)
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['accent']}; color:#fff;
                border:none; border-radius:6px;
                font-weight:700; font-size:12px; padding:0 18px;
            }}
            QPushButton:hover    {{ background:#2563eb; }}
            QPushButton:disabled {{ background:{C['dim']}; color:{C['muted']}; }}
        """)

        hdr.addWidget(dot)
        hdr.addWidget(title)
        hdr.addWidget(legend)
        hdr.addStretch()
        hdr.addWidget(self._srv_badge)
        hdr.addSpacing(8)
        hdr.addWidget(self._start_btn)
        root.addLayout(hdr)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color:{C['border']};")
        root.addWidget(div)

        # body
        body = QHBoxLayout()
        body.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        col_layout = QVBoxLayout(container)
        col_layout.setSpacing(6)
        col_layout.setContentsMargins(0, 0, 4, 0)

        self._rows: list[RegRow] = []
        for i in range(NUM_REGS):
            row = RegRow(i)
            self._rows.append(row)
            col_layout.addWidget(row)
        col_layout.addStretch()

        scroll.setWidget(container)
        body.addWidget(scroll, stretch=1)

        self._alarm_panel = AlarmPanel()
        body.addWidget(self._alarm_panel)

        root.addLayout(body, stretch=1)

        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._sb.showMessage("Server not started.")

    def _wire(self):
        self._start_btn.clicked.connect(self._start_server)
        for row in self._rows:
            row.sig_changed.connect(self._on_row_changed)

    def _start_server(self):
        self._start_btn.setEnabled(False)
        self._srv_badge.setText(f"● RUNNING  :{PORT}")
        self._srv_badge.setStyleSheet(
            f"color:{C['ok']}; font-size:12px; font-weight:600;"
            f"background:#052e16; border:1px solid {C['ok']};"
            f"border-radius:12px; padding:3px 12px;"
        )
        self._sb.showMessage(f"Listening on {HOST}:{PORT}")
        threading.Thread(
            target=lambda: StartTcpServer(context=self.ctx, address=(HOST, PORT)),
            daemon=True,
        ).start()

    def _on_row_changed(self, idx: int, value: int):
        self.ctx[0].setValues(3, idx+1, [value])
        self._sb.showMessage(f"R{idx:02d} → {value}  (slider)")

    def _sync(self):
        try:
            vals = self.ctx[0].getValues(3, 1, NUM_REGS)
        except Exception:
            return
        for i, v in enumerate(vals):
            self._rows[i].set_value(v)
        self._alarm_panel.refresh(vals)


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(server_icon())
    app.setFont(QFont("Segoe UI", 10))
    w = ServerWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
