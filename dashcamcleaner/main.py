#!/usr/bin/env python3
import inspect
import re
import sys
import time
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QLineEdit, QMainWindow, QMessageBox, QRadioButton, QSpinBox
)
from src.qt_wrapper import qtVideoBlurWrapper
from src.ui.ui_mainwindow import Ui_MainWindow
from src.utils.progress_handler import QtProgressHandler


class MainWindow(QMainWindow):
    def __init__(self):
        """
        Constructor
        """
        self.receive_attempts = 0
        save_path = Path(__file__).parent / "gui.ini"
        self.settings = QSettings(str(save_path), QSettings.IniFormat)
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.restore()
        self.load_weights_options()
        self.blur_wrapper = qtVideoBlurWrapper(QtProgressHandler)
        self.blur_wrapper.update.connect(self.updateProgress)
        self.blur_wrapper.init.connect(self.initProgress)
        self.blur_wrapper.finish.connect(self.finishProgress)
        self.blur_wrapper.finished.connect(self.blur_wrapper_finished)

        self.ui.button_source.clicked.connect(self.button_source_clicked)
        self.ui.button_start.clicked.connect(self.button_start_clicked)
        self.ui.button_target.clicked.connect(self.button_target_clicked)
        self.ui.button_abort.clicked.connect(self.button_abort_clicked)

    def load_weights_options(self):
        self.ui.combo_box_weights.clear()
        source_folder = Path(__file__).parent / "weights"
        available_weights_files = list(source_folder.rglob("*.pt"))
        assert len(available_weights_files) > 0, "There has to be at least one .pt file in dashcamcleaner/weights"
        for net_path in available_weights_files:
            self.ui.combo_box_weights.addItem(net_path.stem)

    def blur_wrapper_status(self, message: str):
        self.ui.label_status.setText(message)

    def blur_wrapper_alert(self, message: str):
        """
        Display blurrer messages in the GUI
        :param message: Message to be displayed
        """
        msg_box = QMessageBox()
        msg_box.setText(message)
        msg_box.exec()

    def button_abort_clicked(self):
        """
        Callback for button_abort
        """
        self.blur_wrapper.abort()
        self.ui.button_start.setEnabled(True)
        self.ui.button_abort.setEnabled(False)

    def updateProgress(self, value: int):
        """
        Set progress bar's current progress
        :param value: progress to be set
        """
        self.ui.progress.setValue(value)

    def initProgress(self, len: int, unit: str, desc: str):
        """
        Set progress bar's maximum value
        :param value: value to be set
        """
        self.ui.progress.setMaximum(len)
        self.ui.label_status.setText(desc)

    def finishProgress(self):
        self.ui.label_status.setText("idle")
        self.ui.progress.setValue(0)

    def aggregate_parameters(self):
        model_name = self.ui.combo_box_weights.currentText()
        training_inference_size = int(re.search(r"(?P<imgsz>\d*)p\_", model_name).group("imgsz"))
        inference_size = int(training_inference_size * 16 / 9)
        return {
            "input_path": self.ui.line_source.text(),
            "output_path": self.ui.line_target.text(),
            "blur_size": self.ui.spin_blur.value(),
            "threshold": self.ui.double_spin_threshold.value(),
            "roi_multi": self.ui.double_spin_roimulti.value(),
            "inference_size": inference_size,
            "quality": self.ui.spin_quality.value(),
            "batch_size": self.ui.spin_batch.value(),
            "no_faces": False,
            "feather_edges": self.ui.spin_feather_edges.value(),
            "export_mask": False,
            "export_colored_mask": False,
            "blur_workers": self.ui.spin_blur_workers.value(),
            "tracking_memory": self.ui.spin_memory.value(),
            "tracking_dist": self.ui.double_spin_tracking_dist.value(),
            "weights": model_name,
        }

    def button_start_clicked(self):
        """
        Callback for button_start
        """

        self.ui.button_abort.setEnabled(True)
        self.ui.button_start.setEnabled(False)

        # set up parameters
        parameters = self.aggregate_parameters()
        if self.blur_wrapper:
            self.blur_wrapper.set_params(parameters)
            self.blur_wrapper.start()
        else:
            print("No blurrer object!")
        print("Blurrer started!")

    def button_source_clicked(self):
        """
        Callback for button_source
        """
        source_path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mkv *.avi *.mov *.mp4)")
        self.ui.line_source.setText(source_path)

    def button_target_clicked(self):
        """
        Callback for button_target
        """
        target_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "", "Video Files (*.mkv *.mp4 *.mov)")
        self.ui.line_target.setText(target_path)

    def restore(self):
        """
        Restores relevent UI settings from ini file
        """
        for name, obj in inspect.getmembers(self.ui):
            if isinstance(obj, QSpinBox):
                name = obj.objectName()
                value = self.settings.value(name)
                if value:
                    obj.setValue(int(value))

            if isinstance(obj, QDoubleSpinBox):
                name = obj.objectName()
                value = self.settings.value(name)
                if value:
                    obj.setValue(float(value))

            if isinstance(obj, QLineEdit):
                name = obj.objectName()
                value = self.settings.value(name)
                if value:
                    obj.setText(value)

            if isinstance(obj, QRadioButton):
                name = obj.objectName()
                value = self.settings.value(name)
                if value and value == "true":  # ouch...
                    obj.setChecked(True)

            if isinstance(obj, QComboBox):
                name = obj.objectName()
                value = self.settings.value(name)
                if value:
                    index = obj.findText(value)
                    if index == -1:
                        obj.insertItems(0, [value])
                        index = obj.findText(value)
                        obj.setCurrentIndex(index)
                    else:
                        obj.setCurrentIndex(index)

    def blur_wrapper_finished(self):
        """
        Create a new blurrer, setup UI and notify the user
        """
        msg_box = QMessageBox()
        if self.blur_wrapper and self.blur_wrapper.result["success"]:
            minutes = int(self.blur_wrapper.result["elapsed_time"] // 60)
            seconds = round(self.blur_wrapper.result["elapsed_time"] % 60)
            msg_box.setText(f"Video blurred successfully in {minutes} minutes and {seconds} seconds.")
        else:
            msg_box.setText(f"Blurring resulted in errors:\n{self.blur_wrapper.blurrer.error}")
            self.blur_wrapper.blurrer._abort = False
        msg_box.exec()
        self.ui.button_start.setEnabled(True)
        self.ui.button_abort.setEnabled(False)
        self.ui.progress.setValue(0)

    def save(self):
        """
        Save all relevant UI parameters
        """
        for name, obj in inspect.getmembers(self.ui):
            if isinstance(obj, QSpinBox):
                name = obj.objectName()
                value = obj.value()
                self.settings.setValue(name, value)

            if isinstance(obj, QDoubleSpinBox):
                name = obj.objectName()
                value = obj.value()
                self.settings.setValue(name, value)

            if isinstance(obj, QLineEdit):
                name = obj.objectName()
                value = obj.text()
                self.settings.setValue(name, value)

            if isinstance(obj, QRadioButton):
                name = obj.objectName()
                value = obj.isChecked()
                self.settings.setValue(name, value)

            if isinstance(obj, QComboBox):
                index = obj.currentIndex()  # get current index from combobox
                value = obj.itemText(index)
                self.settings.setValue(name, value)

    def closeEvent(self, event):
        """
        Overload closeEvent to shut down blurrer and save UI settings
        :param event:
        """
        self.blur_wrapper.abort()
        self.save()
        print("saved settings")
        while self.blur_wrapper.isRunning():
            time.sleep(1)
        QMainWindow.closeEvent(self, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
