from datetime import datetime
from fractions import Fraction
from pathlib import Path
from queue import Queue
from threading import Thread
from time import perf_counter

import numpy as np

try:
    import av
except ImportError:
    av = None


# timestamps are stored in milliseconds, frames are written with a variable frame rate
TIME_BASE = Fraction(1, 1000)


class VideoWriter:
    def __init__(
        self,
        path: str | Path = None,
        directory: str | Path = None,
        codec: str = "libx264",
        pixel_format: str = "yuv420p",
        options: dict = None,
    ):
        """
        Writes frames to a video file using PyAV. Encoding happens in a background thread so
        that rendering is not blocked. A new instance is created for every recording.

        Parameters
        ----------
        path: str or Path, optional
            output file, default is ``fastplotlib_<date>_<time>.mp4`` in the current working directory

        codec: str, default "libx264"
            video codec

        pixel_format: str, default "yuv420p"
            pixel format of the encoded video, "yuv420p" is supported by most video players

        options: dict, optional
            codec options passed to PyAV, for example ``{"crf": "18"}``

        """
        if av is None:
            raise ModuleNotFoundError(
                "Recording to a video file requires `av`:\n"
                "https://github.com/PyAV-Org/PyAV"
            )

        if directory is None:
            directory = Path.cwd()

        if path is None:
            path = f"fastplotlib_{datetime.now():%Y-%m-%d_%H-%M-%S}.mp4"

            # joining with an absolute path gives the absolute path, so it is used as is
        path = Path(directory).expanduser() / Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        self._path = path

        if options is None:
            # high quality defaults for sharp lines and text
            options = {"crf": "15", "preset": "medium"}

        self._container = av.open(str(self._path), mode="w")
        self._stream = self._container.add_stream(codec, options=options)
        self._stream.pix_fmt = pixel_format
        self._stream.codec_context.time_base = TIME_BASE

        # (height, width) of the frames, set by the first frame
        self._size: tuple[int, int] | None = None

        # time of the first frame, timestamps are relative to this
        self._start_time: float | None = None

        # frames are passed to the encoding thread through this queue, None ends the recording
        self._queue = Queue()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def path(self) -> Path:
        """output video file"""
        return self._path

    @property
    def size(self) -> tuple[int, int] | None:
        """(height, width) of the frames, ``None`` until the first frame is added"""
        return self._size

    def add_frame(self, frame: np.ndarray):
        """
        Add a frame to the video. The time at which this is called is used as the frame's timestamp.

        Parameters
        ----------
        frame: np.ndarray
            uint8 array of shape [height, width, 3], RGB

        """
        t = perf_counter()

        if self._size is None:
            self._size = frame.shape[:2]
            self._start_time = t

        if frame.shape[:2] != self._size:
            raise ValueError(
                f"frame size {frame.shape[:2]} does not match the video size {self._size}"
            )

        self._queue.put((frame, t - self._start_time))

    def close(self):
        """Finish writing all frames and close the video file. Blocks until encoding is done."""
        self._queue.put(None)
        self._thread.join()

    def _run(self):
        """encoding thread"""
        last_pts = -1

        while True:
            item = self._queue.get()

            # recording has ended
            if item is None:
                break

            frame, t = item

            if last_pts == -1:
                # libx264 requires an even width and height, trim the last row and/or column
                height, width = self._size
                self._stream.height = height - height % 2
                self._stream.width = width - width % 2

            frame = av.VideoFrame.from_ndarray(
                np.ascontiguousarray(
                    frame[: self._stream.height, : self._stream.width]
                ),
                format="rgb24",
            )

            # timestamps must be strictly increasing
            pts = max(round(t / TIME_BASE), last_pts + 1)
            frame.pts = pts
            frame.time_base = TIME_BASE
            last_pts = pts

            for packet in self._stream.encode(frame):
                self._container.mux(packet)

        # flush frames that are still buffered in the encoder
        for packet in self._stream.encode():
            self._container.mux(packet)

        self._container.close()
