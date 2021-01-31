import inspect
import os
import sys

import cv2
import numpy as np
from PySide2.QtCore import QSettings, QThread, Signal
from PySide2.QtWidgets import QApplication, QMainWindow, QFileDialog
from PySide2.QtWidgets import QSpinBox, QDoubleSpinBox, QLineEdit, QRadioButton, QMessageBox
from ui_mainwindow import Ui_MainWindow

# hack to add Anonymizer submodule to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "anonymizer"))
from anonymizer.anonymization.anonymizer import Anonymizer
from anonymizer.detection.detector import Detector
from anonymizer.detection.weights import download_weights, get_weights_path
from anonymizer.obfuscation.obfuscator import Obfuscator
from math import floor, ceil


class MainWindow(QMainWindow):

    def __init__(self):
        """
        Constructor
        """
        self.receive_attempts = 0
        self.settings = QSettings("gui.ini", QSettings.IniFormat)
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
            "fps": self.ui.spin_fps.value(),
            "custom_blur": self.ui.radio_custom_blur.isChecked(),
            "blur_size": self.ui.spin_blur.value(),
            "blur_memory": self.ui.spin_memory.value(),
            "face_threshold": self.ui.double_spin_face.value(),
            "plate_threshold": self.ui.double_spin_plate.value()
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
        print("Worker created")

    def run(self):
        """
        Run Anonymizer on each frame of the input video
        """

        # gather inputs from self.parameters
        print("Worker started")
        input_path = self.parameters["input_path"]
        output_path = self.parameters["output_path"]
        fps = self.parameters["fps"]
        custom_blur = self.parameters["custom_blur"]
        blur_size = self.parameters["blur_size"]
        blur_memory = self.parameters["blur_memory"]
        face_threshold = self.parameters["face_threshold"]
        plate_threshold = self.parameters["plate_threshold"]

        # prepare Anonymizer parameters
        detection_thresholds = {
            "face": face_threshold,
            "plate": plate_threshold
        }

        # setup anonymizer
        blur_str = "1,0,1"  # no blurring by Anonymizer - performance concerns
        if not custom_blur:
            blur_str = f"{blur_size},0,{int(blur_size / 2)}"
        anonymizer = setup_anonymizer("weights", face_threshold, plate_threshold, blur_str)

        cap = cv2.VideoCapture(input_path)

        # gets the height and width of each frame
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # saves the video to a file
        fourcc = cv2.VideoWriter_fourcc(*'H264')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        self.setMaximum.emit(length)

        # to make video actual speed
        if cap.isOpened() == False:
            print('error file not found')

        # while the video is running the loop will keep running
        current_frame = 0
        detections = []
        while cap.isOpened():
            # returns each frame
            ret, frame = cap.read()

            # if there are still frames keeping showing the video
            if ret == True:
                # apply Anonymizer's magic
                res_frame, new_detections = anonymizer.anonymize_image(image=frame,
                                                                       detection_thresholds=detection_thresholds)
                if custom_blur:
                    detections = [[x[0], x[1] + 1] for x in detections if
                                  x[1] <= blur_memory]  # throw out outdated detections, increase age by 1
                    detections.extend([[x, 0] for x in new_detections])
                    for detection in [x[0] for x in detections]:
                        x_min = floor(detection.y_min)
                        x_max = ceil(detection.y_max)
                        y_min = floor(detection.x_min)
                        y_max = ceil(detection.x_max)
                        frame[x_min:x_max, y_min:y_max] = cv2.blur(frame[x_min:x_max, y_min:y_max],
                                                                   (blur_size, blur_size))
                else:
                    frame = res_frame.astype(np.uint8)
                writer.write(frame)

                # check for abort here!!
            else:
                break
            current_frame += 1
            self.updateProgress.emit(current_frame)

        # stop the video, and gets rid of the window that it opens up
        cap.release()
        writer.release()


def setup_anonymizer(weights_path: str, face_threshold: float, plate_threshold: float, obfuscation_parameters: str):
    """
    Sets up and configures an Anonymizer object
    :param weights_path: directory to Anonymizer's weights
    :param face_threshold: threshold for face detection
    :param plate_threshold: threshold for plate detection
    :param obfuscation_parameters: parameters for Gaussian blur
    :return: Anonymizer object
    """
    download_weights(download_directory=weights_path)

    kernel_size, sigma, box_kernel_size = [int(x) for x in obfuscation_parameters.split(',')]

    # Anonymizer requires uneven kernel sizes
    if (kernel_size % 2) == 0:
        kernel_size += 1
    if (box_kernel_size % 2) == 0:
        box_kernel_size += 1
    print(kernel_size, box_kernel_size)

    obfuscator = Obfuscator(kernel_size=int(kernel_size), sigma=float(sigma), box_kernel_size=int(box_kernel_size))
    detectors = {
        'face': Detector(kind='face', weights_path=get_weights_path(weights_path, kind='face')),
        'plate': Detector(kind='plate', weights_path=get_weights_path(weights_path, kind='plate'))
    }
    return Anonymizer(obfuscator=obfuscator, detectors=detectors)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
