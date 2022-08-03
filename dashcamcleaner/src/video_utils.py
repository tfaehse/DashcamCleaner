"""Video read/write functionality with context managers"""

from datetime import datetime, timedelta
from fractions import Fraction

import av
from vidstab.VidStab import VidStab


class VideoWriter:
    def __init__(self, output_path, audio_path, fps, width, height, quality):
        """
        Initialize a video writer and its respective streams
        :param output_path: path to output video file
        :param audio_path: path to an existing video whose audio should be used
        :param fps: output video framerate
        :param width: output video frame width
        :param height: output video frame height
        :param quality: output video quality [0...10], higher = better
        """
        crf = int((1.0 - quality / 10.0) * 51.0)
        self.output = av.open(output_path, "w")
        self.video_stream = self.output.add_stream(
            "libx264rgb", Fraction(fps).limit_denominator(65535), options={"crf": str(crf)}
        )
        self.video_stream.thread_type = "AUTO"
        self.video_stream.pix_fmt = "rgb24"
        self.video_stream.width = width
        self.video_stream.height = height
        self.input = av.open(audio_path, "r")
        if self.input.streams.audio:
            self.audio = self.input.streams.audio[0]
            try:
                self.output.add_stream(template=self.audio)
            except ValueError:
                print("Cannot copy over audio. Sorry?")
                self.audio = None
        else:
            self.audio = None
        self._fail = False

    def __enter__(self):
        """
        Context manager entry
        :return: context manager
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: close streams
        :param exc_type: exception type
        :param exc_val: exception value
        :param exc_tb: exception traceback
        :return:
        """
        if not self._fail:
            self.output.mux(self.video_stream.encode())
            self.write_audio()
            self.output.close()
        self.input.close()

    def set_fail(self):
        """
        In case of failure, output is invalid -> no need to add audio
        :return:
        """
        self._fail = True

    def write_audio(self):
        """
        Write audio from input file to output file
        :return:
        """
        if self.audio:
            for packet in self.input.demux((self.audio,)):
                if packet.dts is None:
                    continue
                packet.stream = self.audio
                self.output.mux(packet)

    def write_frame(self, frame):
        """
        Write a single video frame to the output file
        :param frame: frame to be added to output video
        :return:
        """
        video_frame = av.VideoFrame.from_ndarray(frame)
        for packet in self.video_stream.encode(video_frame):
            self.output.mux(packet)

    def close(self):
        """
        Close streams
        :return:
        """
        self.write_audio()
        self.output.mux(self.video_stream.encode())
        self.output.close()


class VideoReader:
    def __init__(self, input_path, stabilize):
        """
        Initialize a video reader and its respective streams
        :param input_path: path to input video
        :param stabilize: stabilize input video
        """
        self.input_video = av.open(input_path)
        self.stream = self.input_video.streams.video[0]
        self.stream.thread_type = "AUTO"
        if stabilize:
            self.stabilizer = VidStab()
        else:
            self.stabilizer = None

    def __enter__(self):
        """
        Context manager entry
        :return: context manager
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit: close stream
        :param exc_type: exception type
        :param exc_val: exception value
        :param exc_tb: exception traceback
        :return:
        """
        self.input_video.close()

    def __iter__(self):
        """
        Iterator over input stream frames
        :return: iterator
        """
        for frame in self.input_video.decode(self.stream):
            frame = frame.to_ndarray(format="rgb24")
            if self.stabilizer:
                stabilized_frame = self.stabilizer.stabilize_frame(
                    input_frame=frame, smoothing_window=30
                )
                yield stabilized_frame if stabilized_frame.any() else frame
            else:
                yield frame

    def get_metadata(self):
        """
        Get metadata of input video file

        Note: the frames attribute is read directly only if it's actually set. If not,
        it is approximated using framerate and duration of the vide.
        :return: dictionary with metadata of input video
        """
        if self.stream.frames > 0:
            frames = self.stream.frames
        elif self.stream.duration is not None:
            frames = int(self.stream.duration * self.stream.guessed_rate)
        elif "DURATION" in self.stream.metadata:
            try:
                dt = datetime.strptime(self.stream.metadata["DURATION"][:-3], "%H:%M:%S.%f")
                duration = timedelta(
                    hours=dt.hour,
                    minutes=dt.minute,
                    seconds=dt.second,
                    milliseconds=dt.microsecond / 1000,
                ).total_seconds()
                frames = int(duration * self.stream.guessed_rate)
            except ValueError:
                try:
                    dt = datetime.strptime(self.stream.metadata["DURATION"][:-3], "%H:%M:%S,%f")
                    duration = timedelta(
                        hours=dt.hour,
                        minutes=dt.minute,
                        seconds=dt.second,
                        milliseconds=dt.microsecond / 1000,
                    ).total_seconds()
                    frames = int(duration * self.stream.guessed_rate)
                except ValueError:
                    frames = None
        else:
            frames = None
        return {
            "fps": float(self.stream.guessed_rate),
            "frames": frames,
            "width": self.stream.width,
            "height": self.stream.height,
        }

    def close(self):
        """
        Close stream
        :return:
        """
        self.input_video.close()
