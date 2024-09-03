fastplotlib FAQ
===============

What is `fastplotlib`?
----------------------

    `fastplotlib` is a scientific plotting library built on top of the `pygfx <https://github.com/pygfx/pygfx>`_ rendering engine
    that leverages new graphics APIs and modern GPU hardware to create fast and interactive visualizations.


What can I do with `fastplotlib`?
---------------------------------

    `fastplotlib` allows for:
        - GPU accelerated visualization
        - interactive visualization via an intuitive and expressive API
        - rapid prototyping and algorithm design
        - easy exploration and fast rendering of large-scale data
        - design, develop, evaluate and ship machine learning models
        - create visualizations for real-time acquisition systems for scientific instruments (cameras, etc.)

Do I need a GPU?
----------------

    Integrated GPUs, such as those found in modern laptops is sufficient for many use cases.

    For the best performance you will require a dedicated GPU. You can think of it like running a game, a more complex visualization or faster rendering will require a better GPU.

    Limited software rendering using just the CPU is supported on linux using lavapipe, but this is mostly only useful for testing purposes.

How does `fastplotlib` relate to `matplotlib`?
----------------------------------------------

    `fastplotlib` is **not** related to `matplotlib` in any way.

    These are two completely different libraries with their own APIs and use-cases. The `fastplotlib` library is primarily for *interactive*
    visualization that runs on the GPU using WGPU. The `fastplotlib` architecture is completely different from `matplotlib`. Using `fastplotlib`
    is more akin to using `numpy`.

    To expand on this a bit more, the `pygfx` buffer interface is really unlike anything in`matplotlib` and other libraries which is a major reason
    why `fastplotlib` can have an array-like API for plotting. We believe that these design choices make it much easier to learn how to use the library
    and provide fine-grained control over your visualizations. See the "How can I learn to use `fastplotlib`?" section below.

How can I learn to use `fastplotlib`?
-------------------------------------

    We want `fastplotlib` to be easy to learn and use. To get started with the library we recommend taking a look at our `guide <https://fastplotlib.readthedocs.io/en/latest/user_guide/guide.html>`_ and
    `examples gallery <https://fastplotlib.readthedocs.io/en/latest/_gallery/index.html>`_.

    In general, if you are familiar with numpy and array notation you will already have a intuitive understanding of interacting
    with your data in `fastplotlib`. If you have any questions, please do not hesitate to post an issue or discussion forum post.

Should I use `fastplotlib` for making publication figures?
----------------------------------------------------------

    While `fastplotlib` figures can be exported to PNG using ``figure.export()``, `fastplotlib` is not intended for creating *static*
    publication figures. There are many other libraries that are well-suited for this task.

How does `fastplotlib` handle data loading?
-------------------------------------------

    `fastplotlib` is a plotting library and not a data handling or data loading library. These tasks are outside of the scope of
    the library.

    In general, if your data is an array-like object, `fastplotlib` should be able to use it. However, if you have any problems using your data objects,
    please do not hesitate to post an issue! See this `issue <https://github.com/fastplotlib/fastplotlib/issues/483>`_ for more details.

What is the scope of `fastplotlib`?
-----------------------------------

    While the capabilities are very far-reaching, we would like to emphasize that `fastplotlib` is a general-purpose plotting library focused on scientific visualization.
    More specifically, we aim to develop the tools necessary for users to build fast and interactive visualizations for a variety of scientific domains including but not limited to
    neuroscience, astronomy, biology, computer vision, signal processing, and more. If you have a particular feature in mind that you feel is missing, please post an issue and we will respond
    accordingly letting you know if it fits within the scope of the project.

What types of PRs are we willing to accept?
-------------------------------------------

    Primarily the features of `fastplotlib` have been developed as they relate to the core-developers research use cases (mostly neuroscience, algorithm development, and machine learning). With that being said, there are many domains in which
    we do not have the knowledge to best-implement the tools needed for proper visualization. We welcome all PRs that address these types of missing functionality. We
    recommend taking a look at our `Roadmap <https://github.com/fastplotlib/fastplotlib/issues/55>`_ to get a better idea of what those items might be :D

    Closely related to this, we would love to add more examples to our repo for different types of scientific visualizations. We welcome all PRs that showcase using `fastplotlib` for
    your given research domain! :D

    Lastly, documentation is a critical part of open-source software and makes learning/using our tool much easier. We welcome all PRs that add missing or needed documentation of the
    codebase. If you find a piece of the codebase that is confusing or does not have proper documentation, please also feel free to post an issue on the repo!

What frameworks does `fastplotlib` support?
-------------------------------------------

    The short answer is that `fastplotlib` can run on anything that `pygfx` runs on. This includes,
        - `jupyter lab` using `jupyter_rfb`
        - `PyQt` and `PySide`
        - `glfw`
        - `wxPython`

    Note: Use in Google Colab is not highly functional. We recommend using an inexpensive alternative cloud provider
    such as CodeOcean or Lambda Cloud. We have tested these and `fastplotlib` works very well.

How can I use `fastplotlib` interactively?
------------------------------------------

    There are multiple ways to use fastplotlib interactively.

    1. Jupyter

    On jupyter lab the jupyter backend (i.e. jupyter_rfb) is normally selected. This works via client-server rendering.
    Images generated on the server are streamed to the client (Jupyter) via a jpeg byte stream. Events (such as mouse or keyboard events)
    are then streamed in the opposite direction prompting new images to be generated by the server if necessary.
    This remote-frame-buffer approach makes the rendering process very fast. `fastplotlib` viusalizations can be displayed
    in cell output or on the side using sidecar.

    A Qt backend can also optionally be used as well. If %gui qt is selected before importing `fastplotlib` then this
    backend will be used instead.

    Lastly, users can also force using glfw by specifying this as an argument when instantiating a
    Figure (i.e. Figure(canvas="gflw").

    **Note:** Do not mix between gui backends. For example, if you start the notebook using Qt, do not attempt to
    force using another backend such as jupyter_rfb later.

    2. IPython

    Users can select between using a Qt backend or glfw using the same methods as above.
