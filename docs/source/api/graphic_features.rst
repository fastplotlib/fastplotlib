.. _api_graphic_features:

Graphic Features
****************

FeatureEvent
############

    Dataclass that holds feature event information. Has ``type`` and ``pick_info`` attributes.

    **Attributes**

    - type: ``str``, example "colors"

    - pick_info: ``dict`` in the form:

        ============== =============================================================================
        key             value
        ============== =============================================================================
        "index"         indices where feature data was changed, ``range`` object or ``List[int]``
        "world_object"  world object the feature belongs to
        "new_data:      the new data for this feature
        ============== =============================================================================

Image
#####

.. autoclass:: fastplotlib.graphics.features.ImageDataFeature
    :members:
    :inherited-members: 
    :exclude-members: __init__
    :no-undoc-members:
    
.. autoclass:: fastplotlib.graphics.features.ImageCmapFeature
    :members:
    :inherited-members: 
    :exclude-members: __init__
    :no-undoc-members:
    
Heatmap
#######

.. autoclass:: fastplotlib.graphics.features.HeatmapDataFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

.. autoclass:: fastplotlib.graphics.features.HeatmapCmapFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

Line
####

.. autoclass:: fastplotlib.graphics.features.PointsDataFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

.. autoclass:: fastplotlib.graphics.features.ColorFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

.. autoclass:: fastplotlib.graphics.features.ThicknessFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

Scatter
#######

.. autoclass:: fastplotlib.graphics.features.PointsDataFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

.. autoclass:: fastplotlib.graphics.features.ColorFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:

Common
######

Features common to all graphics

.. autoclass:: fastplotlib.graphics.features.PresentFeature
    :members:
    :inherited-members:
    :exclude-members: __init__
    :no-undoc-members:
