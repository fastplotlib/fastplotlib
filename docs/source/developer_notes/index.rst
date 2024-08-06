Developer Notes
***************

Welcome to the Developer Notes for `fastplotlib`. These notes aim to provide detailed and technical information
about the various modules, classes, and functions that make up this library, as well as guidelines on how to write
code that integrates nicely with our package. They are intended to help current and future developers understand
the design decisions, and functioning of the library. Furthermore, these notes aim to provide guidance on how to
modify, extend, and maintain the codebase.

Intended Audience
-----------------

These notes are primarily intended for the following groups:

- **Current Developers**: The Developer Notes can serve as a comprehensive guide to understanding the library, making it easier to debug, modify and maintain the code.

- **Future Developers**: These notes can help onboard new developers to the project, providing them with detailed explanations of the codebase and its underlying architecture.

- **Contributors**: If you wish to contribute to the `fastplotlib` project, the Developer Notes can provide a solid foundation of understanding, helping to ensure that your contributions align with the existing structure and design principles of the library.

- **Advanced Users**: While the primary focus of these notes is on development, they might also be of interest to advanced users who want a deeper understanding of the library's functionality.

Please note that these notes assume a certain level of programming knowledge. Familiarity with Python, object-oriented programming, and the NumPy and pygfx libraries would be beneficial when reading these notes.

Navigating the Developer Notes
------------------------------

The Developer Notes are divided into sections, each focusing on a different component of the library. Each section provides an overview of the class or module, explains its role and functionality within the library, and offers a comprehensive guide to its classes and functions.
Typically, we will provide instructions on how to extend the existing modules. We generally advocate for the use of inheritance and encourage consistency with the existing codebase. In creating developer instructions, we follow the conventions outlined below:

- **Must**: This denotes a requirement. Any method or function that fails to meet the requirement will not be merged.
- **Should**: This denotes a suggestion. Reasons should be provided if a suggestion is not followed.
- **May**: This denotes an option that, if implemented, could enhance the user/developer experience but can be overlooked if deemed unnecessary.

Interact with us
----------------

If you're considering contributing to the library, first of all, welcome aboard! As a first step, we recommend that you read the [`CONTRIBUTING.md`](https://github.com/fastplotlib/fastplotlib/blob/main/CONTRIBUTING.md) guidelines.
These will help you understand how to interact with other contributors and how to submit your changes.

If you have any questions or need further clarification on any of the topics covered in these notes, please don't hesitate to reach out to us. You can do so via the [discussion](https://github.com/fastplotlib/fastplotlib/discussions/landing) forum on GitHub.

We're looking forward to your contributions and to answering any questions you might have!

.. toctree::
    :maxdepth: 1

    graphics
    layouts