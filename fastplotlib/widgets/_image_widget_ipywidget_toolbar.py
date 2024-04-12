from functools import partial

from ipywidgets import (
    VBox,
    Button,
    Layout,
    IntSlider,
    BoundedIntText,
    Play,
    jslink,
    HBox,
)


class IpywidgetImageWidgetToolbar(VBox):
    def __init__(self, iw):
        """
        Basic toolbar for a ImageWidget instance.

        Parameters
        ----------
        plot:
        """
        self.iw = iw

        self.reset_vminvmax_button = Button(
            value=False,
            disabled=False,
            icon="adjust",
            layout=Layout(width="auto"),
            tooltip="reset vmin/vmax",
        )

        self.reset_vminvmax_hlut_button = Button(
            value=False,
            icon="adjust",
            description="reset",
            layout=Layout(width="auto"),
            tooltip="reset vmin/vmax and reset histogram using current frame",
        )

        self.sliders: dict[str, IntSlider] = dict()

        # only for xy data, no time point slider needed
        if self.iw.ndim == 2:
            widgets = [self.reset_vminvmax_button]
        # for txy, tzxy, etc. data
        else:
            for dim in self.iw.slider_dims:
                slider = IntSlider(
                    min=0,
                    max=self.iw._dims_max_bounds[dim] - 1,
                    step=1,
                    value=0,
                    description=f"dimension: {dim}",
                    orientation="horizontal",
                )

                slider.observe(
                    partial(self.iw._slider_value_changed, dim), names="value"
                )

                self.sliders[dim] = slider

            self.step_size_setter = BoundedIntText(
                value=1,
                min=1,
                max=self.sliders["t"].max,
                step=1,
                description="Step Size:",
                disabled=False,
                description_tooltip="set slider step",
                layout=Layout(width="150px"),
            )
            self.speed_text = BoundedIntText(
                value=100,
                min=1,
                max=1_000,
                step=50,
                description="Speed",
                disabled=False,
                description_tooltip="Playback speed, this is NOT framerate.\nArbitrary units between 1 - 1,000",
                layout=Layout(width="150px"),
            )
            self.play_button = Play(
                value=0,
                min=self.sliders["t"].min,
                max=self.sliders["t"].max,
                step=self.sliders["t"].step,
                description="play/pause",
                disabled=False,
            )
            widgets = [
                self.reset_vminvmax_button,
                self.reset_vminvmax_hlut_button,
                self.play_button,
                self.step_size_setter,
                self.speed_text,
            ]

            self.play_button.interval = 10

            self.step_size_setter.observe(self._change_stepsize, "value")
            self.speed_text.observe(self._change_framerate, "value")
            jslink((self.play_button, "value"), (self.sliders["t"], "value"))
            jslink((self.play_button, "max"), (self.sliders["t"], "max"))

        self.reset_vminvmax_button.on_click(self._reset_vminvmax)
        self.reset_vminvmax_hlut_button.on_click(self._reset_vminvmax_frame)

        self.iw.figure.renderer.add_event_handler(self._set_slider_layout, "resize")

        # the buttons
        self.hbox = HBox(widgets)

        super().__init__((self.hbox, *list(self.sliders.values())))

    def _reset_vminvmax(self, obj):
        self.iw.reset_vmin_vmax()

    def _reset_vminvmax_frame(self, obj):
        self.iw.reset_vmin_vmax_frame()

    def _change_stepsize(self, obj):
        self.sliders["t"].step = self.step_size_setter.value

    def _change_framerate(self, change):
        interval = int(1000 / change["new"])
        self.play_button.interval = interval

    def _set_slider_layout(self, *args):
        w, h = self.iw.figure.renderer.logical_size

        for k, v in self.sliders.items():
            v.layout = Layout(width=f"{w}px")
