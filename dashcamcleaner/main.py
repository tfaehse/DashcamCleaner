import inspect
import os
import sys
from glob import glob
from math import floor, ceil, sqrt

import cv2
import numpy as np
import torch
from PySide2.QtCore import QSettings, QThread, Signal
from PySide2.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide2.QtWidgets import QSpinBox, QDoubleSpinBox, QLineEdit, QRadioButton, QMessageBox

from ui_mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):

    def __init__(self):
        """
        Constructor
        """
        self.receive_attempts = 0
        self.settings = QSettings("gui.ini", QSettings.IniFormat)
        self.blurrer = None
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.restore()
        self.load_weights_options()
        self.ui.button_source.clicked.connect(self.button_source_clicked)
        self.ui.button_start.clicked.connect(self.button_start_clicked)
        self.ui.button_target.clicked.connect(self.button_target_clicked)
        self.ui.button_abort.clicked.connect(self.button_abort_clicked)
        self.ui.combo_box_weights.currentIndexChanged.connect(self.setup_blurrer)

    def load_weights_options(self):
        for net_path in glob(f"./weights/*.pt"):
            clean_name = os.path.splitext(os.path.basename(net_path))[0]
            self.ui.combo_box_weights.addItem(clean_name)
        self.setup_blurrer()

    def setup_blurrer(self):
        """
        Create and connect a blurrer thread
        """
        weights_name = self.ui.combo_box_weights.currentText()
        self.blurrer = VideoBlurrer(weights_name)
        self.blurrer.setMaximum.connect(self.setMaximumValue)
        self.blurrer.updateProgress.connect(self.setProgress)
        self.blurrer.finished.connect(self.blurrer_finished)
        msg_box = QMessageBox()
        msg_box.setText(f"Successfully loaded {weights_name}.pt")
        msg_box.exec_()

    def button_abort_clicked(self):
        """
        Callback for button_abort
        """
        self.force_blurrer_quit()
        self.ui.progress.setValue(0)
        self.ui.button_start.setEnabled(True)
        self.ui.button_abort.setEnabled(False)
        self.setup_blurrer()

    def setProgress(self, value: int):
        """
        Set progress bar's current progress
        :param value: progress to be set
        """
        self.ui.progress.setValue(value)

    def setMaximumValue(self, value: int):
        """
        Set progress bar's maximum value
        :param value: value to be set
        """
        self.ui.progress.setMaximum(value)

    def button_start_clicked(self):
        """
        Callback for button_start
        """

        self.ui.button_abort.setEnabled(True)
        self.ui.button_start.setEnabled(False)

        # set up parameters
        parameters = {
            "input_path": self.ui.line_source.text(),
            "output_path": self.ui.line_target.text(),
            "weights_path": "weights/yolov5s_weights.pt",
            "blur_size": self.ui.spin_blur.value(),
            "blur_memory": self.ui.spin_memory.value(),
            "threshold": self.ui.double_spin_threshold.value(),
            "roi_multi": self.ui.double_spin_roimulti.value(),
            "inference_scale": self.ui.double_spin_size.value()
        }
        if self.blurrer:
            self.blurrer.parameters = parameters
            self.blurrer.start()
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
        target_path, _ = QFileDialog.getSaveFileName(self, "Save Video", "", "Video Files (*.mkv)")
        self.ui.line_target.setText(target_path)

    def force_blurrer_quit(self):
        """
        Force blurrer thread to quit
        """
        if self.blurrer.isRunning():
            self.blurrer.terminate()
            self.blurrer.wait()

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

    def blurrer_finished(self):
        """
        Create a new blurrer, setup UI and notify the user
        """
        msg_box = QMessageBox()
        msg_box.setText("Blurrer terminated.")
        msg_box.exec_()
        if not self.blurrer:
            self.setup_blurrer()
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

    def closeEvent(self, event):
        """
        Overload closeEvent to shut down blurrer and save UI settings
        :param event:
        """
        self.force_blurrer_quit()
        self.save()
        print("saved settings")
        QMainWindow.closeEvent(self, event)


class Box:
    def __init__(self, x_min, y_min, x_max, y_max, score, kind):
        self.x_min = int(x_min)
        self.y_min = int(y_min)
        self.x_max = int(x_max)
        self.y_max = int(y_max)
        self.score = float(score)
        self.kind = str(kind)

    def coords_as_slices(self):
        """
        Calculate integer slices of the box coordinates
        :return: Slices of box coordinates
        """
        return slice(int(self.y_min), int(self.y_max)), slice(int(self.x_min), int(self.x_max))

    def scale(self, shape, multiplier):
        """
        Scales a bounding box by a size multiplier and while respecting image dimensions
        :param shape: shape of the image
        :param multiplier: multiplier to scale the detection with
        :return: scaled Boxs
        """
        frame_height, frame_width = shape[:2]

        width = self.x_max - self.x_min
        height = self.y_max - self.y_min

        # scale detection by ROI multiplier - 2x means a twofold increase in AREA, not circumference
        x_min = self.x_min - ((sqrt(multiplier) - 1) * width) / 2
        x_max = self.x_max + ((sqrt(multiplier) - 1) * width) / 2
        y_min = self.y_min - ((sqrt(multiplier) - 1) * height) / 2
        y_max = self.y_max + ((sqrt(multiplier) - 1) * height) / 2
        scaled_detection = Box(max(floor(x_min), 0), max(floor(y_min), 0), min(floor(x_max), frame_width),
                               min(floor(y_max), frame_height), self.score, self.kind)
        return scaled_detection

    def __repr__(self):
        return f'Box({self.x_min}, {self.y_min}, {self.x_max}, {self.y_max}, {self.score}, {self.kind})'

    def __eq__(self, other):
        if isinstance(other, Box):
            return (self.x_min == other.x_min and self.y_min == other.y_min and
                    self.x_max == other.x_max and self.y_max == other.y_max and
                    self.score == other.score and self.kind == other.kind)
        return False


class VideoBlurrer(QThread):
    setMaximum = Signal(int)
    updateProgress = Signal(int)

    def __init__(self, weights_name, parameters=None):
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        super(VideoBlurrer, self).__init__()
        self.parameters = parameters
        self.detections = []
        weights_path = os.path.join("weights", f"{weights_name}.pt")
        self.detector = setup_detector(weights_path)
        print("Worker created")

    def apply_blur(self, frame: np.array, new_detections: list):
        """
        Apply Gaussian blur to regions of interests
        :param frame: input image
        :param new_detections: list of newly detected faces and plates
        :return: processed image
        """
        # gather inputs from self.parameters
        blur_size = self.parameters["blur_size"]
        blur_memory = self.parameters["blur_memory"]
        roi_multi = self.parameters["roi_multi"]

        # gather and process all currently relevant detections
        self.detections = [[x[0], x[1] + 1] for x in self.detections if
                           x[1] <= blur_memory]  # throw out outdated detections, increase age by 1
        for detection in new_detections:
            scaled_detection = detection.scale(frame.shape, roi_multi)
            self.detections.append([scaled_detection, 0])

        for detection in [x[0] for x in self.detections]:
            # two-fold blurring: softer blur on the edge of the box to look smoother and less abrupt
            outer_box = detection
            inner_box = detection.scale(frame.shape, 0.8)
            frame[outer_box.coords_as_slices()] = cv2.blur(
                frame[outer_box.coords_as_slices()], (blur_size, blur_size))
            frame[inner_box.coords_as_slices()] = cv2.blur(
                frame[inner_box.coords_as_slices()],
                (blur_size * 2 + 1, blur_size * 2 + 1))
        return frame

    def detect_identifiable_information(self, image: np.array):
        """
        Run plate and face detection on an input image
        :param image: input image
        :return: detected faces and plates
        """
        scale = ceil(image.shape[1] * self.parameters[
            "inference_scale"] / self.detector.stride.max()) * self.detector.stride.max()
        results = self.detector(image, size=scale.item())
        boxes = []
        for res in results.xyxy[0]:
            boxes.append(Box(res[0].item(), res[1].item(), res[2].item(), res[3].item(), res[4].item(), res[5].item()))
        return boxes

    def run(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """

        # gather inputs from self.parameters
        print("Worker started")
        input_path = self.parameters["input_path"]
        output_path = self.parameters["output_path"]
        threshold = self.parameters["threshold"]

        # customize detector
        self.detector.conf = threshold

        # open video file
        cap = cv2.VideoCapture(input_path)

        # get the height and width of each frame
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # save the video to a file
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # update GUI's progress bar on its maximum frames
        self.setMaximum.emit(length)

        if cap.isOpened() == False:
            print('error file not found')
            return

        # loop through video
        current_frame = 0
        while cap.isOpened():
            ret, frame = cap.read()

            if ret == True:
                new_detections = self.detect_identifiable_information(frame.copy())
                frame = self.apply_blur(frame, new_detections)
                writer.write(frame)

            else:
                break

            current_frame += 1
            self.updateProgress.emit(current_frame)

        self.detections = []
        cap.release()
        writer.release()


def setup_detector(weights_path: str):
    """
    Load YOLOv5 detector from torch hub and update the detector with this repo's weights
    :param weights_path: path to .pt file with this repo's weights
    :return: initialized yolov5 detector
    """
    model = torch.hub.load('ultralytics/yolov5', 'custom', weights_path)
    if torch.cuda.is_available():
        print(f"Using {torch.cuda.get_device_name(torch.cuda.current_device())}.")
        torch.backends.cudnn.benchmark = True
        model.cuda()
    else:
        print("Using CPU.")
    return model


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
