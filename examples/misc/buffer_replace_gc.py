"""
Buffer replacement garbage collection test
==========================================

This is an example that used for a manual test to ensure that GPU VRAM is free when buffers are replaced.

Use while monitoring VRAM usage with nvidia-smi
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'


from typing import Literal
import numpy as np
import fastplotlib as fpl
from fastplotlib.ui import EdgeWindow
from imgui_bundle import imgui


def generate_dataset(size: int) -> dict[str, np.ndarray]:
    return {
        "data": np.random.rand(size, 3),
        "colors": np.random.rand(size, 4),
        # TODO: there's a wgpu bind group issue with edge_colors, will figure out later
        # "edge_colors": np.random.rand(size, 4),
        "markers": np.random.choice(list("osD+x^v<>*"), size=size),
        "sizes": np.random.rand(size) * 5,
        "point_rotations": np.random.rand(size) * 180,
    }


datasets = {
    "init": generate_dataset(50_000),
    "small": generate_dataset(100),
    "large": generate_dataset(5_000_000),
}


class UI(EdgeWindow):
    def __init__(self, figure):
        super().__init__(figure=figure, size=200, location="right", title="UI")
        init_data = datasets["init"]
        self._figure["line"].add_line(
            data=init_data["data"], colors=init_data["colors"], name="line"
        )
        self._figure["scatter"].add_scatter(
            **init_data,
            uniform_size=False,
            uniform_marker=False,
            uniform_edge_color=False,
            name="scatter",
        )

    def update(self):
        for graphic in ["line", "scatter"]:
            if graphic == "line":
                features = ["data", "colors"]

            elif graphic == "scatter":
                features = list(datasets["init"].keys())

            for size in ["small", "large"]:
                for fea in features:
                    if imgui.button(f"{size} - {graphic} - {fea}"):
                        self._replace(graphic, fea, size)

        imgui.text(f"VRAM usage: {self.vram_usage} MB")

    def _replace(
        self,
        graphic: Literal["line", "scatter", "image"],
        feature: Literal["data", "colors", "markers", "sizes", "point_rotations"],
        size: Literal["small", "large"],
    ):
        new_value = datasets[size][feature]

        setattr(self._figure[graphic][graphic], feature, new_value)


figure = fpl.Figure(shape=(3, 1), size=(700, 1600), names=["line", "scatter", "image"])
ui = UI(figure)
figure.add_gui(ui)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
