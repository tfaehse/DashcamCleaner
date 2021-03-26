import inspect
import sys
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
        self.ui.button_source.clicked.connect(self.button_source_clicked)
        self.ui.button_start.clicked.connect(self.button_start_clicked)
        self.ui.button_target.clicked.connect(self.button_target_clicked)
        self.ui.button_abort.clicked.connect(self.button_abort_clicked)
        self.setup_blurrer()

    def setup_blurrer(self):
        """
        Create and connect a blurrer thread
        """
        self.blurrer = VideoBlurrer()
        self.blurrer.setMaximum.connect(self.setMaximumValue)
        self.blurrer.updateProgress.connect(self.setProgress)
        self.blurrer.finished.connect(self.blurrer_finished)

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
        self.x_min = float(x_min)
        self.y_min = float(y_min)
        self.x_max = float(x_max)
        self.y_max = float(y_max)
        self.score = float(score)
        self.kind = str(kind)

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

    def __init__(self, parameters=None):
        """
        Constructor
        :param parameters: all relevant paremeters for the blurring process
        """
        super(VideoBlurrer, self).__init__()
        self.parameters = parameters
        self.detections = []
        self.detector = setup_detector("weights/yolov5s_weights.pt")
        print("Worker created")

    def apply_blur(self, frame: np.array, new_detections: list):
        """
        Apply Gaussian blur to regions of interests
        :param frame: input image
        :param new_detections: list of newly detected faces and plates
        :return: processed image
        """
        frame_height, frame_width = frame.shape[:2]

        # gather inputs from self.parameters
        blur_size = self.parameters["blur_size"]
        blur_memory = self.parameters["blur_memory"]
        roi_multi = self.parameters["roi_multi"]

        # gather all currently relevant detections
        self.detections = [[x[0], x[1] + 1] for x in self.detections if
                           x[1] <= blur_memory]  # throw out outdated detections, increase age by 1
        for detection in new_detections:
            width = detection.x_max - detection.x_min
            height = detection.y_max - detection.y_min

            # scale detection by ROI multiplier - 2x means a twofold increase in AREA, not circumference
            x_min = detection.x_min - ((sqrt(roi_multi) - 1) * width) / 2
            x_max = detection.x_max + ((sqrt(roi_multi) - 1) * width) / 2
            y_min = detection.y_min - ((sqrt(roi_multi) - 1) * height) / 2
            y_max = detection.y_max + ((sqrt(roi_multi) - 1) * height) / 2

            detection.x_min = max(floor(x_min), 0)
            detection.x_max = min(floor(x_max), frame_width)
            detection.y_min = max(floor(y_min), 0)
            detection.y_max = min(floor(y_max), frame_height)

            self.detections.append([detection, 0])

        for detection in [x[0] for x in self.detections]:
            x_min = detection.x_min
            x_max = detection.x_max
            y_min = detection.y_min
            y_max = detection.y_max
            frame[y_min:y_max, x_min:x_max] = cv2.blur(frame[y_min:y_max, x_min:x_max], (blur_size, blur_size))
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
        profiler.enable()

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
