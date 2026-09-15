from __future__ import annotations
from collections.abc import Callable
from dataclasses import make_dataclass, field, fields, dataclass, asdict
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


class ConfigDescriptor:
    """Descriptor pattern so classes can access their configuration for users to set/get config options"""

    def __init__(self, classes):
        self.__classes = classes

    def __get__(self, instance, cls: type = None):
        if instance is not None:
            raise AttributeError("set config options on the class, not an instance")

        if cls not in self.__classes:
            raise AttributeError("Class is not registered")

        return self.__classes[cls]

    def __set__(self, obj, value):
        raise AttributeError("Cannot set")


def identify(val):
    return val


def merge(current, new):
    # nested kwargs, e.g. frame_kwargs["title_kwargs"], merge instead of replacing
    if not (isinstance(current, dict) and isinstance(new, dict)):
        return new

    merged = dict(current)
    for key, value in new.items():
        merged[key] = merge(current.get(key), value)

    return merged


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


def _config_to_dict(self) -> dict:
    """
    get the current method config as a dict
    do this instead of `asdict()` from dataclasses because that creates a copy
    """
    return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class Pending:
    """
    A method that is 'pending', waiting for the class to be registered.

    These are created for decorated methods with `@GlobalConfig.declare()`.
    They are converted to the config dataclass using the `to_config()` method
    once the python interpreter reaches the `@GlobalConfig.register` for the
    created class.

    """

    method: Callable  # the actual method obj
    configurable: tuple[str, ...]

    @property
    def name(self) -> str:
        """method's name as a string, resolves __init__ -> init"""
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
        """check if other Pending object belongs to the same class as this one"""
        return self.cls_qual == other.cls_qual

    def belongs_to(self, cls: type) -> bool:
        """check if this module belongs to this fully created class object, used for @GlobalConfig.register"""
        return self.cls_qual == (cls.__module__, cls.__qualname__)

    def to_config(self) -> object:
        """create the config dataclass for this method"""
        if "to_dict" in self.configurable:
            raise ValueError(
                "`to_dict` is not a valid configurable argument name "
                "since this is reserved for the configuration system."
            )

        type_hints = get_type_hints(self.method)

        params = inspect.signature(self.method).parameters

        invalid_args = set(self.configurable) - set(params.keys())

        if invalid_args:
            raise LookupError(
                f"{self.method.__qualname__}: `@global_config.declare` lists {invalid_args} as configurable "
                f"but they are not valid arguments for this method. Valid arguments are: {params.keys()}"
            )

        missing_defaults = [
            arg
            for arg in self.configurable
            if params[arg].default is inspect.Parameter.empty
        ]
        if missing_defaults:
            raise ValueError(
                f"{self.method.__qualname__}: `@global_config.declare` lists {missing_defaults} as configurable "
                f"arguments but they do not have a default value set in the function signature. A default value "
                f"is required to initialize the default configuration"
            )

        signature = list()
        for arg in self.configurable:
            # if the type isn't declared in the function signature fill with Any
            type_annot = type_hints.get(arg, Any)

            # get the default value
            val = params[arg].default

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
                "to_dict": _config_to_dict,
            },
        )

        return mc()


class GlobalConfig:
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
        """Register a class to the GlobalConfig"""
        if self._pending and not self._pending[-1].belongs_to(cls):
            raise TypeError(
                f"{self._pending[-1].cls_qual} is not registered with the global config"
            )

        for parent in cls.__mro__:
            # can't use getattr since that will call ConfigDescriptor.__get__
            # getting it from __dict__ provides the actual descriptor object
            if isinstance(parent.__dict__.get("config"), ConfigDescriptor):
                break

        else:
            raise AttributeError(
                f"{cls} is registered with @global_config.register but doesn't have a "
                f"config descriptor class attribute."
            )

        method_configs = {p.name: p.to_config() for p in self._pending}

        # derive any un-set methods from closest parent class that has it
        # this is mainly for the ImguiFigure class
        # we want ImguiFigure.config.init to just use Figure.config.init
        parents = cls.__mro__[1:-1]  # [1:-1] skips the class itself and bare object
        for parent in parents:
            if parent in self._registry:
                # get the names of all configurable methods on this parent
                for f in fields(self._registry[parent]):
                    # if the parent has a configurable method that this subclass doesn't have defaults for
                    if f.name not in method_configs and hasattr(
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

    def declare(self, *configurable):
        """
        Declare configurable arguments for a method.
        """
        if not configurable:
            raise IndexError(
                "No configurable arguments declared, this cannot be left empty. "
                "Either declare configurable arguments or don't decorate this method."
            )

        def append_to_config(method):
            new_pending = Pending(method, configurable)
            if self._pending and not new_pending.is_sibling(self._pending[-1]):
                raise TypeError(
                    f"{self._pending[-1].cls_qual} is not registered with the global config"
                )

            self._pending.append(new_pending)

            # keep these to use them in the injector
            method_name = new_pending.name
            # create signature object just once when the method is decorated instead of every time the method is called
            sig = inspect.signature(method)

            # NOTE: variables within here are available in the injector because they exist in its __closure__
            # any variables from the outer function that are used in the inner function are always in the __closure__
            # source: https://stackoverflow.com/questions/14413946/what-exactly-is-contained-within-a-obj-closure
            # official docs: https://docs.python.org/3/reference/datamodel.html#function.__closure__

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

                config_dict = method_config.to_dict()
                # merge config values with the binding
                # any values that the user explicitly provided will be in binding.arguments
                # therefore an explicit user provided value will override the config value
                binding.arguments = {**config_dict, **binding.arguments}

                # apply any missing default vals from the method signature
                # this isn't actually necessary but is just a robust failsafe
                # I think it should account for any weirdness with methods that have positional-only arguments
                binding.apply_defaults()

                # finally call method with updated binding from config
                return method(*binding.args, **binding.kwargs)

            return injector

        return append_to_config

    def update(self, method_config, **options):
        """
        Set config options for a method, merging into what is already configured.

        A dict value is merged key by key, recursing into nested dicts, so keys set by an
        earlier call are kept unless this call names them. Any other value replaces what is
        there. This is what makes the options that are themselves kwargs composable, e.g.
        with ``Subplot.config.init.frame_kwargs`` already
        ``{"title_kwargs": {"face_color": "black"}}``::

            global_config.update(
                Subplot.config.init, frame_kwargs={"title_kwargs": {"font_size": 10}}
            )
            # -> {"title_kwargs": {"face_color": "black", "font_size": 10}}
        """
        for option, value in options.items():
            setattr(method_config, option, merge(getattr(method_config, option), value))

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


global_config = GlobalConfig()
