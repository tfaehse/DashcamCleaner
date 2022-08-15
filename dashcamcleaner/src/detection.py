from src.bounds import Bounds


class Detection:
    bounds: Bounds
    score: float
    kind: str
    age: int

    def __init__(self: 'Detection', bounds: Bounds, score: float, kind: str) -> None:
        self.bounds = bounds
        self.score = score
        self.kind = kind
        self.age = 0

    def get_scaled(self: 'Detection', shape, multiplier) -> 'Detection':
        result = Detection(self.bounds.scale(shape, multiplier), self.score, self.kind)
        result.age = self.age
        return result

    def get_older(self: 'Detection') -> 'Detection':
        older_clone = Detection(self.bounds, self.score, self.kind)
        older_clone.age = self.age + 1
        return older_clone

    def __eq__(self: 'Detection', other) -> bool:
        if isinstance(other, Detection):
            return (
                self.bounds == other.bounds
                and self.score == other.score
                and self.kind == other.kind
            )
        return False
