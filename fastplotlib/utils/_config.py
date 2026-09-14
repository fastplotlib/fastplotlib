from __future__ import annotations
from collections.abc import Callable
from dataclasses import make_dataclass, field, fields, dataclass
from functools import wraps, partial
import inspect
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


def identify(val):
    return val


def _config_setattr(self, name, value):
    if name not in self.__slots__:
        cls_qual, method = self._fpl_owner
        raise AttributeError(
            f"'{method}' config for {cls_qual} has no option '{name}'\n"
            f"Valid options: {sorted(self.__slots__)}"
        ) from None
    object.__setattr__(self, name, value)


def _config_getattr(self, name):
    cls_qual, method = self._fpl_owner
    raise AttributeError(
        f"'{method}' config for {cls_qual} has no option '{name}'\n"
        f"Valid options: {sorted(self.__slots__)}"
    )


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

        params = inspect.signature(self.method).parameters

        sig_value_is_config = {
            name for name, p in params.items() if p.default is ConfigValue
        }

        missing_default = sig_value_is_config - self.defaults.keys()
        if missing_default:
            raise TypeError(
                f"{self.method.__qualname__}: signature marks {sorted(missing_default)} "
                f"as ConfigValue but @global_config.set declares no value for them"
            )

        missing_marker = self.defaults.keys() - sig_value_is_config
        if missing_marker:
            raise TypeError(
                f"{self.method.__qualname__}: @global_config.set declares {sorted(missing_marker)} "
                f"but the signature doesn't mark them as ConfigValue, so they'll be ignored"
            )

        signature = list()
        for arg, val in self.defaults.items():
            # if the type isn't declared in the function signature fill with Any
            type_annot = type_hints.get(arg, Any)
            # for each parameter: (arg, type, default value)
            if val.__class__.__hash__ is None:
                # need to handle unhashable differently, i.e. mutable, objects like arrays and lists differently
                f = field(default_factory=partial(identify, val))
            else:
                f = field(default=val)
            signature.append((arg, type_annot, f))

        mc = make_dataclass(
            self.name,
            fields=signature,
            slots=True,  # fields are fixed, user can't do method.something_random = value
            eq=False,  # == operator makes no sense since values can be any object, arrays, buffers, etc.
            namespace={
                "__setattr__": _config_setattr,
                "__getattr__": _config_getattr,
                "_fpl_owner": (self.cls, self.method.__name__),
            },
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

        for parent in cls.__mro__:
            # can't use getattr since that will call ConfigDescriptor.__get__
            if isinstance(parent.__dict__.get("config"), ConfigDescriptor):
                break

        else:
            raise AttributeError(
                f"{cls} is registered with @global_config.register but doesn't have a "
                f"config descriptor class attribute."
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
                    if f.name not in method_configs.keys() and hasattr(
                        cls, inv_get_method_name(f.name)
                    ):
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
            fields=[
                (m, type(mdc), field(default=mdc)) for m, mdc in method_dcs.items()
            ],
            slots=True,  # fields are fixed, each class set a fixed set of methods
            frozen=True,  # can't change method config instances
            eq=False,  # == operator makes no sense here, every config class is unique anyways
        )

        self._registry[cls] = dc()

    def set(self, **defaults):
        """register a method with default kwargs"""

        def wrapper(method):
            new_pending = Pending(method, defaults)
            if self._pending and not new_pending.is_sibling(self._pending[-1]):
                raise TypeError(
                    f"{self._pending[-1].cls_qual} is not registered with the global config"
                )

            self._pending.append(new_pending)

            # keep these to use them in the injector
            method_name = new_pending.name
            # create signature object just once when the method is decorated instead of every time the method is called
            sig = inspect.signature(method)

            @wraps(method)
            def injector(instance, *args, **kwargs):
                # get the method config dataclass
                method_config = getattr(type(instance).config, method_name)

                # create a binding
                try:
                    binding = sig.bind(instance, *args, **kwargs)
                except TypeError as e:
                    # if *args and **kwargs don't match the signature raises a TypeError
                    # useful if the user passed wrong things, we need to catch and tell them what method it was
                    # since binding has no idea of the full namespace when we're handling it here
                    raise TypeError(f"{method.__qualname__}: {e}") from None

                # apply the default vals from the method signature
                # these are the default vals in the method signature itself
                binding.apply_defaults()

                for arg, val in binding.arguments.items():
                    # configurable value
                    if val is ConfigValue:
                        # fill in from current config
                        binding.arguments[arg] = getattr(method_config, arg)

                return method(*binding.args, **binding.kwargs)

            return injector

        return wrapper

    def __getitem__(self, cls: type):
        if cls not in self._registry:
            raise KeyError(f"{cls} not registered in global config")

        return self._registry[cls]

    def print_config(self):
        """print the config of every registered class, yaml-like"""
        for cls, class_config in self._registry.items():
            print(f"{cls.__name__}:")

            for method in fields(class_config):
                method_config = getattr(class_config, method.name)
                print(f"  {method.name}:")

                for arg in fields(method_config):
                    print(f"    {arg.name}: {getattr(method_config, arg.name)!r}")


global_config = Config()
