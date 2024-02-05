import multiprocessing as mp
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from shutil import which
from timeit import default_timer as timer

import cv2
import imageio
import pandas as pd
from more_itertools import chunked
from PySide6.QtCore import QThread, Signal
from src.blurrer import VideoBlurrer, blur_helper
from src.tracking import BoxTracker
from src.utils.detection import Detection


class qtVideoBlurWrapper(QThread):
    init = Signal(int, str, str)
    update = Signal(int)
    finish = Signal()

    def __init__(self, progress_handler_cls):
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        QThread.__init__(self)
        self.progress_handler = progress_handler_cls(self.init, self.update, self.finish)
        self.result = {"success": False, "elapsed_time": 0}
        self._abort = False
        self.blurrer = None

    def set_params(self, parameters):
        if not self.blurrer:
            self.blurrer = VideoBlurrer(self.progress_handler, parameters["weights"], parameters)
        self.blurrer.parameters = parameters

    def abort(self):
        """
        Tell the blurrer to (cleanly) exit by processing no further batches
        """
        self.result = {"success": False}
        if self.blurrer:
            self.blurrer.error = "Aborted by user"
            self.blurrer._abort = True

    def run(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """

        # reset success and start timer
        if not self.blurrer:
            self.result = {"success": False}
        self.result["success"] = False
        start = timer()
        self.blurrer.execute_pipeline()
        elapsed = timer() - start
        if not self.blurrer._abort:
            self.result = {"success": True, "elapsed_time": elapsed}
