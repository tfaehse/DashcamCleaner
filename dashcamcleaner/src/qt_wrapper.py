from shutil import which
from timeit import default_timer as timer

from PySide6.QtCore import QThread, Signal
from src.blurrer import VideoBlurrer, batch_iter
from src.video_utils import VideoReader, VideoWriter


class qtVideoBlurWrapper(QThread, VideoBlurrer):
    setMaximum = Signal(int)
    updateProgress = Signal(int)
    alert = Signal(str)

    def __init__(self, weights_name, parameters):
        """
        Constructor
        :param weights_name: file name of the weights to be used
        :param parameters: all relevant paremeters for the blurring process
        """
        QThread.__init__(self)
        VideoBlurrer.__init__(self, weights_name, parameters)
        self.elapsed = None
        self._abort = False

    def set_abort(self):
        """
        Set abort flag
        :return:
        """
        self._abort = True

    def reset(self):
        """
        Reset blurrer
        :return:
        """
        self.elapsed = None
        self._abort = False

    def run(self):
        """
        Write a copy of the input video stripped of identifiable information, i.e. faces and license plates
        """

        # reset elapsed time and start timer
        self.elapsed = None
        start = timer()

        # gather inputs from self.parameters
        input_path = self.parameters["input_path"]
        output_path = self.parameters["output_path"]
        threshold = self.parameters["threshold"]
        quality = self.parameters["quality"]
        batch_size = self.parameters["batch_size"]
        stabilize = self.parameters["stabilize"]

        # customize detector
        self.detector.conf = threshold

        # open video file
        with VideoReader(input_path, stabilize) as reader:

            # get the height and width of each frame for future debug outputs on frame
            meta = reader.get_metadata()
            print(meta)

            # save the video to a file
            with VideoWriter(
                output_path, input_path, meta["fps"], meta["width"], meta["height"], quality
            ) as writer:
                # update GUI's progress bar on its maximum frames
                self.setMaximum.emit(meta["frames"])

                current_frame = 0

                for batch in batch_iter(reader, batch_size):
                    if self._abort:
                        writer.set_fail()
                        return

                    # buffer is full - detect information for all images in buffer
                    new_detections = self.detect_identifiable_information(batch)
                    for frame, detections in zip(batch, new_detections):
                        frame = self.apply_blur(frame, detections)
                        writer.write_frame(frame)
                    current_frame += len(batch)
                    self.updateProgress.emit(current_frame)

        # store success and elapsed time
        self.elapsed = timer() - start


def is_installed(name):
    """
    Check whether an executable is available
    """
    return which(name) is not None
