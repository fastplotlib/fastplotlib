from typing import *
from pathlib import Path
from multiprocessing import Queue, Process

import cv2


class VideoWriter(Process):
    def __init__(self, path: Union[Path, str], queue: Queue, fps, dims, fourcc):
        super().__init__()
        self.path = path
        self.queue = queue

        fourcc = cv2.VideoWriter_fourcc(*fourcc)

        self.writer = cv2.VideoWriter(
            str(path),
            fourcc,
            fps,
            dims
        )

    def run(self):
        while True:
            if self.queue.empty():
                continue

            frame = self.queue.get()

            if frame is None:
                self.writer.release()
                return

            self.writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
