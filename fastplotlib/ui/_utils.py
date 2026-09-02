class ChangeFlag:
    """
    A flag that helps detect whether an imgui UI has been changed by the user.
    Basically, once True, always True.

    Example::

        changed = ChangeFlag(False)

        changed.value, bah = (False, False)

        print(changed.value)

        changed.value, bah = (True, False)

        print(changed.value)

        changed.value, bah = (False, False)

        print(changed.value)

    """

    def __init__(self, value: bool):
        self._value = bool(value)

    @property
    def value(self) -> bool:
        return self._value

    @value.setter
    def value(self, value: bool):
        if value:
            self._value = True

    def __bool__(self):
        return self.value

    def __or__(self, other):
        return self._value | other

    def __eq__(self, other):
        return self.value == other

    def force_value(self, value):
        self._value = value
