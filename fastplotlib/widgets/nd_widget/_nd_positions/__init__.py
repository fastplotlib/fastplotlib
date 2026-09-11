import importlib

from ._nd_positions import NDPositions, NDPositionsSlicer
from ._nd_timeseries import NDTimeseries

class Extras:
    pass

ndp_extras = Extras()


for optional in ["pandas"]:
    try:
        importlib.import_module(optional)
    except ImportError:
        pass
    else:
        module = importlib.import_module(f"._{optional}", "fastplotlib.widgets.nd_widget._nd_positions")
        cls = getattr(module, f"{optional.capitalize()}Slicer")
        setattr(
            ndp_extras,
            f"{optional.capitalize()}",
            cls
        )
