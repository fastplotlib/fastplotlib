import importlib
import pkgutil

# every public module in this dir is an extra, named after the library that it requires,
# i.e. `pandas.py` is `nds_extras.pandas` and requires `pandas`. They are imported on
# attribute access so an optional dependency is never imported along with fastplotlib.
_EXTRAS = sorted(
    name for _, name, _ in pkgutil.iter_modules(__path__) if not name.startswith("_")
)


def __getattr__(name: str):
    if name not in _EXTRAS:
        raise AttributeError(f"no extras module `{name}`, available extras: {_EXTRAS}")

    try:
        return importlib.import_module(f".{name}", __name__)
    except ModuleNotFoundError as e:
        if e.name != name:
            # the extras module imports something else that is missing
            raise

        raise ModuleNotFoundError(
            f"`nds_extras.{name}` requires the `{name}` package.\npip install {name}"
        ) from e


def __dir__() -> list[str]:
    return _EXTRAS
