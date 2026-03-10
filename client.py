"""
Modbus Client  ─  PySide6 + pymodbus
Per-register WARN / CRIT setpoints editable live.
Alarms shown on cards, alarm panel, and write table.
Setpoints saved to setpoints.json and shared with the server when running on same machine.
"""

import sys
import collections
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QStatusBar, QSpinBox,
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui  import QColor, QFont, QPainter, QPen, QBrush, QPolygon
from pymodbus.client import ModbusTcpClient
import setpoints as SP
from app_icons import client_icon

SERVER_IP    = "127.0.0.1"
PORT         = 5020
NUM_REGS     = SP.NUM_REGS
CHART_LEN    = 80
READ_MS      = 400
RECONNECT_MS = 3000

C = {
    "bg"      : "#0a0e17",
    "surface" : "#111827",
    "card"    : "#1a2235",
    "border"  : "#1f2d45",
    "accent"  : "#6366f1",
    "ok"      : "#22c55e",
    "warn"    : "#f59e0b",
    "crit"    : "#ef4444",
    "text"    : "#f1f5f9",
    "muted"   : "#64748b",
    "dim"     : "#1e293b",
}

REG_HUE = [
    "#6366f1","#14b8a6","#a78bfa","#f472b6","#fb923c",
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
#  Sparkline
# ══════════════════════════════════════════════
class Sparkline(QFrame):
    def __init__(self, reg_idx: int, color: str, parent=None):
        super().__init__(parent)
        self._idx   = reg_idx
        self._buf   = collections.deque([0]*CHART_LEN, maxlen=CHART_LEN)
        self._color = QColor(color)
        self.setFixedHeight(44)
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
#  Live register card  (read-only monitor)
# ══════════════════════════════════════════════
class RegCard(QFrame):
    def __init__(self, idx: int, parent=None):
        super().__init__(parent)
        self._idx   = idx
        self._color = REG_HUE[idx % len(REG_HUE)]
        self._alarm = "ok"
        self.setObjectName("regcard")
        self._set_border(C["border"])

        tag = QLabel(f"R{idx:02d}")
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(
            f"color:{self._color}; font-weight:700; font-size:11px;"
            f"background:{C['dim']}; border-radius:4px; padding:2px 6px;"
        )

        self.val_lbl = QLabel("0")
        self.val_lbl.setAlignment(Qt.AlignCenter)
        self.val_lbl.setStyleSheet(
            f"color:{self._color}; font-size:26px; font-weight:700;"
        )

        self.alarm_lbl = QLabel("● OK")
        self.alarm_lbl.setAlignment(Qt.AlignCenter)
        self.alarm_lbl.setStyleSheet(
            f"color:{C['ok']}; font-size:10px; font-weight:700;"
        )

        self.spark = Sparkline(idx, color=self._color)

        root = QVBoxLayout(self)
        root.setSpacing(3)
        root.setContentsMargins(8, 8, 8, 6)
        root.addWidget(tag)
        root.addWidget(self.val_lbl)
        root.addWidget(self.alarm_lbl)
        root.addWidget(self.spark)

    def update_value(self, v: int):
        self.val_lbl.setText(str(v))
        self.spark.push(v)
        state = SP.alarm_state(self._idx, v)
        if state == self._alarm:
            return
        self._alarm = state
        text  = {"ok": "● OK", "warn": "▲ HIGH", "crit": "■ CRITICAL"}[state]
        color = {"ok": C["ok"], "warn": C["warn"], "crit": C["crit"]}[state]
        self.alarm_lbl.setText(text)
        self.alarm_lbl.setStyleSheet(f"color:{color}; font-size:10px; font-weight:700;")
        self.spark.set_color(color if state != "ok" else self._color)
        self._set_border(color if state != "ok" else C["border"])

    def refresh_setpoints(self):
        """Call when setpoints change so sparkline redraws threshold lines."""
        self.spark.update()

    def _set_border(self, color):
        self.setStyleSheet(f"""
            QFrame#regcard {{
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
            badge = QLabel("—")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedWidth(88)
            badge.setStyleSheet(self._bs("ok"))
            grid.addWidget(name,  i, 0)
            grid.addWidget(badge, i, 1)
            self._badges.append(badge)

        self.summary = QLabel("Waiting for data…")
        self.summary.setWordWrap(True)
        self.summary.setAlignment(Qt.AlignCenter)
        self.summary.setStyleSheet(
            f"color:{C['muted']}; font-size:11px; background:transparent;"
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
#  Write + Setpoint table
# ══════════════════════════════════════════════
class WriteTable(QFrame):
    """
    Columns: Reg | Set Value (write spinbox) | Last Read | W setpoint | C setpoint
    """
    def __init__(self, on_sp_changed, parent=None):
        """
        on_sp_changed(idx) called whenever a setpoint spinbox changes,
        so the main window can refresh cards/alarm panel.
        """
        super().__init__(parent)
        self._on_sp_changed = on_sp_changed
        self.setFixedWidth(310)
        self.setStyleSheet(f"""
            background:{C['surface']};
            border:1px solid {C['border']};
            border-radius:8px;
        """)

        # ── title row
        title = QLabel("WRITE  /  SETPOINTS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color:{C['muted']}; font-size:11px; font-weight:700; letter-spacing:2px;"
            f"border-bottom:1px solid {C['border']}; padding:8px 0; background:transparent;"
        )

        # ── column headers
        hdr_grid = QGridLayout()
        hdr_grid.setContentsMargins(10, 4, 10, 0)
        hdr_grid.setSpacing(4)
        for col, (txt, w) in enumerate([
            ("Reg",   28),
            ("Write", 52),
            ("Read",  36),
            ("W",     48),
            ("C",     48),
        ]):
            lbl = QLabel(txt)
            lbl.setFixedWidth(w)
            lbl.setAlignment(Qt.AlignCenter)
            colors = ["muted","muted","muted","warn","crit"]
            lbl.setStyleSheet(
                f"color:{C[colors[col]]}; font-size:10px; font-weight:700; background:transparent;"
            )
            hdr_grid.addWidget(lbl, 0, col)

        # ── data rows
        data_grid = QGridLayout()
        data_grid.setContentsMargins(10, 4, 10, 4)
        data_grid.setSpacing(4)

        self._write_spins: list[QSpinBox] = []
        self._read_lbls:   list[QLabel]   = []
        self._warn_spins:  list[QSpinBox] = []
        self._crit_spins:  list[QSpinBox] = []

        for i in range(NUM_REGS):
            # tag
            tag = QLabel(f"R{i:02d}")
            tag.setFixedWidth(28)
            tag.setAlignment(Qt.AlignCenter)
            tag.setStyleSheet(
                f"color:{REG_HUE[i % len(REG_HUE)]}; font-weight:700;"
                f"font-size:11px; background:transparent;"
            )

            # write spinbox
            w_spin = QSpinBox()
            w_spin.setRange(0, 100)
            w_spin.setValue(0)
            w_spin.setFixedWidth(52)
            w_spin.setFixedHeight(24)
            w_spin.setStyleSheet(SPIN_STYLE)
            w_spin.setToolTip(f"Value to write to R{i:02d}")

            # last read label
            read_lbl = QLabel("—")
            read_lbl.setFixedWidth(36)
            read_lbl.setAlignment(Qt.AlignCenter)
            read_lbl.setStyleSheet(
                f"color:{C['muted']}; font-size:11px; background:transparent;"
            )

            # warn setpoint
            warn_sp = QSpinBox()
            warn_sp.setRange(0, 100)
            warn_sp.setValue(SP.get_warn(i))
            warn_sp.setFixedWidth(48)
            warn_sp.setFixedHeight(24)
            warn_sp.setStyleSheet(SPIN_STYLE)
            warn_sp.setToolTip(f"R{i:02d} warning threshold")

            # crit setpoint
            crit_sp = QSpinBox()
            crit_sp.setRange(0, 100)
            crit_sp.setValue(SP.get_crit(i))
            crit_sp.setFixedWidth(48)
            crit_sp.setFixedHeight(24)
            crit_sp.setStyleSheet(SPIN_STYLE)
            crit_sp.setToolTip(f"R{i:02d} critical threshold")

            data_grid.addWidget(tag,      i, 0)
            data_grid.addWidget(w_spin,   i, 1)
            data_grid.addWidget(read_lbl, i, 2)
            data_grid.addWidget(warn_sp,  i, 3)
            data_grid.addWidget(crit_sp,  i, 4)

            # capture i for lambdas
            def make_warn_cb(idx):
                def cb(v):
                    SP.set_warn(idx, v); SP.save()
                    self._on_sp_changed(idx)
                return cb

            def make_crit_cb(idx):
                def cb(v):
                    SP.set_crit(idx, v); SP.save()
                    self._on_sp_changed(idx)
                return cb

            warn_sp.valueChanged.connect(make_warn_cb(i))
            crit_sp.valueChanged.connect(make_crit_cb(i))

            self._write_spins.append(w_spin)
            self._read_lbls.append(read_lbl)
            self._warn_spins.append(warn_sp)
            self._crit_spins.append(crit_sp)

        # ── buttons
        self.write_all_btn = QPushButton("⬆  Write All")
        self.write_sel_btn = QPushButton("⬆  Write Selected")
        for btn in (self.write_all_btn, self.write_sel_btn):
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{C['accent']}; color:#fff;
                    border:none; border-radius:5px;
                    font-weight:700; font-size:11px;
                }}
                QPushButton:hover    {{ background:#4f46e5; }}
                QPushButton:disabled {{ background:{C['dim']}; color:{C['muted']}; }}
            """)

        self.msg_lbl = QLabel("")
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setAlignment(Qt.AlignCenter)
        self.msg_lbl.setStyleSheet(
            f"color:{C['muted']}; font-size:11px; background:transparent;"
            f"border-top:1px solid {C['border']}; padding:5px 4px;"
        )

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(10, 0, 10, 0)
        btn_row.setSpacing(6)
        btn_row.addWidget(self.write_all_btn)
        btn_row.addWidget(self.write_sel_btn)

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(title)
        root.addLayout(hdr_grid)
        root.addLayout(data_grid)
        root.addLayout(btn_row)
        root.addWidget(self.msg_lbl)
        root.addStretch()

    # ── public API ─────────────────────────────
    def get_write_value(self, idx: int) -> int:
        return self._write_spins[idx].value()

    def set_read(self, idx: int, v: int):
        lbl = self._read_lbls[idx]
        lbl.setText(str(v))
        state = SP.alarm_state(idx, v)
        color = {"ok": C["muted"], "warn": C["warn"], "crit": C["crit"]}[state]
        lbl.setStyleSheet(
            f"color:{color}; font-size:11px; font-weight:700; background:transparent;"
        )

    def selected_row(self) -> int:
        for i, s in enumerate(self._write_spins):
            if s.hasFocus():
                return i
        return -1

    def set_msg(self, text: str, ok=False):
        color = C["ok"] if ok else C["warn"]
        self.msg_lbl.setText(text)
        self.msg_lbl.setStyleSheet(
            f"color:{color}; font-size:11px; background:transparent;"
            f"border-top:1px solid {C['border']}; padding:5px 4px;"
        )


# ══════════════════════════════════════════════
#  Main window
# ══════════════════════════════════════════════
class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modbus Client")
        self.setWindowIcon(client_icon())
        self.resize(1160, 740)
        self._client    = ModbusTcpClient(SERVER_IP, port=PORT)
        self._connected = False
        self._build_ui()
        self._wire()
        self._start_timers()
        self._try_connect()

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
        title = QLabel("MODBUS CLIENT")
        title.setStyleSheet(
            f"color:{C['text']}; font-size:16px; font-weight:700; letter-spacing:3px;"
        )
        legend = QLabel("  ·  W = warn setpoint   C = crit setpoint   (per register)")
        legend.setStyleSheet(f"color:{C['muted']}; font-size:10px;")

        self._conn_badge = QLabel("● DISCONNECTED")
        self._conn_badge.setStyleSheet(
            f"color:{C['crit']}; font-size:12px; font-weight:600;"
            f"background:#2a0a0a; border:1px solid {C['crit']};"
            f"border-radius:12px; padding:3px 12px;"
        )
        self._reconn_btn = QPushButton("↻  Reconnect")
        self._reconn_btn.setFixedHeight(32)
        self._reconn_btn.setCursor(Qt.PointingHandCursor)
        self._reconn_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['dim']}; color:{C['muted']};
                border:1px solid {C['border']}; border-radius:6px;
                font-weight:600; font-size:12px; padding:0 14px;
            }}
            QPushButton:hover {{ color:{C['text']}; border-color:{C['accent']}; }}
        """)

        hdr.addWidget(dot)
        hdr.addWidget(title)
        hdr.addWidget(legend)
        hdr.addStretch()
        hdr.addWidget(self._conn_badge)
        hdr.addSpacing(8)
        hdr.addWidget(self._reconn_btn)
        root.addLayout(hdr)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color:{C['border']};")
        root.addWidget(div)

        # body
        body = QHBoxLayout()
        body.setSpacing(12)

        # card grid (2 columns, scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        card_grid = QGridLayout(container)
        card_grid.setSpacing(8)
        card_grid.setContentsMargins(0, 0, 4, 0)

        self._cards: list[RegCard] = []
        for i in range(NUM_REGS):
            card = RegCard(i)
            self._cards.append(card)
            card_grid.addWidget(card, i // 2, i % 2)

        scroll.setWidget(container)
        body.addWidget(scroll, stretch=1)

        # alarm panel
        self._alarm_panel = AlarmPanel()
        body.addWidget(self._alarm_panel)

        # write + setpoint table
        self._write_table = WriteTable(on_sp_changed=self._on_sp_changed)
        body.addWidget(self._write_table)

        root.addLayout(body, stretch=1)

        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._sb.showMessage("Not connected.")

    def _wire(self):
        self._reconn_btn.clicked.connect(self._try_connect)
        self._write_table.write_all_btn.clicked.connect(self._write_all)
        self._write_table.write_sel_btn.clicked.connect(self._write_selected)

    def _start_timers(self):
        self._read_timer    = QTimer(self, timeout=self._read,        interval=READ_MS)
        self._reconn_timer  = QTimer(self, timeout=self._try_connect, interval=RECONNECT_MS)
        self._reconn_timer.start()

    # ── setpoint changed locally ───────────────
    def _on_sp_changed(self, idx: int):
        """Setpoint spinbox changed — refresh card threshold lines and alarm panel."""
        self._cards[idx].refresh_setpoints()
        # re-evaluate alarm state against latest known read value
        read_text = self._write_table._read_lbls[idx].text()
        try:
            v = int(read_text)
            self._cards[idx].update_value(v)
        except ValueError:
            pass

    # ── connection ─────────────────────────────
    def _try_connect(self):
        if self._connected:
            return
        try:
            if self._client.connect():
                self._connected = True
                self._conn_badge.setText(f"● CONNECTED  {SERVER_IP}:{PORT}")
                self._conn_badge.setStyleSheet(
                    f"color:{C['ok']}; font-size:12px; font-weight:600;"
                    f"background:#052e16; border:1px solid {C['ok']};"
                    f"border-radius:12px; padding:3px 12px;"
                )
                self._sb.showMessage(f"Connected to {SERVER_IP}:{PORT}")
                self._read_timer.start()
            else:
                self._sb.showMessage("Connection failed — retrying…")
        except Exception as e:
            self._sb.showMessage(f"Error: {e}")

    def _disconnect(self):
        if not self._connected:
            return
        self._connected = False
        self._client.close()
        self._read_timer.stop()
        self._conn_badge.setText("● DISCONNECTED")
        self._conn_badge.setStyleSheet(
            f"color:{C['crit']}; font-size:12px; font-weight:600;"
            f"background:#2a0a0a; border:1px solid {C['crit']};"
            f"border-radius:12px; padding:3px 12px;"
        )
        self._sb.showMessage("Disconnected — retrying…")

    # ── read ───────────────────────────────────
    def _read(self):
        try:
            rr = self._client.read_holding_registers(1, NUM_REGS)
            if rr.isError():
                self._disconnect(); return
            vals = rr.registers
            for i, v in enumerate(vals):
                self._cards[i].update_value(v)
                self._write_table.set_read(i, v)
            self._alarm_panel.refresh(vals)
        except Exception:
            self._disconnect()

    # ── write ──────────────────────────────────
    def _send(self, idx: int, value: int) -> bool:
        if not self._connected:
            self._write_table.set_msg("⚠ Not connected")
            return False
        try:
            res = self._client.write_register(idx+1, value)
            if res.isError():
                self._write_table.set_msg(f"⚠ Server rejected R{idx:02d}")
                return False
            return True
        except Exception as e:
            self._write_table.set_msg(f"⚠ Error: {e}")
            self._disconnect()
            return False

    def _write_all(self):
        failed = [str(i) for i in range(NUM_REGS)
                  if not self._send(i, self._write_table.get_write_value(i))]
        if failed:
            self._write_table.set_msg(f"⚠ Failed: R{', R'.join(failed)}")
        else:
            self._write_table.set_msg("✓ All registers written", ok=True)
            self._sb.showMessage("All registers written.")

    def _write_selected(self):
        row = self._write_table.selected_row()
        if row < 0:
            self._write_table.set_msg("⚠ Click a Write spinbox first")
            return
        v = self._write_table.get_write_value(row)
        if self._send(row, v):
            self._write_table.set_msg(f"✓ R{row:02d} → {v}", ok=True)
            self._sb.showMessage(f"R{row:02d} → {v}")


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(client_icon())
    app.setFont(QFont("Segoe UI", 10))
    w = ClientWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
