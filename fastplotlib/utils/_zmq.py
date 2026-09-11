from functools import wraps

import numpy as np
import zmq

from .. import Graphic, Figure


class ZmqWorker:
    def __init__(self, address: str = "tcp://127.0.0.1", port_start: int = 5555):
        self._address = address
        self._port_start = port_start
        self._port_iterator = 0

        self._context = zmq.Context()
        # maps (graphic, feature) -> Socket
        self._sockets: dict[(str, str), zmq.Socket] = dict()

        self._figures: set[Figure] = set()

    def _create_socket(self, graphic: Graphic):
        for feature in graphic._features:
            subscriber = self._context.socket(zmq.SUB)
            subscriber.setsocketopt(zmq.SUBSCRIBE, b"")
            subscriber.setsocketopt(zmq.CONFLATE, 1)

            subscriber.connect(f"{self._address}:{self._port_start + self._port_iterator}")

            self._port_iterator += 1

            self._sockets[(graphic, feature)] = subscriber

    def _add_figure(self, figure: Figure):
        if figure in self._figures:
            return
        figure.add_animations(self._receive)

    def _receive(self, figure: Figure):
        """receive new data and update for all graphics in the given Figure"""

        for (graphic, feature), subscriber in self._sockets.items():
            if graphic._plot_area.get_figure() is not figure:
                continue
            try:
                new_bytes = subscriber.recv(zmq.NOBLOCK)
            except zmq.Again:
                pass
            else:
                current_data = getattr(graphic, feature).value
                new_data = np.frombuffer(new_bytes, dtype=current_data.dtype).reshape(current_data.shape)
                setattr(graphic, feature, new_data)

    def dispatch(self, graphics: list[Graphic] = None):
        def decorator(compute_func):
            @wraps(compute_func)
            def dispatch_compute(*args, **kwargs):
                # create socket and subscriber for each graphic
                for g in graphics:
                    self._create_socket(g)
                    self._add_figure(g._plot_area.get_figure())

            return dispatch_compute
        return decorator
