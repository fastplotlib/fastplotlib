"""
LinearRegionSelectors
=====================

Example with ipywidgets sliders to change a sine wave and view the frequency spectra. You can run this in jupyterlab
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

import numpy as np
import fastplotlib as fpl
from ipywidgets import FloatSlider, Checkbox, VBox


def generate_data(freq, duration, sampling_rate, ampl, noise_sigma):
    # generate a sine wave using given params
    xs = np.linspace(0, duration, sampling_rate * duration)
    ys = np.sin((2 * np.pi) * freq * xs) * ampl

    noise = np.random.normal(scale=noise_sigma, size=sampling_rate * duration)

    signal = np.column_stack([xs, ys + noise])
    fft_mag = np.abs(np.fft.rfft(signal[:, 1]))
    fft_freqs = np.linspace(0, sampling_rate / 2, num=fft_mag.shape[0])

    return np.column_stack([xs, ys + noise]), np.column_stack([fft_freqs, fft_mag])


signal, fft = generate_data(
    freq=1,
    duration=10,
    sampling_rate=50,
    ampl=1,
    noise_sigma=0.05
)

# create a figure
figure = fpl.Figure(shape=(2, 1), names=["signal", "fft"], size=(700, 560))

# line graphic for the signal
signal_line = figure[0, 0].add_line(signal, thickness=1)

# easier to understand the frequency of the sine wave if the
# axes go through the middle of the sine wave
figure[0, 0].axes.intersection = (0, 0, 0)

# line graphic for fft
fft_line = figure[1, 0].add_line(fft)

# do not maintain the aspect ratio of the fft subplot
figure[1, 0].camera.maintain_aspect = False

# create ipywidget sliders
slider_freq = FloatSlider(min=0.1, max=10, value=1.0, step=0.1, description="freq: ")
slider_ampl = FloatSlider(min=0.0, max=10, value=1.0, step=0.5, description="ampl: ")
slider_noise = FloatSlider(min=0, max=1, value=0.05, step=0.05, description="noise: ")

# checkbox
checkbox_autoscale = Checkbox(value=False, description="autoscale: ")


def update(*args):
    # update whenever a slider changes
    freq = slider_freq.value
    ampl = slider_ampl.value
    noise = slider_noise.value

    signal, fft = generate_data(
        freq=freq,
        duration=10,
        sampling_rate=50,
        ampl=ampl,
        noise_sigma=noise,
    )

    signal_line.data[:, :-1] = signal
    fft_line.data[:, :-1] = fft

    if checkbox_autoscale.value:
        for subplot in figure:
            subplot.auto_scale(maintain_aspect=False)


# when any one slider changes, it calls update
for slider in [slider_freq, slider_ampl, slider_noise]:
    slider.observe(update, "value")

# display the fastplotlib figure and ipywidgets in a VBox (vertically stacked)
# figure.show() just returns an ipywidget object
VBox([figure.show(), slider_freq, slider_ampl, slider_noise, checkbox_autoscale])
