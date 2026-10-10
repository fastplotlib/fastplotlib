from time import sleep

import av
import numpy as np
import pytest

import fastplotlib as fpl
from fastplotlib.utils._video_writer import VideoWriter

N_FRAMES = 10
CANVAS_SIZE = (500, 300)  # width, height


def decode(path) -> list[av.VideoFrame]:
    """decode all frames of a video file"""
    with av.open(str(path)) as container:
        return list(container.decode(video=0))


def make_frames(n: int, height: int, width: int) -> list[np.ndarray]:
    """frames with a moving white column so that every frame is different"""
    frames = list()
    for i in range(n):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:, i % width] = 255
        frames.append(frame)

    return frames


def make_figure() -> fpl.Figure:
    fig = fpl.Figure(canvas="offscreen", size=CANVAS_SIZE)
    fig[0, 0].add_line(np.random.rand(50, 2).astype(np.float32))
    fig.show()

    return fig


def test_video_writer(tmp_path):
    path = tmp_path / "test.mp4"

    writer = VideoWriter(path)
    assert writer.path == path
    assert writer.size is None

    for frame in make_frames(N_FRAMES, 48, 64):
        writer.add_frame(frame)

    assert writer.size == (48, 64)

    writer.close()

    frames = decode(path)
    assert len(frames) == N_FRAMES
    assert (frames[0].height, frames[0].width) == (48, 64)


def test_video_writer_timestamps(tmp_path):
    path = tmp_path / "test.mp4"

    # variable frame rate, the time between frames should be preserved
    delays = [0.02] * 5 + [0.1] * 5

    writer = VideoWriter(path)
    for frame, delay in zip(make_frames(len(delays), 48, 64), delays):
        writer.add_frame(frame)
        sleep(delay)
    writer.close()

    frames = decode(path)
    times = np.array([float(frame.time) for frame in frames])

    # timestamps are strictly increasing
    assert np.all(np.diff(times) > 0)

    # first frame is at 0, last frame is at the sum of all delays except the last one
    assert times[0] == 0
    np.testing.assert_allclose(times[-1], sum(delays[:-1]), atol=0.05)


@pytest.mark.parametrize("size", [(48, 64), (47, 64), (48, 65), (47, 65)])
def test_video_writer_odd_size(tmp_path, size):
    path = tmp_path / "test.mp4"
    height, width = size

    writer = VideoWriter(path)
    for frame in make_frames(N_FRAMES, height, width):
        writer.add_frame(frame)
    writer.close()

    # libx264 requires an even width and height, last row and/or column is trimmed
    frames = decode(path)
    assert (frames[0].height, frames[0].width) == (
        height - height % 2,
        width - width % 2,
    )


def test_video_writer_frame_size_mismatch(tmp_path):
    writer = VideoWriter(tmp_path / "test.mp4")
    writer.add_frame(np.zeros((48, 64, 3), dtype=np.uint8))

    with pytest.raises(ValueError):
        writer.add_frame(np.zeros((64, 48, 3), dtype=np.uint8))

    writer.close()


def test_video_writer_no_frames(tmp_path):
    path = tmp_path / "test.mp4"

    writer = VideoWriter(path)
    writer.close()

    assert writer.size is None
    assert not path.exists()


def test_video_writer_default_name(tmp_path):
    writer = VideoWriter(directory=tmp_path)

    assert writer.path.parent == tmp_path
    assert writer.path.name.startswith("fastplotlib_")
    assert writer.path.suffix == ".mp4"

    writer.close()


@pytest.mark.parametrize("path", ["clip.mp4", "sub/clip.mp4", "nested/sub/clip.mp4"])
def test_video_writer_relative_path(tmp_path, path):
    # relative paths are inside the directory, folders are created if they don't exist
    directory = tmp_path / "recordings"

    writer = VideoWriter(path, directory=directory)
    assert writer.path == directory / path
    assert writer.path.parent.is_dir()

    writer.close()


def test_video_writer_absolute_path(tmp_path):
    # absolute paths are used as is, directory is ignored
    path = tmp_path / "other" / "clip.mp4"

    writer = VideoWriter(path, directory=tmp_path / "recordings")
    assert writer.path == path
    assert path.parent.is_dir()
    assert not (tmp_path / "recordings").exists()

    writer.close()


def test_video_writer_home_directory(tmp_path, monkeypatch):
    # "~" is expanded on all OS, HOME is used on unix and USERPROFILE on windows
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    writer = VideoWriter("clip.mp4", directory="~/recordings")
    assert writer.path == tmp_path / "recordings" / "clip.mp4"
    writer.close()

    writer = VideoWriter("~/clip.mp4", directory=tmp_path / "recordings")
    assert writer.path == tmp_path / "clip.mp4"
    writer.close()


def test_record_figure(tmp_path):
    path = tmp_path / "test.mp4"
    fig = make_figure()

    assert not fig.recording

    fig.start_recording(path)
    assert fig.recording

    for i in range(N_FRAMES):
        fig.canvas.draw()

    fig.stop_recording()
    assert not fig.recording

    frames = decode(path)
    assert len(frames) == N_FRAMES

    width, height = fig.canvas.get_physical_size()
    assert (frames[0].height, frames[0].width) == (
        height - height % 2,
        width - width % 2,
    )


def test_record_figure_no_frames(tmp_path):
    path = tmp_path / "test.mp4"
    fig = make_figure()

    fig.start_recording(path)

    # nothing was rendered, no file is written
    fig.stop_recording()
    assert not path.exists()


def test_recording_state(tmp_path):
    fig = make_figure()

    # stopping when not recording does nothing
    fig.stop_recording()
    assert not fig.recording

    fig.start_recording(tmp_path / "test.mp4")

    # can't start if already recording
    with pytest.raises(RuntimeError):
        fig.start_recording(tmp_path / "test2.mp4")

    fig.canvas.draw()
    fig.stop_recording()

    # stopping twice does nothing
    fig.stop_recording()
    assert not fig.recording

    # can record again after stopping
    fig.start_recording(tmp_path / "test2.mp4")
    fig.canvas.draw()
    fig.stop_recording()
    assert (tmp_path / "test2.mp4").exists()


def test_record_resize(tmp_path):
    fig = make_figure()

    fig.start_recording(tmp_path / "test.mp4")
    for i in range(N_FRAMES):
        fig.canvas.draw()

    # video size can't change, recording stops and is saved
    fig.canvas.set_logical_size(400, 400)
    with pytest.warns(UserWarning, match="resized"):
        fig.canvas.draw()

    assert not fig.recording

    # frame after the resize is not in the video
    frames = decode(tmp_path / "test.mp4")
    assert len(frames) == N_FRAMES


@pytest.mark.skipif(not fpl.IMGUI, reason="toolbar requires imgui-bundle")
def test_record_includes_imgui(tmp_path):
    fig = make_figure()

    # lossless so that the comparison is exact
    fig.start_recording(
        tmp_path / "test.mp4", pixel_format="yuv444p", options={"crf": "0"}
    )
    # imgui windows only appear after the first frame
    for i in range(3):
        fig.canvas.draw()
    fig.stop_recording()

    recorded = decode(tmp_path / "test.mp4")[-1].to_ndarray(format="rgb24")

    # renderer snapshot only has the pygfx render, no imgui
    snapshot = fig.export_numpy(rgb=True)[: recorded.shape[0], : recorded.shape[1]]

    # toolbar is at the bottom of the subplot, it should be in the recording but not in the snapshot
    toolbar_rows = slice(-25, None)
    difference = np.abs(
        recorded[toolbar_rows].astype(np.int16)
        - snapshot[toolbar_rows].astype(np.int16)
    )
    assert difference.max() > 100


def test_record_default_directory(tmp_path, monkeypatch):
    # default directory is ~/fastplotlib-recordings, point home at tmp_path so nothing is written to the real home
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    assert fpl.Figure.config.start_recording.directory == "~/fastplotlib-recordings"

    fig = make_figure()

    fig.start_recording()
    fig.canvas.draw()
    fig.stop_recording()

    files = list((tmp_path / "fastplotlib-recordings").glob("fastplotlib_*.mp4"))
    assert len(files) == 1


def test_record_config_directory(tmp_path):
    fig = make_figure()

    default = fpl.Figure.config.start_recording.directory
    fpl.Figure.config.start_recording.directory = tmp_path / "recordings"

    try:
        # directory from config is used
        fig.start_recording("clip.mp4")
        fig.canvas.draw()
        fig.stop_recording()
        assert (tmp_path / "recordings" / "clip.mp4").exists()

        # explicitly passed directory takes priority over config
        fig.start_recording("clip.mp4", directory=tmp_path / "other")
        fig.canvas.draw()
        fig.stop_recording()
        assert (tmp_path / "other" / "clip.mp4").exists()

        # absolute path takes priority over config
        fig.start_recording(tmp_path / "absolute.mp4")
        fig.canvas.draw()
        fig.stop_recording()
        assert (tmp_path / "absolute.mp4").exists()

    finally:
        # reset config so other tests are not affected
        fpl.Figure.config.start_recording.directory = default