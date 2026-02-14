import importlib

from .core import NDPositions, NDPositionsProcessor

class Extras:
    pass

ndp_extras = Extras()


for optional in ["pandas", "zarr"]:
    try:
        importlib.import_module(optional)
    except ImportError:
        pass
    else:
        module = importlib.import_module(f"._{optional}", "fastplotlib.widgets.nd_widget._nd_positions")
        cls = getattr(module, f"NDPP_{optional.capitalize()}")
        setattr(
            ndp_extras,
            f"NDPP_{optional.capitalize()}",
            cls
        )
