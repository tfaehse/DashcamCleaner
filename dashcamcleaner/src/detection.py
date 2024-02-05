from src.bounds import Bounds


class Detection:
    bounds: Bounds
    score: float
    kind: str

    def __init__(self: "Detection", bounds: Bounds, score: float, kind: str) -> None:
        self.bounds = bounds
        self.score = float(score)
        self.kind = kind

    def get_scaled(self: "Detection", shape, multiplier) -> "Detection":
        result = Detection(self.bounds.scale(shape, multiplier), self.score, self.kind)
        return result

    def __eq__(self: "Detection", other) -> bool:
        if isinstance(other, Detection):
            return self.bounds == other.bounds and self.score == other.score and self.kind == other.kind
        return False
