import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QTextEdit, QGroupBox, QLineEdit, QPushButton,
    QSlider
)
from PyQt6.QtCore import pyqtSignal, QObject, pyqtSlot, Qt
from PyQt6.QtGui import QFont


class DashboardSignals(QObject):
    # 'object' type accepts Pydantic models — PyQt6 doesn't register them natively
    state_updated = pyqtSignal(object)
    log_message = pyqtSignal(str)
    # Signal fired when the user submits a typed text command
    text_command_submitted = pyqtSignal(str)
    # Signal fired when a slider is moved: (command_str, value_int)
    slider_command = pyqtSignal(str, int)


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Automotive Instrument Cluster")
        self.setGeometry(100, 100, 940, 720)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")

        self.signals = DashboardSignals()
        self.signals.state_updated.connect(self.update_ui_state)
        self.signals.log_message.connect(self.append_log)

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 8, 12, 12)
        main_layout.setSpacing(8)
        central_widget.setLayout(main_layout)

        # ── Title ─────────────────────────────────────────────────────────
        title_label = QLabel("🚗  AUTOMOTIVE INSTRUMENT CLUSTER")
        title_label.setFont(QFont("Arial", 17, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #00CFFF; padding: 6px 0; letter-spacing: 2px;")
        main_layout.addWidget(title_label)

        # ── Status panels grid ─────────────────────────────────────────────
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        main_layout.addLayout(grid_layout)

        # Climate Control
        climate_group = self._make_group("🌡  CLIMATE CONTROL")
        climate_layout = QVBoxLayout()
        self.lbl_ac_temp   = QLabel("AC Temp:   --°C")
        self.lbl_fan_speed = QLabel("Fan Speed: [      ]")
        self.lbl_ac_on     = QLabel("AC Status: [ ON ]")
        self.lbl_ac_on.setStyleSheet("color: #00FF9F;")
        for w in (self.lbl_ac_temp, self.lbl_fan_speed, self.lbl_ac_on):
            w.setStyleSheet(w.styleSheet() + " font-size: 14px; padding: 2px;")
            climate_layout.addWidget(w)
        climate_group.setLayout(climate_layout)
        grid_layout.addWidget(climate_group, 0, 0)

        # Sunroof & Windows — with interactive sliders
        sunroof_group = self._make_group("🌤  SUNROOF & WINDOWS")
        sunroof_layout = QVBoxLayout()

        # Sunroof row
        sroof_row = QHBoxLayout()
        self.lbl_sunroof = QLabel("Sunroof:  0%")
        self.lbl_sunroof.setStyleSheet("font-size: 13px; min-width: 100px;")
        self.slider_sunroof = QSlider(Qt.Orientation.Horizontal)
        self.slider_sunroof.setRange(0, 100)
        self.slider_sunroof.setValue(0)
        self.slider_sunroof.setTickInterval(25)
        self.slider_sunroof.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #00CFFF; width: 16px; height: 16px; "
            "margin: -5px 0; border-radius: 8px; }"
            "QSlider::sub-page:horizontal { background: #00CFFF; border-radius: 3px; }"
        )
        self.slider_sunroof.valueChanged.connect(
            lambda v: (self.lbl_sunroof.setText(f"Sunroof: {v}%"),
                       self.signals.slider_command.emit("open_sunroof", v))
        )
        sroof_row.addWidget(self.lbl_sunroof)
        sroof_row.addWidget(self.slider_sunroof)
        sunroof_layout.addLayout(sroof_row)

        # Window row
        win_row = QHBoxLayout()
        self.lbl_window = QLabel("Window:  0%")
        self.lbl_window.setStyleSheet("font-size: 13px; min-width: 100px;")
        self.slider_window = QSlider(Qt.Orientation.Horizontal)
        self.slider_window.setRange(0, 100)
        self.slider_window.setValue(0)
        self.slider_window.setTickInterval(25)
        self.slider_window.setStyleSheet(
            "QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #88FF88; width: 16px; height: 16px; "
            "margin: -5px 0; border-radius: 8px; }"
            "QSlider::sub-page:horizontal { background: #88FF88; border-radius: 3px; }"
        )
        self.slider_window.valueChanged.connect(
            lambda v: (self.lbl_window.setText(f"Window: {v}%"),
                       self.signals.slider_command.emit("open_window", v))
        )
        win_row.addWidget(self.lbl_window)
        win_row.addWidget(self.slider_window)
        sunroof_layout.addLayout(win_row)

        sunroof_group.setLayout(sunroof_layout)
        grid_layout.addWidget(sunroof_group, 0, 1)

        # Lighting
        lighting_group = self._make_group("💡  LIGHTING")
        lighting_layout = QVBoxLayout()
        self.lbl_headlights = QLabel("Headlights: [ OFF ]")
        self.lbl_headlights.setStyleSheet("font-size: 14px; padding: 2px; color: #888888;")
        lighting_layout.addWidget(self.lbl_headlights)
        lighting_group.setLayout(lighting_layout)
        grid_layout.addWidget(lighting_group, 1, 0)

        # Assistant Status
        assistant_group = self._make_group("🎙  ASSISTANT STATUS")
        assistant_layout = QVBoxLayout()
        self.lbl_assistant = QLabel("Status: [ Idle ]")
        self.lbl_assistant.setStyleSheet("color: #00FF00; font-size: 14px; padding: 2px;")
        assistant_layout.addWidget(self.lbl_assistant)
        assistant_group.setLayout(assistant_layout)
        grid_layout.addWidget(assistant_group, 1, 1)

        # ── CAN Bus Logger ─────────────────────────────────────────────────
        log_group = self._make_group("📡  VIRTUAL CAN BUS LIVE TELEMETRY")
        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFixedHeight(170)
        self.log_text_edit.setStyleSheet(
            "background-color: #0a0a0a; color: #00FF00; "
            "font-family: monospace; font-size: 12px; border: none;"
        )
        log_layout.addWidget(self.log_text_edit)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # ── Text Command Input ─────────────────────────────────────────────
        cmd_group = self._make_group("⌨️  TEXT COMMAND  (type here if voice isn't clear)")
        cmd_group.setStyleSheet(
            cmd_group.styleSheet() +
            "QGroupBox { border-color: #335577; }"
        )
        cmd_outer = QVBoxLayout()

        cmd_row = QHBoxLayout()
        self.txt_command = QLineEdit()
        self.txt_command.setPlaceholderText(
            'e.g. "Set temperature to 24"  /  "Turn on headlights"  /  "Open sunroof halfway"'
        )
        self.txt_command.setStyleSheet(
            "background-color: #1e1e2e; color: #E0E0E0; border: 1px solid #445577; "
            "border-radius: 5px; padding: 6px 10px; font-size: 13px;"
        )
        self.txt_command.returnPressed.connect(self._on_send_text_command)

        self.btn_send = QPushButton("▶  Send")
        self.btn_send.setFixedWidth(100)
        self.btn_send.setStyleSheet(
            "background-color: #0066CC; color: white; border: none; "
            "border-radius: 5px; padding: 7px 12px; font-size: 13px; font-weight: bold;"
        )
        self.btn_send.clicked.connect(self._on_send_text_command)

        cmd_row.addWidget(self.txt_command)
        cmd_row.addWidget(self.btn_send)
        cmd_outer.addLayout(cmd_row)

        # Quick-fire example buttons — natural phrases + explicit commands
        examples_row1 = QHBoxLayout()
        examples_row1.setSpacing(6)
        examples_row2 = QHBoxLayout()
        examples_row2.setSpacing(6)

        natural_phrases = [
            "I'm feeling hot 🥵",
            "I want fresh air 🌬️",
            "It's stuffy in here",
            "I'm freezing 🥶",
            "It's getting dark 🌙",
            "It's starting to rain 🌧️",
        ]
        explicit_cmds = [
            "Set AC to 24 degrees",
            "Open sunroof halfway",
            "Turn on headlights",
            "Close sunroof",
            "Turn off AC",
            "Fan speed max",
        ]

        def make_btn(label, style_extra=""):
            b = QPushButton(label)
            b.setStyleSheet(
                f"background-color: #1e2a1e; color: #88CC88; border: 1px solid #336633; "
                f"border-radius: 4px; padding: 5px 8px; font-size: 11px; {style_extra}"
            )
            return b

        for phrase in natural_phrases:
            raw = phrase.split(" 🥵")[0].split(" 🌬️")[0].split(" 🥶")[0].split(" 🌙")[0].split(" 🌧️")[0]
            btn = make_btn(phrase, "background-color: #1e1e2e; color: #88AAFF; border-color: #334477;")
            btn.clicked.connect(lambda checked, t=raw: self._submit_command(t))
            examples_row1.addWidget(btn)

        for cmd in explicit_cmds:
            btn = make_btn(cmd)
            btn.clicked.connect(lambda checked, t=cmd: self._submit_command(t))
            examples_row2.addWidget(btn)

        cmd_outer.addLayout(examples_row1)
        cmd_outer.addLayout(examples_row2)
        cmd_group.setLayout(cmd_outer)
        main_layout.addWidget(cmd_group)

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _make_group(title: str) -> QGroupBox:
        g = QGroupBox(title)
        g.setStyleSheet(
            "QGroupBox { font-weight: bold; font-size: 12px; color: #AAAAAA; "
            "border: 1px solid #333; border-radius: 6px; margin-top: 12px; padding-top: 8px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }"
        )
        return g

    def _on_send_text_command(self):
        text = self.txt_command.text().strip()
        if text:
            self._submit_command(text)
            self.txt_command.clear()

    def _submit_command(self, text: str):
        self.append_log(f"[TEXT INPUT] → \"{text}\"")
        self.signals.text_command_submitted.emit(text)

    # ── Slots (called only on main/UI thread via pyqtSignal) ──────────────

    @pyqtSlot(object)
    def update_ui_state(self, state):
        """Thread-safe update of all dashboard indicators."""
        self.lbl_ac_temp.setText(f"AC Temp:   {state.ac_temperature:.1f}°C")
        fan_bars = "|" * state.fan_speed + "─" * (6 - state.fan_speed)
        self.lbl_fan_speed.setText(f"Fan Speed: [{fan_bars}]")
        self.lbl_ac_on.setText(f"AC Status: [ {'ON' if state.ac_on else 'OFF'} ]")

        self.lbl_sunroof.setText(f"Sunroof: {state.sunroof_position}%")
        self.slider_sunroof.blockSignals(True)
        self.slider_sunroof.setValue(state.sunroof_position)
        self.slider_sunroof.blockSignals(False)

        self.lbl_window.setText(f"Window: {state.window_position}%")
        self.slider_window.blockSignals(True)
        self.slider_window.setValue(state.window_position)
        self.slider_window.blockSignals(False)

        hl = state.headlights_on
        self.lbl_headlights.setText(f"Headlights: [ {'ON' if hl else 'OFF'} ]")
        self.lbl_headlights.setStyleSheet(
            f"font-size: 14px; padding: 2px; color: {'#FFD700' if hl else '#888888'};"
        )

        status_colors = {
            "Idle":       "#00FF00",
            "Listening":  "#FF4444",
            "Processing": "#FFAA00",
            "Speaking":   "#00AAFF",
        }
        color = status_colors.get(state.assistant_status, "#FFFFFF")
        self.lbl_assistant.setText(f"Status: [ {state.assistant_status} ]")
        self.lbl_assistant.setStyleSheet(
            f"color: {color}; font-size: 14px; padding: 2px;"
        )

    @pyqtSlot(str)
    def append_log(self, message: str):
        """Thread-safe append to the CAN bus log."""
        self.log_text_edit.append(message)
        sb = self.log_text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
