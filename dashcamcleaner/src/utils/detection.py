from src.utils.bounds import Bounds


class Detection:
    bounds: Bounds
    score: float
    kind: str

    def __init__(self: "Detection", bounds: Bounds, score: float, kind: str) -> None:
        self.bounds = bounds
        self.score = float(score)
        self.kind = kind

    @classmethod
    def from_row(cls, row):
        bounds = Bounds((row["x_min"], row["x_max"]), (row["y_min"], row["y_max"]))
        score = row["score"] if "score" in row.keys() else 1.0
        kind = row["class"]
        return cls(bounds, score, kind)

    def get_scaled(self: "Detection", shape, multiplier) -> "Detection":
        result = Detection(self.bounds.scale(shape, multiplier), self.score, self.kind)
        return result

    def __eq__(self: "Detection", other) -> bool:
        if isinstance(other, Detection):
            return self.bounds == other.bounds and self.score == other.score and self.kind == other.kind
        return False

    def dict_format(self):
        return self.bounds.__dict__ | {"score": self.score, "class": self.kind}
