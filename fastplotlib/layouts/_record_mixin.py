from typing import *
from pathlib import Path
from multiprocessing import Queue, Process
from time import time

try:
    import av
except ImportError:
    HAS_AV = False
else:
    HAS_AV = True


class VideoWriterAV(Process):
    def __init__(
            self,
            path: Union[Path, str],
            queue: Queue,
            fps: int,
            width: int,
            height: int,
            codec: str,
            pixel_format: str,
            options: dict = None
    ):
        super().__init__()
        self.path = path
        self.queue = queue

        self.container = av.open(path, mode="w")

        self.stream = self.container.add_stream(codec, rate=fps, options=options)

        # in case libx264, trim last rows and/or column
        if width % 2 != 0:
            width -= 1
        if height % 2 != 0:
            height -= 1

        self.stream.width = width
        self.stream.height = height

        self.stream.pix_fmt = pixel_format

    def run(self):
        while True:
            if self.queue.empty():
                continue

            frame = self.queue.get()

            if frame is None:
                self.container.close()
                break

            frame = av.VideoFrame.from_ndarray(
                frame[:self.stream.height, :self.stream.width],  # trim if necessary
                format="rgb24"
            )

            for packet in self.stream.encode(frame):
                self.container.mux(packet)

        for packet in self.stream.encode():
            self.container.mux(packet)

        self.container.close()

        self.close()


# adds recording functionality to GridPlot and Plot
class RecordMixin:
    def __init__(self):
        self._record_writer: VideoWriterAV = None
        self._record_queue = Queue()
        self._record_fps = 25
        self._record_timer = 0
        self._record_start_time = 0

    def _record(self):
        t = time()
        # this is required else it tries to record EVERY frame and slows everything else down
        if t - self._record_timer < (1 / self._record_fps):
            return

        self._record_timer = t

        if self._record_writer is not None:
            ss = self.canvas.snapshot()
            # exclude alpha channel
            self._record_queue.put(ss.data[..., :-1])

    def record_start(
            self,
            path: Union[str, Path],
            fps: int = 25,
            codec: str = "mpeg4",
            pixel_format: str = "yuv420p",
            options: dict = None
    ):
        """
        Start a recording, experimental. Call ``record_end()`` to end a recording.
        Playback duration does not exactly match recording duration.

        Requires OpenCV. **Do not resize canvas during a recording.**

        Parameters
        ----------
        path: str or Path
            path to save the recording

        fps: int, default ``25``
            framerate, do not use > 25 within jupyter

        codec: str, default "mpeg4"
            codec to use, see ffmpeg list: https://www.ffmpeg.org/ffmpeg-codecs.html .
            In general, ``"mpeg4"`` should work on most systems. ``"libx264"`` is a
            better option if you have it installed.

        pixel_format: str, default "yuv420p"
            pixel format

        options: dict, optional
            Codec options. For example, if using ``"mpeg4"`` you can use ``{"q:v": "20"}`` to set the quality between
            1-31, where "1" is highest and "31" is lowest. If using ``"libx264"``` you can use ``{"crf": "30"}`` where
            the "crf" value is between "0" (highest quality) and "50" (lowest quality).


        """

        if not HAS_AV:
            raise ModuleNotFoundError(
                "Recording to video file requires `av`\n"
                "https://github.com/PyAV-Org/PyAV"
            )

        self._record_queue = Queue()

        ss = self.canvas.snapshot()

        if Path(path).exists():
            raise FileExistsError(f"File already exists at given path: {path}")

        self._record_writer = VideoWriterAV(
            path=str(path),
            queue=self._record_queue,
            fps=int(fps),
            width=ss.width,
            height=ss.height,
            codec=codec,
            pixel_format=pixel_format,
            options=options
        )

        self._record_writer.start()

        # 1.3 seems to work well to reduce that difference between playback time and recording time
        # will properly investigate later
        self._record_fps = fps * 1.3
        self._record_timer = time()
        self._record_start_time = time()

        self.add_animations(self._record)

    def record_stop(self) -> float:
        """
        End a current recording. Returns the real duration of the recording

        Returns
        -------
        float
            recording duration
        """

        self._record_queue.put(None)
        self._record_writer.join(timeout=5)
        self._record_queue.close()
        # self._record_writer = None

        self.remove_animation(self._record)
        return time() - self._record_start_time
