from tqdm import tqdm


class ProgressHandler:
    def init(self, len, unit, desc):
        pass

    def update(self, increment=1):
        pass

    def finish(self):
        pass


# CLI Progress Handler
class CLIProgressHandler(ProgressHandler):
    def __init__(self):
        self.progress = None

    def init(self, len, unit, desc):
        self.progress = tqdm(total=len, desc=desc, unit=unit)

    def update(self, increment=1):
        self.progress.update(increment)

    def finish(self):
        self.progress.close()


# GUI Progress Handler
class QtProgressHandler(ProgressHandler):
    def __init__(self, init_signal, update_signal, finish_signal):
        self.init_signal = init_signal
        self.update_signal = update_signal
        self.finish_signal = finish_signal
        self.len = 0
        self.current = 0

    def init(self, len, unit, desc):
        self.len = len
        self.current = 0
        self.init_signal.emit(len, unit, desc)  # Initialize progress bar in GUI

    def update(self, increment=1):
        self.current += increment
        self.update_signal.emit(self.current)

    def finish(self):
        self.finish_signal.emit()
