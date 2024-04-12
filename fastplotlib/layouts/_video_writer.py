from pathlib import Path
from multiprocessing import Queue, Process


def _get_av():
    try:
        import av
    except ImportError:
        raise ModuleNotFoundError(
            "Recording to video file requires `av`:\n"
            "https://github.com/PyAV-Org/PyAV"
        ) from None
    else:
        return av


class VideoWriterAV(Process):
    """Video writer, uses PyAV in an external process to write frames to disk"""

    def __init__(
        self,
        path: Path | str,
        queue: Queue,
        fps: int,
        width: int,
        height: int,
        codec: str,
        pixel_format: str,
        options: dict = None,
    ):
        super().__init__()
        self.queue = queue

        av = _get_av()
        self.container = av.open(path, mode="w")

        self.stream = self.container.add_stream(codec, rate=fps, options=options)

        # in case libx264, trim last rows and/or column
        # because libx264 doesn't like non-even number width or height
        if width % 2 != 0:
            width -= 1
        if height % 2 != 0:
            height -= 1

        self.stream.width = width
        self.stream.height = height

        self.stream.pix_fmt = pixel_format

    def run(self):
        av = _get_av()
        while True:
            if self.queue.empty():  # no frame to write
                continue

            frame = self.queue.get()

            # recording has ended
            if frame is None:
                self.container.close()
                break

            frame = av.VideoFrame.from_ndarray(
                frame[
                    : self.stream.height, : self.stream.width
                ],  # trim if necessary because of x264
                format="rgb24",
            )

            for packet in self.stream.encode(frame):
                self.container.mux(packet)

        # I don't exactly know what this does, copied from pyav example
        for packet in self.stream.encode():
            self.container.mux(packet)

        # close file
        self.container.close()

        # close process, release resources
        self.close()
