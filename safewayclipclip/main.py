#!/usr/bin/env python3

# This script clips all available Safeway coupons.

import argparse
import atexit
from functools import partial
import logging
import os
import sys
import time

from PyQt5.QtCore import (
    Qt, QMetaObject, QObject, QThread, pyqtSlot, pyqtSignal)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QProgressBar,
    QPushButton, QShortcut, QWidget, QVBoxLayout)

from safewayclipclip.args import (
    define_common_args, get_name_to_help_dict, BASE_PATH)
from safewayclipclip.webdriver import get_webdriver

logger = logging.getLogger(__name__)

NEVER_SAVE_MSG = 'Username is *never* saved.'


class ClipClipGui:
    def __init__(self, args, arg_name_to_help):
        self.args = args
        self.arg_name_to_help = arg_name_to_help

    def create_gui(self):
        try:
            from fbs_runtime.application_context.PyQt5 import (
                ApplicationContext)
            appctxt = ApplicationContext()
            app = appctxt.app
        except ImportError:
            app = QApplication(sys.argv)
        app.setStyle('Fusion')
        self.window = QMainWindow()

        self.quit_shortcuts = []
        for seq in ("Ctrl+Q", "Ctrl+C", "Ctrl+W", "ESC"):
            s = QShortcut(QKeySequence(seq), self.window)
            s.activated.connect(app.exit)
            self.quit_shortcuts.append(s)

        v_layout = QVBoxLayout()

        safeway_group = QGroupBox('Safeway Login')
        safeway_group.setMinimumWidth(350)
        safeway_layout = QFormLayout()

        safeway_layout.addRow(
            'Username (email or phone#):',
            self.create_line_edit('safeway_username', tool_tip=NEVER_SAVE_MSG))
        safeway_layout.addRow(
            'I will login myself',
            self.create_checkbox('safeway_user_will_login'))

        safeway_group.setLayout(safeway_layout)
        v_layout.addWidget(safeway_group)

        self.start_button = QPushButton('Go')
        self.start_button.setAutoDefault(True)
        self.start_button.clicked.connect(self.on_start_button_clicked)
        v_layout.addWidget(self.start_button)

        main_widget = QWidget()
        main_widget.setLayout(v_layout)
        self.window.setCentralWidget(main_widget)
        self.window.show()
        return app.exec_()

    def on_quit(self):
        pass

    def on_dialog_closed(self):
        self.start_button.setEnabled(True)

    def on_start_button_clicked(self):
        self.start_button.setEnabled(False)
        args = argparse.Namespace(**vars(self.args))
        self.progress = ProgressDialog(
            args=args,
            parent=self.window)
        self.progress.show()
        self.progress.finished.connect(self.on_dialog_closed)

    def clear_layout(self, layout):
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()
                elif child.layout() is not None:
                    self.clear_layout(child.layout())

    def create_checkbox(self, name, tool_tip=None, invert=False):
        x_box = QCheckBox()
        x_box.setTristate(False)
        x_box.setCheckState(
            Qt.Checked if getattr(self.args, name) else Qt.Unchecked)
        if not tool_tip and name in self.arg_name_to_help:
            tool_tip = 'When checked, ' + self.arg_name_to_help[name]
        if tool_tip:
            x_box.setToolTip(tool_tip)

        def on_changed(state):
            setattr(
                self.args, name,
                state != Qt.Checked if invert else state == Qt.Checked)
        x_box.stateChanged.connect(on_changed)
        return x_box

    def advance_focus(self):
        self.window.focusNextChild()

    def create_line_edit(self, name, tool_tip=None, password=False):
        line_edit = QLineEdit(getattr(self.args, name))
        if not tool_tip:
            tool_tip = self.arg_name_to_help[name]
        if tool_tip:
            line_edit.setToolTip(tool_tip)
        if password:
            line_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        def on_changed(state):
            setattr(self.args, name, state)

        def on_return():
            self.advance_focus()
        line_edit.textChanged.connect(on_changed)
        line_edit.returnPressed.connect(on_return)
        return line_edit


class ProgressDialog(QDialog):
    def __init__(self, args, **kwargs):
        super(ProgressDialog, self).__init__(**kwargs)

        self.args = args

        self.worker = Worker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.worker.on_error.connect(self.on_error)
        self.worker.on_stopped.connect(self.on_stopped)
        self.worker.on_progress.connect(self.on_progress)

        self.thread.started.connect(
            partial(self.worker.clip_clip, args, self))
        self.thread.start()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('ClipClip is running...')
        self.setModal(True)
        self.v_layout = QVBoxLayout()
        self.setLayout(self.v_layout)

        self.label = QLabel()
        self.v_layout.addWidget(self.label)

        self.progress = 0
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.v_layout.addWidget(self.progress_bar)

        self.button_bar = QHBoxLayout()
        self.v_layout.addLayout(self.button_bar)

        self.cancel_button = QPushButton('Cancel')
        self.button_bar.addWidget(self.cancel_button)
        self.cancel_button.clicked.connect(self.on_cancel)

    def on_error(self, msg):
        logger.error(msg)
        self.label.setText('Error: {}'.format(msg))
        self.label.setStyleSheet(
            'QLabel { color: red; font-weight: bold; }')
        self.cancel_button.setText('Close')
        self.cancel_button.clicked.connect(self.close)

    def on_stopped(self):
        self.close()

    def on_progress(self, msg, max, value):
        self.label.setText(msg)
        self.progress_bar.setRange(0, max)
        self.progress_bar.setValue(value)

    def on_cancel(self):
        if not self.reviewing:
            QMetaObject.invokeMethod(
                self.worker, 'stop', Qt.QueuedConnection)
        else:
            self.close()


class Worker(QObject):
    """This class is required to prevent locking up the main Qt thread."""
    on_error = pyqtSignal(str)
    on_done = pyqtSignal(int)
    on_stopped = pyqtSignal()
    on_progress = pyqtSignal(str, int, int)
    stopping = False
    webdriver = None

    @pyqtSlot()
    def stop(self):
        self.stopping = True

    @pyqtSlot(object)
    def clip_clip(self, args, parent):
        try:
            self.do_clip_clip(args, parent)
        except Exception as e:
            msg = 'Internal error while running clip clip: {}'.format(e)
            self.on_error.emit(msg)
            logger.exception(msg)

    def close_webdriver(self):
        if self.webdriver:
            self.webdriver.close()
            self.webdriver = None

    def get_webdriver(self, args):
        if self.webdriver:
            logger.info('Using existing webdriver')
            return self.webdriver
        logger.info('Creating a new webdriver')
        self.webdriver = get_webdriver(args.headless, args.session_path)
        return self.webdriver

    def do_clip_clip(self, args, parent):
        atexit.register(self.close_webdriver)
        # bound_webdriver_factory = partial(self.get_webdriver, args)
        num_clips = 1000
        self.on_done.emit(num_clips)
        self.close_webdriver()


def main():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(logging.StreamHandler())
    # Disable noisy log spam from filelock from within tldextract.
    logging.getLogger("filelock").setLevel(logging.WARN)
    # For helping remote debugging, also log to file.
    # Developers should be vigilant to NOT log any PII, ever (including being
    # mindful of what exceptions might be thrown).
    log_directory = os.path.join(BASE_PATH, 'Logs')
    os.makedirs(log_directory, exist_ok=True)
    log_filename = os.path.join(log_directory, '{}.log'.format(
        time.strftime("%Y-%m-%d_%H-%M-%S")))
    root_logger.addHandler(logging.FileHandler(log_filename))

    parser = argparse.ArgumentParser(description='Clip Safeway coupons.')
    define_common_args(parser)
    args = parser.parse_args()

    sys.exit(ClipClipGui(args, get_name_to_help_dict(parser)).create_gui())


if __name__ == '__main__':
    main()
