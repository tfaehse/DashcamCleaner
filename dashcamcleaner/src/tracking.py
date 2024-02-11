import numpy as np
import pandas as pd
from norfair import Detection as TrackerDetection
from norfair import Tracker, Video, draw_tracked_objects
from tqdm import tqdm, trange


class BoxTracker:
    """
    Class to track detections forwards and backwards in time
    """

    def __init__(self, distance_th, fw_hitc, bw_hitc):
        """
        Constructor
        :param distance_th: max. prediction - detection pixel difference
        :param fw_hitc: max. hit counter in forward tracking
        :param bw_hitc: max. hit counter in backward tracking
        """
        self.distance_threshold = distance_th
        self.forward_max_hit_count = fw_hitc
        self.backward_max_hit_count = bw_hitc

    def run_forward_tracking(self, detections: pd.DataFrame, progress_handler: "ProgressHandler"):
        """
        Execute forward tracking
        :param detections: input detections
        :param progress_handler: progress handler object to communicate progress to user
        :return: tracking results
        """
        tracker = Tracker(
            distance_function="euclidean",
            distance_threshold=self.distance_threshold,
            hit_counter_max=self.forward_max_hit_count,
            initialization_delay=0,
        )
        output_objects = []
        progress_handler.init(len=detections["frame"].max(), unit="frames", desc="Running forward tracking...")
        for frame in range(detections["frame"].max()):
            frame_dets = detections.loc[detections["frame"] == frame]
            norfair_detections = [
                TrackerDetection(
                    np.array([[det["x_min"], det["y_min"]], [det["x_max"], det["y_max"]]]), label=det["class"]
                )
                for _, det in frame_dets.iterrows()
            ]
            tracked_objects = tracker.update(norfair_detections)
            output_objects += [
                {
                    "frame": frame,
                    "x_min": int(obs.get_estimate()[0][0]),
                    "y_min": int(obs.get_estimate()[0][1]),
                    "x_max": int(obs.get_estimate()[1][0]),
                    "y_max": int(obs.get_estimate()[1][1]),
                    "class": obs.label,
                }
                for obs in tracked_objects
            ]
            progress_handler.update()
        progress_handler.finish()
        return pd.DataFrame(output_objects)

    def run_backward_tracking(self, tracks: pd.DataFrame, progress_handler: "ProgressHandler"):
        """
        Execute backward tracking
        :param tracks: input tracks
        :param progress_handler: progress handler object to communicate progress to user
        :return: tracking results
        """
        tracker = Tracker(
            distance_function="euclidean",
            distance_threshold=self.distance_threshold,
            hit_counter_max=self.backward_max_hit_count,
            initialization_delay=1,
        )
        output_objects = []
        length = tracks["frame"].max()
        progress_handler.init(len=length, unit="frames", desc="Running backward tracking...")
        for frame in reversed(range(length)):
            frame_dets = tracks.loc[tracks["frame"] == frame]
            norfair_detections = [
                TrackerDetection(
                    np.array([[det["x_min"], det["y_min"]], [det["x_max"], det["y_max"]]]), label=det["class"]
                )
                for _, det in frame_dets.iterrows()
            ]
            tracked_objects = tracker.update(norfair_detections)
            output_objects += [
                {
                    "frame": frame,
                    "x_min": int(obs.get_estimate()[0][0]),
                    "y_min": int(obs.get_estimate()[0][1]),
                    "x_max": int(obs.get_estimate()[1][0]),
                    "y_max": int(obs.get_estimate()[1][1]),
                    "class": obs.label,
                }
                for obs in tracked_objects
            ]
            progress_handler.update()
        progress_handler.finish()
        return pd.DataFrame(output_objects)
