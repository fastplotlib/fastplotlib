Flags
=====

Flags are passed as ``int``. The values are ``enum.IntFlag`` members of the classes below and can be
combined with ``|``::

    imgui.slider_float(
        "gamma", v=gamma, v_min=0.1, v_max=5.0,
        flags=imgui.SliderFlags_.logarithmic | imgui.SliderFlags_.no_input,
    )

``Col_``, ``Cond_``, ``StyleVar_`` hold single values rather than flags, they are listed here because the
elements take them.

.. _imgui.ButtonFlags_:

imgui.ButtonFlags\_
-------------------

.. imgui-flags:: ButtonFlags_

.. _imgui.ChildFlags_:

imgui.ChildFlags\_
------------------

.. imgui-flags:: ChildFlags_

.. _imgui.Col_:

imgui.Col\_
-----------

.. imgui-flags:: Col_

.. _imgui.ColorEditFlags_:

imgui.ColorEditFlags\_
----------------------

.. imgui-flags:: ColorEditFlags_

.. _imgui.ComboFlags_:

imgui.ComboFlags\_
------------------

.. imgui-flags:: ComboFlags_

.. _imgui.Cond_:

imgui.Cond\_
------------

.. imgui-flags:: Cond_

.. _imgui.FocusedFlags_:

imgui.FocusedFlags\_
--------------------

.. imgui-flags:: FocusedFlags_

.. _imgui.HoveredFlags_:

imgui.HoveredFlags\_
--------------------

.. imgui-flags:: HoveredFlags_

.. _imgui.InputTextFlags_:

imgui.InputTextFlags\_
----------------------

.. imgui-flags:: InputTextFlags_

.. _imgui.PopupFlags_:

imgui.PopupFlags\_
------------------

.. imgui-flags:: PopupFlags_

.. _imgui.SelectableFlags_:

imgui.SelectableFlags\_
-----------------------

.. imgui-flags:: SelectableFlags_

.. _imgui.SliderFlags_:

imgui.SliderFlags\_
-------------------

.. imgui-flags:: SliderFlags_

.. _imgui.StyleVar_:

imgui.StyleVar\_
----------------

.. imgui-flags:: StyleVar_

.. _imgui.TabBarFlags_:

imgui.TabBarFlags\_
-------------------

.. imgui-flags:: TabBarFlags_

.. _imgui.TabItemFlags_:

imgui.TabItemFlags\_
--------------------

.. imgui-flags:: TabItemFlags_

.. _imgui.TableColumnFlags_:

imgui.TableColumnFlags\_
------------------------

.. imgui-flags:: TableColumnFlags_

.. _imgui.TableFlags_:

imgui.TableFlags\_
------------------

.. imgui-flags:: TableFlags_

.. _imgui.TableRowFlags_:

imgui.TableRowFlags\_
---------------------

.. imgui-flags:: TableRowFlags_

.. _imgui.TreeNodeFlags_:

imgui.TreeNodeFlags\_
---------------------

.. imgui-flags:: TreeNodeFlags_

.. _imgui.WindowFlags_:

imgui.WindowFlags\_
-------------------

.. imgui-flags:: WindowFlags_

