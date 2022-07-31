import os
import subprocess
from timeit import default_timer as timer

import cv2
import imageio
import numpy as np
from PySide6.QtCore import QThread, Signal
from src.blurrer import VideoBlurrer
from shutil import which


class qtVideoBlurWrapper(QThread):
    setMaximum = Signal(int)
    updateProgress = Signal(int)
    alert = Signal(str)

    def __init__(self, weights_name, parameters=None):
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        super(qtVideoBlurWrapper, self).__init__()
        self.blurrer = VideoBlurrer(weights_name, parameters)
        self.result = {"success": False, "elapsed_time": 0}

    def apply_blur(self, frame: np.array, new_detections: list):
        """
        Apply Gaussian blur to regions of interests
        :param frame: input image
        :param new_detections: list of newly detected faces and plates
        :return: processed image
        """
        return self.blurrer.apply_blur(frame, new_detections)

    def detect_identifiable_information(self, image: np.array):
        """
        Run plate and face detection on an input image
        :param image: input image
        :return: detected faces and plates
        """
        return self.blurrer.detect_identifiable_information(image)

    def run(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """

        # reset success and start timer
        self.result["success"] = False
        start = timer()

        # gather inputs from self.parameters
        input_path = self.blurrer.parameters["input_path"]
        temp_output = f"{os.path.splitext(self.blurrer.parameters['output_path'])[0]}_copy{os.path.splitext(self.blurrer.parameters['output_path'])[1]}"
        output_path = self.blurrer.parameters["output_path"]
        threshold = self.blurrer.parameters["threshold"]
        quality = self.blurrer.parameters["quality"]
        batch_size = self.blurrer.parameters["batch_size"]

        # customize detector
        self.blurrer.detector.conf = threshold

        # open video file
        with imageio.get_reader(input_path) as reader:

            # get the height and width of each frame for future debug outputs on frame
            meta = reader.get_meta_data()
            fps = meta["fps"]
            duration = meta["duration"]
            length = int(duration * fps)
            audio_present = "audio_codec" in meta

            # save the video to a file
            with imageio.get_writer(
                temp_output, codec="libx264", fps=fps, quality=quality
            ) as writer:

                # update GUI's progress bar on its maximum frames
                self.setMaximum.emit(length)

                buffer = []
                current_frame = 0

                for frame_read in reader:
                    rgb_frame = cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB)
                    if len(buffer) < batch_size:
                        buffer.append(rgb_frame)
                    else:
                        # buffer is full - detect information for all images in buffer
                        new_detections = self.detect_identifiable_information(buffer)
                        for frame, detections in zip(buffer, new_detections):
                            frame = self.apply_blur(frame, detections)
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            writer.append_data(frame_rgb)
                        current_frame += len(buffer)
                        self.updateProgress.emit(current_frame)
                        buffer = [rgb_frame]

                # Detect information for the rest of the buffer
                new_detections = self.detect_identifiable_information(buffer)
                for frame, detections in zip(buffer, new_detections):
                    frame = self.apply_blur(frame, detections)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    writer.append_data(frame_rgb)
                current_frame += len(buffer)
                self.updateProgress.emit(current_frame)

        # copy over audio stream from original video to edited video
        if is_installed("ffmpeg"):
            ffmpeg_exe = "ffmpeg"
        else:
            ffmpeg_exe = os.getenv("FFMPEG_BINARY")
            if not ffmpeg_exe:
                self.alert.emit(
                    "FFMPEG could not be found! Please make sure the ffmpeg.exe is available under the envirnment variable 'FFMPEG_BINARY'."
                )
                return
        if audio_present:
            subprocess.run(
                [
                    ffmpeg_exe,
                    "-y",
                    "-i",
                    temp_output,
                    "-i",
                    input_path,
                    "-c",
                    "copy",
                    "-map",
                    "0:0",
                    "-map",
                    "1:1",
                    "-shortest",
                    output_path,
                ],
                stdout=subprocess.DEVNULL,
            )
            # delete temporary output that had no audio track
            try:
                os.remove(temp_output)
            except Exception as e:
                self.alert.emit(
                    f"Could not delete temporary, muted video. Maybe another process (like a cloud storage service or antivirus) is using it already.\n{str(e)}"
                )
        else:
            os.rename(temp_output, output_path)

        # store success and elapsed time
        self.result["success"] = True
        self.result["elapsed_time"] = timer() - start


def is_installed(name):
    """
    Check whether an executable is available
    """
    return which(name) is not None
