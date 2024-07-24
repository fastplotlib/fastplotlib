fastplotlib FAQ
===============

.. dropdown:: What is `fastplotlib`?

    `fastplotlib` is a scientific plotting library built on top of the `pygfx <https://github.com/pygfx/pygfx>`_ rendering engine
    that leverages new graphics APIs and modern GPU hardware to create fast and interactive visualizations.


.. dropdown:: What can I do with `fastplotlib`?

    `fastplotlib` allows for:
        - interactive visualization via an intuitive and expressive API
        - rapid prototyping and algorithm design
        - easy exploration and rendering of large-scale data

.. dropdown:: How does `fastplotlib` relate to `matplotlib`?

    `fastplotlib` is **NOT** related to `matplotlib` in any way.

    These are two completely different libraries with their own APIs and use-cases. The `fastplotlib` library is primarily for *interactive*
    visualization that runs on the GPU using WGPU.

.. dropdown:: How can I learn to use `fastplotlib`?

    We want `fastplotlib` to be easy to learn and use. To get started with the library we recommend taking a look at our `guide <https://fastplotlib.readthedocs.io/en/latest/user_guide/guide.html>`_ and
    `examples gallery <https://fastplotlib.readthedocs.io/en/latest/_gallery/index.html>`_.

    In general, if you are familiar with numpy and array notation you will already have a intuitive understanding of interacting
    with your data in `fastplotlib`. If you have any questions, please do not hesitate to post an issue or discussion forum post.

.. dropdown:: Should I use `fastplotlib` for making publication figures?

    **NO!** `fastplotlib` is not meant for creating *static* publication figures. There are many other libraries that are well-suited
    for this task.

.. dropdown:: How does `fastplotlib` handle data loading?

    `fastplotlib` is a plotting library and **NOT** a data handling or data loading library. These tasks are outside of the scope of
    the library.

    In general, if your data is an array-like object, `fastplotlib` should be able to use it.

