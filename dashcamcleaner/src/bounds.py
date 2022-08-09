from math import floor, sqrt
from typing import Tuple


class Bounds:
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def __init__(self: 'Bounds', x_min: int, y_min: int, x_max: int, y_max: int):
        self.x_min = int(x_min)
        self.y_min = int(y_min)
        self.x_max = int(x_max)
        self.y_max = int(y_max)

    def coords_as_slices(self):
        """
        Calculate integer slices of the box coordinates
        :return: Slices of box coordinates
        """
        return slice(int(self.y_min), int(self.y_max)), slice(int(self.x_min), int(self.x_max))

    def ellipse_coordinates(self: 'Bounds') -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Calculate elliptic coordinates for the box
        :return: position + radii
        """
        center_pos = (int((self.x_max + self.x_min) / 2), int((self.y_max + self.y_min) / 2))
        axis_length = (int((self.x_max - self.x_min) / 2), int((self.y_max - self.y_min) / 2))
        return center_pos, axis_length

    def pt1(self: 'Bounds') -> Tuple[int, int]:
        return (self.x_max, self.y_max)

    def pt2(self: 'Bounds') -> Tuple[int, int]:
        return (self.x_min, self.y_min)

    def scale(self: 'Bounds', shape, multiplier):
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
        scaled_detection = Bounds(
            max(floor(x_min), 0),
            max(floor(y_min), 0),
            min(floor(x_max), frame_width),
            min(floor(y_max), frame_height),
        )
        return scaled_detection

    def __repr__(self: 'Bounds') -> str:
        return f"Box({self.x_min}, {self.y_min}, {self.x_max}, {self.y_max}, xs={self.x_max-self.x_min}, ys={self.y_max-self.y_min})"

    def __eq__(self: 'Bounds', other):
        if isinstance(other, Bounds):
            return (
                self.x_min == other.x_min
                and self.y_min == other.y_min
                and self.x_max == other.x_max
                and self.y_max == other.y_max
            )
        return False
