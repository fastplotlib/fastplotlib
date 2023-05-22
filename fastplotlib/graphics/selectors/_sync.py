from typing import *

from . import LinearSelector


class Synchronizer:
    def __init__(self, *selectors: LinearSelector, key_bind: str = "Shift"):
        """
        Synchronize the movement of `Selectors`. Selectors will move in sync only when the selected `"key_bind"` is
        used during the mouse movement event. Valid key binds are: ``"Control"``, ``"Shift"`` and ``"Alt"``.
        If ``key_bind`` is ``None`` then the selectors will always be synchronized.

        Parameters
        ----------
        selectors
            selectors to synchronize

        key_bind: str, default ``"Shift"``
            one of ``"Control"``, ``"Shift"`` and ``"Alt"`` or ``None``
        """
        self._selectors = list()
        self.key_bind = key_bind

        for s in selectors:
            self.add(s)

        self.block_event = False

        self.enabled: bool = True

    @property
    def selectors(self):
        """Selectors managed by the Synchronizer"""
        return self._selectors

    def add(self, selector):
        """add a selector"""
        selector.selection.add_event_handler(self._handle_event)
        self._selectors.append(selector)

    def remove(self, selector):
        """remove a selector"""
        self._selectors.remove(selector)
        selector.selection.remove_event_handler(self._handle_event)

    def _handle_event(self, ev):
        if self.block_event:
            # because infinite recursion
            return

        if not self.enabled:
            return

        self.block_event = True

        source = ev.pick_info["graphic"]
        delta = ev.pick_info["delta"]
        pygfx_ev = ev.pick_info["pygfx_event"]

        # only moves when modifier is used
        if pygfx_ev is None:
            self.block_event = False
            return

        if self.key_bind is not None:
            if self.key_bind not in pygfx_ev.modifiers:
                self.block_event = False
                return

        if delta is not None:
            self._move_selectors(source, delta)

        self.block_event = False

    def _move_selectors(self, source, delta):
        for s in self.selectors:
            # must use == and not is to compare Graphics because they are weakref proxies!
            if s == source:
                # if it's the source, since it has already movied
                continue

            s._move_graphic(delta)

    def __del__(self):
        for s in self.selectors:
            self.remove(s)

        self.selectors.clear()
