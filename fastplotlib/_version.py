__version__ = "0.5.0"

version_info = tuple(
    int(i) if i.isnumeric() else i for i in __version__.split("+")[0].split(".")
)
