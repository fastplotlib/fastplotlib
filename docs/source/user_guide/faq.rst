fastplotlib FAQ
===============

.. dropdown:: What is `fastplotlib`?

    `fastplotlib` is a scientific plotting library built on top of the `pygfx <https://github.com/pygfx/pygfx>`_ rendering engine
    that leverages new graphics APIs and modern GPU hardware to create fast and interactive visualizations.


.. dropdown:: What can I do with `fastplotlib`?

    `fastplotlib` allows for:
        - interactive visualization via an intuitive and expressive API
        - rapid prototyping and algorithm design
        - easy exploration and fast rendering of large-scale data

.. dropdown:: How does `fastplotlib` relate to `matplotlib`?

    `fastplotlib` is **not** related to `matplotlib` in any way.

    These are two completely different libraries with their own APIs and use-cases. The `fastplotlib` library is primarily for *interactive*
    visualization that runs on the GPU using WGPU. The `fastplotlib` architecture is completely different from `matplotlib`. Using `fastplotlib`
    is more akin to using `numpy`. See the "How can I learn to use `fastplotlib`?" section below.

.. dropdown:: How can I learn to use `fastplotlib`?

    We want `fastplotlib` to be easy to learn and use. To get started with the library we recommend taking a look at our `guide <https://fastplotlib.readthedocs.io/en/latest/user_guide/guide.html>`_ and
    `examples gallery <https://fastplotlib.readthedocs.io/en/latest/_gallery/index.html>`_.

    In general, if you are familiar with numpy and array notation you will already have a intuitive understanding of interacting
    with your data in `fastplotlib`. If you have any questions, please do not hesitate to post an issue or discussion forum post.

.. dropdown:: Should I use `fastplotlib` for making publication figures?

    No, `fastplotlib` is not meant for creating *static* publication figures. There are many other libraries that are well-suited
    for this task.

.. dropdown:: How does `fastplotlib` handle data loading?

    `fastplotlib` is a plotting library and not a data handling or data loading library. These tasks are outside of the scope of
    the library.

    In general, if your data is an array-like object, `fastplotlib` should be able to use it.

.. dropdown:: What is the scope of `fastplotlib'?

    While the capabilities are very far-reaching, we would like to emphasize that `fastplotlib` is a general-purpose plotting library focused on scientific visualization.
    More specifically, we aim to develop the tools necessary for users to build fast and interactive visualizations for a variety of scientific domains (e.g. neuroscience,
    astrophysics). If you have a particular feature in mind that you feel is missing, please post an issue and we will respond accordingly letting you know if it fits within
    the scope of the project.

.. dropdown:: What types of PRs are we willing to accept?

    Primarily the features of `fastplotlib` have been developed as they relate to the core-developers research use cases (mostly neuroscience). With that being said, there are many domains in which
    we do not have the knowledge to best-implement the tools needed for proper visualization. We welcome all PRs that address these types of missing functionality. We
    recommend taking a look at our `Roadmap <https://github.com/fastplotlib/fastplotlib/issues/55>`_ to get a better idea of what those items might be :D

    Closely related to this, we would love to add more examples to our repo for different types of scientific visualizations. We welcome all PRs that showcase using `fastplotlib` for
    your given research domain.

    Lastly, documentation is a critical part of open-source software and makes learning/using our tool much easier. We welcome all PRs that add missing or needed documentation of the
    codebase. If you find a piece of the codebase that is confusing or does not have proper documentation, please also feel free to post an issue on the repo!
