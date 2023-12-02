import multiprocessing as mp
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from shutil import which
from timeit import default_timer as timer

import cv2
import imageio
from more_itertools import chunked
from PySide6.QtCore import QThread, Signal
from src.blurrer import VideoBlurrer, blur_helper


class qtVideoBlurWrapper(VideoBlurrer, QThread):
    setMaximum = Signal(int)
    updateProgress = Signal(int)
    alert = Signal(str)
    status = Signal(str)

    def __init__(self, weights_name, parameters):
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        QThread.__init__(self)
        VideoBlurrer.__init__(self, weights_name, parameters)
        self.result = {"success": False, "elapsed_time": 0}
        self._abort = False

    def abort(self):
        """
        Tell the blurrer to (cleanly) exit by processing no further batches
        """
        self._abort = True

    def run(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """

        # reset success and start timer
        self.result["success"] = False
        start = timer()

        # gather inputs from self.parameters
        input_path = self.parameters["input_path"]
        output_file = Path(self.parameters["output_path"])
        temp_output = output_file.parent / f"{output_file.stem}_copy{output_file.suffix}"
        output_path = self.parameters["output_path"]
        quality = self.parameters["quality"]
        batch_size = self.parameters["batch_size"]
        blur_workers = min(self.parameters["blur_workers"], mp.cpu_count(), batch_size)

        # open video file
        with imageio.get_reader(input_path) as reader:

            # get the height and width of each frame for future debug outputs on frame
            meta = reader.get_meta_data()
            fps = meta["fps"]
            duration = meta["duration"]
            length = int(duration * fps)
            audio_present = "audio_codec" in meta
            blur_executor = ProcessPoolExecutor(blur_workers)

            # save the video to a file
            with imageio.get_writer(
                temp_output, codec="libx264", fps=fps, quality=quality, macro_block_size=None
            ) as writer:

                # update GUI's progress bar on its maximum frames
                self.setMaximum.emit(length)
                current_frame = 0

                for frame_batch in chunked(reader, batch_size):
                    if self._abort:
                        break

                    frame_buffer = [cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB) for frame_read in frame_batch]
                    self.status.emit("Getting detections...")
                    new_detections = self.detect_identifiable_information(frame_buffer)
                    args = [
                        [frame, detections, self.parameters] for frame, detections in zip(frame_buffer, new_detections)
                    ]
                    self.status.emit("Blurring and writing frames...")
                    for frame_blurred in blur_executor.map(blur_helper, args):
                        frame_blurred_rgb = cv2.cvtColor(frame_blurred, cv2.COLOR_BGR2RGB)
                        writer.append_data(frame_blurred_rgb)
                    current_frame += batch_size
                    self.updateProgress.emit(current_frame)
                    self.status.emit("Getting frames...")

        self.status.emit("idle")
        if self._abort:
            self._abort = False
            return

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
