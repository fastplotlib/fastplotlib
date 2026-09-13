from __future__ import annotations
from collections.abc import Callable
from dataclasses import make_dataclass, field, fields, dataclass
from functools import wraps, partial
from typing import get_type_hints, Any


def get_method_name(method: Callable) -> str:
    # we can't use __init__ as a dataclass field for the config
    if method.__name__ == "__init__":
        return "init"

    return method.__name__


def inv_get_method_name(name: str) -> str:
    # inverse of get_method_name
    if name == "init":
        return "__init__"

    return name


class ConfigValue:
    """Just used to mark a configurable argument"""

    pass


class ConfigDescriptor:
    """Descriptor pattern so classes can access their configuration for users to set/get config options"""

    def __init__(self, classes):
        self.__classes = classes

    def __get__(self, instance, cls: type = None):
        if instance is not None:
            raise AttributeError("set config options on the class, not an instance")

        if cls not in self.__classes.keys():
            raise AttributeError("Class is not registered")

        return self.__classes[cls]

    def __set__(self, obj, value):
        raise AttributeError("Cannot set")


@dataclass
class Pending:
    method: Callable  # the actual method obj
    defaults: dict

    @property
    def name(self) -> str:
        return get_method_name(self.method)

    @property
    def module(self) -> str:
        """the pending module"""
        return self.method.__module__

    @property
    def cls(self) -> str:
        """name of class module belongs to"""
        return self.method.__qualname__.rpartition(".")[0]

    @property
    def cls_qual(self) -> tuple[str, str]:
        """fully qualifying name of class module belongs to"""

        # use a tuple to disambiguate ("a.b_module", "Class") vs ("a", "b_class.Class")
        # edge case but easy to cover
        return (self.module, self.cls)

    def is_sibling(self, other: Pending) -> bool:
        """check if other Pending belong to the same class as this one"""
        return self.cls_qual == other.cls_qual

    def belongs_to(self, cls: type) -> bool:
        """check if this module belongs to this fully created class object, used for @Config.register"""
        return self.cls_qual == (cls.__module__, cls.__qualname__)

    def to_config(self) -> object:
        """create the config dataclass for this method"""
        type_hints = get_type_hints(self.method)

        signature = list()
        for arg, val in self.defaults.items():
            # if the type isn't declared in the function signature fill with Any
            type_annot = type_hints.get(arg, Any)
            # for each parameter: (arg, type, default value)
            signature.append((arg, type_annot, field(default=val)))

        mc = make_dataclass(
            self.name,
            fields=signature,
            slots=True,  # fields are fixed, user can't do method.something_random = value
            eq=False,  # == operator makes no sense since values can be any object, arrays, buffers, etc.
        )

        return mc()


class Config:
    """Global config system"""

    def __init__(self):
        # list of Pending
        self._pending = list()

        # dict maps: {cls -> cls_dataclass_config}
        self._registry: dict[type, object] = {}
        # descriptor so classes can actually access their config options
        self._descriptor = ConfigDescriptor(self._registry)

    @property
    def descriptor(self) -> ConfigDescriptor:
        return self._descriptor

    def register(self, cls):
        """Register a class"""
        if self._pending and not self._pending[-1].belongs_to(cls):
            raise TypeError(
                f"{self._pending[-1].cls_qual} is not registered with the global config"
            )

        method_configs = {p.name: p.to_config() for p in self._pending}

        # derive any un-registered methods from closest parent class that has it
        # this is mainly for the ImguiFigure class
        # we want Figure.config.show to derive from ImguiFigure.show

        # [1:-1] skips the class itself and bare object
        parents = cls.__mro__[1:-1]
        for parent in parents:
            if parent in self._registry:
                # get the names of all configurable methods on this parent
                for f in fields(self._registry[parent]):
                    # if the parent has a configurable method that this subclass doesn't have defaults for
                    if f.name not in method_configs.keys() and hasattr(cls, inv_get_method_name(f.name)):
                        # use the same method dataclass configuration object for this subclass
                        method_configs[f.name] = getattr(self._registry[parent], f.name)

        if not method_configs:
            raise LookupError(
                f"{cls} has no registered defaults nor any parent class with registered defaults to derive from"
            )

        self._register(cls, method_configs)

        self._pending.clear()

        return cls

    def _register(self, cls, method_dcs: dict[str, object]):
        # actually adds the class along with all the method configurable dataclasses to the registry
        dc = make_dataclass(
            cls.__name__,
            fields=[(m, type(mdc), field(default=mdc)) for m, mdc in method_dcs.items()],
            slots=True,  # fields are fixed, each class set a fixed set of methods
            frozen=True,  # can't change method config instances
            eq=False,  # == operator makes no sense here, every config class is unique anyways
        )

        self._registry[cls] = dc()

    def defaults(self, **defaults):
        """register a method with default kwargs"""

        def wrapper(method):
            new_pending = Pending(method, defaults)
            if self._pending and not new_pending.is_sibling(self._pending[-1]):
                raise TypeError(
                    f"{self._pending[-1].cls_qual} is not registered with the global config"
                )

            self._pending.append(new_pending)

            @wraps(method)
            def injector(*args, **kwargs):
                print("inside injector")
                return method(*args, **kwargs)

            return injector

        return wrapper


config = Config()


# TODO: usage plan
class Graphic:
    config = config.descriptor


@config.register
class LineGraphic(Graphic):
    @config.defaults(colors="w", thickness=2.0)
    def __init__(
        self,
        data,
        colors: str | tuple[float, float, float] = ConfigValue,
        thickness: float = ConfigValue,
        cmap: str | None = None,
    ):
        print(data, colors, thickness, cmap)
        print(LineGraphic.config)


@config.register
class Figure:
    def __init__(self):
        pass

    @config.defaults(show=True)
    def show(self, toolbar: bool = ConfigValue):
        pass
