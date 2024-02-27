.. fastplotlib documentation master file, created by
   sphinx-quickstart on Wed Dec 28 12:46:56 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to fastplotlib's documentation!
=======================================

.. toctree::
    :caption: Quick Start
    :maxdepth: 2
    
    quickstart

.. toctree::
   :caption: User Guide
   :maxdepth:  1

   GPU Info <user_guide/gpu>

.. toctree::
   :maxdepth: 1
   :caption: API
   
   Plot <api/layouts/plot>
   Gridplot <api/layouts/gridplot>
   Subplot <api/layouts/subplot>
   Graphics <api/graphics/index>
   Graphic Features <api/graphic_features/index>
   Selectors <api/selectors/index>
   Widgets <api/widgets/index>
   Utils <api/utils>

Summary
=======

A fast plotting library built using the `pygfx <https://github.com/pygfx/pygfx>`_ render engine utilizing `Vulkan <https://en.wikipedia.org/wiki/Vulkan>`_, `DX12 <https://en.wikipedia.org/wiki/DirectX#DirectX_12>`_, or `Metal <https://developer.apple.com/metal/>`_ via `WGPU <https://github.com/gfx-rs/wgpu-native>`_, so it is very fast! We also aim to be an expressive plotting library that enables rapid prototyping for large scale explorative scientific visualization. `fastplotlib` will run on any framework that ``pygfx`` runs on, this includes ``glfw``, ``Qt`` and ``jupyter lab``



Installation
============

For installation please see the instructions on GitHub:

https://github.com/kushalkolar/fastplotlib#installation

FAQ
===

1. Axes, axis, ticks, labels, legends

A: They are on the `roadmap <https://github.com/fastplotlib/fastplotlib/issues/55>`_ and expected by summer 2024 :)

2. Why the parrot logo?

A: The logo is a `swift parrot <https://en.wikipedia.org/wiki/Swift_parrot>`_, they are the fastest species of parrot and they are colorful like fastplotlib visualizations :D 

Contributing
============

Contributions are welcome! See the contributing guide on GitHub: https://github.com/kushalkolar/fastplotlib/blob/master/CONTRIBUTING.md.

Also take a look at the `Roadmap 2025 <https://github.com/kushalkolar/fastplotlib/issues/55>`_ for future plans or ways in which you could contribute.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
