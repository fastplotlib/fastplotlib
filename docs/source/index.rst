Welcome to fastplotlib's documentation!
=======================================

.. toctree::
   :caption: Getting started
   :maxdepth:  2

   user_guide/index

.. toctree::
   :maxdepth: 2
   :caption: API

   api/index

.. toctree::
   :caption: Gallery
   :maxdepth: 1

   _gallery/index

Summary
=======

Next-gen plotting library built using the `pygfx <https://github.com/pygfx/pygfx>`_ render engine utilizing
`Vulkan <https://en.wikipedia.org/wiki/Vulkan>`_, `DX12 <https://en.wikipedia.org/wiki/DirectX#DirectX_12>`_, or
`Metal <https://developer.apple.com/metal/>`_ via `WGPU <https://github.com/gfx-rs/wgpu-native>`_, so it is very fast!
``fastplotlib`` is an expressive plotting library that enables rapid prototyping for large scale exploratory scientific
visualization. ``fastplotlib`` will run on any framework that ``pygfx`` runs on, this includes ``glfw``, ``Qt``
and ``jupyter lab``

Installation
============

Install via pip:

.. code-block::

    # with imgui and jupyterlab
    pip install -U "fastplotlib[notebook,imgui]"

    # minimal install, install glfw, pyqt6 or pyside6 separately
    pip install -U fastplotlib

    # with imgui
    pip install -U "fastplotlib[imgui]"

    # to use in jupyterlab, no imgui
    pip install -U "fastplotlib[notebook]"

Contributing
============

Contributions are welcome! See the `contributing guide on GitHub <https://github.com/fastplotlib/fastplotlib/blob/main/CONTRIBUTING.md>`_

Also take a look at the `Roadmap 2025 <https://github.com/fastplotlib/fastplotlib/issues/55>`_ for future plans or ways in which you could contribute.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
