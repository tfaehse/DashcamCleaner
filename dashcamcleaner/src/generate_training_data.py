import os
import random
import sys
from argparse import ArgumentParser
from glob import glob
from math import floor, sqrt

import cv2
import pandas as pd
from anonymizer.anonymization.anonymizer import Anonymizer
from anonymizer.detection.detector import Detector
from anonymizer.detection.weights import download_weights, get_weights_path
from anonymizer.obfuscation.obfuscator import Obfuscator
from pascal_voc_writer import Writer
from tqdm import tqdm

# hack to add Anonymizer submodule to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "anonymizer"))


def setup_anonymizer(weights_path: str, obfuscation_parameters: str):
    """
    Sets up and configures an Anonymizer object
    :param weights_path: directory to Anonymizer's weights
    :param obfuscation_parameters: parameters for Gaussian blur
    :return: Anonymizer object
    """
    download_weights(download_directory=weights_path)
    kernel_size, sigma, box_kernel_size = [int(x) for x in obfuscation_parameters.split(",")]
    # Anonymizer requires uneven kernel size
    if (kernel_size % 2) == 0:
        kernel_size += 1

    if (box_kernel_size % 2) == 0:
        box_kernel_size += 1

    obfuscator = Obfuscator(
        kernel_size=int(kernel_size), sigma=float(sigma), box_kernel_size=int(box_kernel_size)
    )
    detectors = {
        "face": Detector(kind="face", weights_path=get_weights_path(weights_path, kind="face")),
        "plate": Detector(kind="plate", weights_path=get_weights_path(weights_path, kind="plate")),
    }
    return Anonymizer(obfuscator=obfuscator, detectors=detectors)


class TrainingDataGenerator:
    """
    Generate training data for license plate and face detectors from raw video footage
    """

    def __init__(self, folder_path: str, skip_frames: int = 10):
        """
        Initializer
        :param folder_path:
        :param skip_frames:
        """
        self.anonymizer = setup_anonymizer("weights", "1,0,1")
        self.folder = folder_path
        self.skip_frames = skip_frames

    def batch_processing(self, input_folder, image_folder, label_folder, train_split, label_format):
        """
        Batch process a folder of videos
        :param image_folder: final image folder name
        :param label_folder: final label folder name
        :param train_split: train ratio (0,1)
        :param label_format: format for class labels
        :return:
        """
        videos = glob(input_folder + "/*.m*")
        pictures = glob(input_folder + "/**/*.jpg", recursive=True)
        num_videos = len(videos)
        num_pictures = len(pictures)
        randomized_videos = random.sample(videos, num_videos)
        randomized_pictures = random.sample(pictures, num_pictures)
        train_videos = floor(train_split * num_videos)
        train_pictures = floor(train_split * num_pictures)

        if label_format == "yolo":
            # create necessary output folders
            for folder in [image_folder, label_folder]:
                for training_set in ["train", "val"]:
                    os.makedirs(os.path.join(pic_out, folder, training_set), exist_ok=True)

        # train pictures
        self.labeled_data_from_pictures(randomized_pictures[:train_pictures], label_format, "train")

        # validate pictures
        self.labeled_data_from_pictures(randomized_pictures[train_pictures:], label_format, "val")

        # train videos
        for index, vid in enumerate(
            tqdm(randomized_videos[:train_videos], desc="Processing training video file")
        ):
            self.labeled_data_from_video(vid, index, label_format, "train")

        # validate videos
        for index, vid in enumerate(
            tqdm(randomized_videos[train_videos:], desc="Processing validation video file")
        ):
            self.labeled_data_from_video(vid, index, label_format, "val")

    def labeled_data_from_video(
        self, video_path: str, vid_num: int, label_format, folder_suffix, roi_multi=1.2
    ):
        """
        Extract frames and labels from a video
        :param video_path: path to video
        :param vid_num: number of video, used to create unique file names
        :param label_format: format for class labels
        :param folder_suffix: last level folder name, e.g. train or val
        :param roi_multi: multiplier for region of interest size
        :return:
        """
        cap = cv2.VideoCapture(video_path)

        # gets the height and width of each frame
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        boxes = []
        detection_thresholds = {"face": 0.3, "plate": 0.2}

        if cap.isOpened() is False:
            print("error file not found")
            return

        counter = 0
        progress = tqdm(total=length)
        while cap.isOpened():
            # returns each frame
            ret, frame = cap.read()
            if ret is True:
                # skip frames to avoid too similar frames
                if counter % (self.skip_frames) == 0:
                    _, new_detections = self.anonymizer.anonymize_image(frame, detection_thresholds)
                    file_name = f"vid{vid_num}frame{counter}.jpg"
                    path_name = f"{self.folder}/images/{folder_suffix}/{file_name}"
                    for detection in new_detections:
                        width = detection.x_max - detection.x_min
                        height = detection.y_max - detection.y_min

                        # scale detection by ROI multiplier - 2x means a twofold increase in AREA, not circumference
                        detection.x_min -= ((sqrt(roi_multi) - 1) * width) / 2
                        detection.x_max += ((sqrt(roi_multi) - 1) * width) / 2
                        detection.y_min -= ((sqrt(roi_multi) - 1) * height) / 2
                        detection.y_max += ((sqrt(roi_multi) - 1) * height) / 2

                        x_min = max(detection.y_min, 0)
                        x_max = min(detection.y_max, frame_height)
                        y_min = max(detection.x_min, 0)
                        y_max = min(detection.x_max, frame_width)

                        # save frame to folder
                        boxes.append(
                            {
                                "name": file_name,
                                "type": detection.kind,
                                "xmin": x_min,
                                "xmax": x_max,
                                "ymin": y_min,
                                "ymax": y_max,
                                "width": frame_width,
                                "height": frame_height,
                            }
                        )
                    cv2.imwrite(path_name, frame)
            else:
                break
            counter += 1
            progress.update(1)
        progress.close()
        cap.release()
        df = pd.DataFrame(boxes)

        if not df.empty:
            if label_format == "yolo":
                # convert to YOLO label format
                df["y_center"] = (df["xmin"] + df["xmax"]) / 2 / df["height"]
                df["x_center"] = (df["ymax"] + df["ymin"]) / 2 / df["width"]
                df["box_width"] = (df["ymax"] - df["ymin"]) / df["width"]
                df["box_height"] = (df["xmax"] - df["xmin"]) / df["height"]
                df.loc[df["type"] == "face", "yolo_class"] = 1
                df.loc[df["type"] == "plate", "yolo_class"] = 0
                df["yolo_class"] = df["yolo_class"].astype("int8")
                # df.to_csv(f"{self.folder}/labels.csv", index=False)
                df.apply(lambda x: write_yolo(x, self.folder, folder_suffix), axis=1)
            elif label_format == "voc":
                for name, group in df.groupby("name"):
                    width = group.iloc[0]["width"]
                    height = group.iloc[0]["height"]
                    writer = Writer(os.path.basename(name), width, height)
                    for _, row in group.iterrows():
                        writer.addObject(
                            row["type"], row["xmin"], row["ymin"], row["xmax"], row["ymax"]
                        )
                    writer.save(os.path.splitext(name)[0] + ".xml")
            elif label_format == "torch":
                class_dict = {"plate": 0, "face": 1}
                df["class"] = df["type"].apply(lambda x: class_dict[x])
                df.to_csv("labels.csv")
            else:
                raise AttributeError(f"Label format {label_format} is not supported!")
        else:
            print("This video seems to contain no faces or plates whatsoever!")

    def labeled_data_from_pictures(
        self, picture_paths: str, label_format: str, folder_suffix: str, roi_multi=1.2
    ):
        """
        Extract frames and labels from a video
        :param picture_paths: paths to image files
        :param label_format: format for class labels
        :param folder_suffix: last level folder name, e.g. train or val
        :param roi_multi: multiplier for region of interest size
        :return:
        """
        boxes = []
        detection_thresholds = {"face": 0.3, "plate": 0.2}

        counter = 0
        for pic_path in tqdm(picture_paths, desc=f"Processing {folder_suffix} image files"):
            frame = cv2.imread(pic_path)
            frame_height, frame_width = frame.shape[:2]
            _, new_detections = self.anonymizer.anonymize_image(frame, detection_thresholds)
            file_name = f"image{counter}.jpg"
            path_name = f"{self.folder}/images/{folder_suffix}/{file_name}"
            for detection in new_detections:
                width = detection.x_max - detection.x_min
                height = detection.y_max - detection.y_min

                # scale detection by ROI multiplier - 2x means a twofold increase in AREA, not circumference
                detection.x_min -= ((sqrt(roi_multi) - 1) * width) / 2
                detection.x_max += ((sqrt(roi_multi) - 1) * width) / 2
                detection.y_min -= ((sqrt(roi_multi) - 1) * height) / 2
                detection.y_max += ((sqrt(roi_multi) - 1) * height) / 2

                x_min = max(detection.y_min, 0)
                x_max = min(detection.y_max, frame_height)
                y_min = max(detection.x_min, 0)
                y_max = min(detection.x_max, frame_width)

                # save frame to folder
                boxes.append(
                    {
                        "name": file_name,
                        "type": detection.kind,
                        "xmin": x_min,
                        "xmax": x_max,
                        "ymin": y_min,
                        "ymax": y_max,
                        "width": frame_width,
                        "height": frame_height,
                    }
                )
            if len(new_detections) > 0:
                cv2.imwrite(path_name, frame)
            counter += 1
        df = pd.DataFrame(boxes)

        if not df.empty:
            if label_format == "yolo":
                # convert to YOLO label format
                df["y_center"] = (df["xmin"] + df["xmax"]) / 2 / df["height"]
                df["x_center"] = (df["ymax"] + df["ymin"]) / 2 / df["width"]
                df["box_width"] = (df["ymax"] - df["ymin"]) / df["width"]
                df["box_height"] = (df["xmax"] - df["xmin"]) / df["height"]
                df.loc[df["type"] == "face", "yolo_class"] = 1
                df.loc[df["type"] == "plate", "yolo_class"] = 0
                df["yolo_class"] = df["yolo_class"].astype("int8")
                # df.to_csv(f"{self.folder}/labels.csv", index=False)
                df.apply(lambda x: write_yolo(x, self.folder, folder_suffix), axis=1)
            elif label_format == "voc":
                for name, group in df.groupby("name"):
                    width = group.iloc[0]["width"]
                    height = group.iloc[0]["height"]
                    writer = Writer(os.path.basename(name), width, height)
                    for _, row in group.iterrows():
                        writer.addObject(
                            row["type"], row["xmin"], row["ymin"], row["xmax"], row["ymax"]
                        )
                    writer.save(os.path.splitext(name)[0] + ".xml")
            elif label_format == "torch":
                class_dict = {"plate": 0, "face": 1}
                df["class"] = df["type"].apply(lambda x: class_dict[x])
                df.to_csv("labels.csv")
            else:
                raise AttributeError(f"Label format {label_format} is not supported!")
        else:
            print("This folder seems to contain no images with faces or plates whatsoever!")


def write_yolo(row: pd.Series, folder_path: str, folder_suffix: str):
    """
    Appends a row of YOLO labels to a text file
    :param row: label data
    :param folder_path: path to dataset folder
    :param folder_suffix: folder name for current set, e.g. train or val
    :return:
    """
    file_name = os.path.splitext(row["name"])[0] + ".txt"
    with open(os.path.join(folder_path, "labels", folder_suffix, file_name), "a") as f:
        f.write(
            f"""{row["yolo_class"]} {row["x_center"]} {row["y_center"]} {row["box_width"]} {row["box_height"]} \n"""
        )


def parse_args():
    """
    Parse CLI arguments for this script
    :return:
    """
    parser = ArgumentParser()
    parser.add_argument("input", type=str, help="input folder containing video and jpg files")
    parser.add_argument("output", type=str, help="output folder for labeled training images")
    parser.add_argument("labelformat", type=str, help="label format - yolo, voc or torch")
    parser.add_argument(
        "skipframes",
        type=int,
        help="for each analyzed image, skip n frames - to avoid too similar frames",
    )
    parser.add_argument("trainsplit", type=float, help="training split of all data")
    args = parser.parse_args()
    return args.input, args.output, args.labelformat, args.skipframes, args.trainsplit


if __name__ == "__main__":
    input_folder, pic_out, label_format, skip_frames, train_split = parse_args()
    gen = TrainingDataGenerator(pic_out, skip_frames)
    gen.batch_processing(input_folder, "images", "labels", train_split, label_format)
