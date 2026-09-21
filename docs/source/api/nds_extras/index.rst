ND Slicer Extras
****************

Slicers for data sources that require an optional dependency. Each module is named
after the library that it requires and is imported when you access it, ex.
``fpl.nds_extras.pandas``. Accessing one whose library is not installed raises
``ModuleNotFoundError`` naming the package to install.

.. toctree::
    :maxdepth: 1

    pandas
