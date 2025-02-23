# Contributing Guide

`fastplotlib` is a next-generation plotting library built on top of the `pygfx` rendering engine that leverages modern 
GPU hardware and new graphics APIs to build large-scale scientific visualizations. We welcome and encourage contributions
from everyone! :smile: 

This guide explains how to contribute: if you have questions about the process, please 
reach out on [GitHub Discussions](https://github.com/fastplotlib/fastplotlib/discussions).

> **_NOTE:_** If you are already familiar with contributing to open-source software packages, 
> please check out the [quick guide](#contributing-quick-guide)!

## General Guidelines

Developers are encouraged to contribute to various areas of development. This could include the addition of new features (e.g. 
graphics or selector tools), bug fixes, or the addition of new examples to the [examples gallery](https://www.fastplotlib.org/ver/dev/_gallery/index.html). 
Enhancements to documentation and the overall readability of the code are also greatly appreciated. 

Feel free to work on any section of the code that you believe you can improve. More importantly, remember to thoroughly test all
your classes and functions, and to provide clear, detailed comments within your code. This not only aids others in using the library,
but also facilitates future maintenance and further development.

For more detailed information about `fastplotlib` modules, including design choices and implementation details, visit the 
[`For Develeopers`](https://www.fastplotlib.org/ver/dev/developer_notes/index.html) section of the package documentation.

## Contributing to the code 

### Contribution workflow cycle

In order to contribute, you will need to do the following:

1) Create your own branch
2) Make sure that tests pass 
3) Open a Pull Request

The `fastplotlib` package follows the [Git feature branch](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow) workflow. In essence, `main` is the primary branch to which no one is allowed to
push directly. All development happens in separate feature branches that are then merged into `main` once we have determined they are ready. When enough changes have accumulated, a new release is 
generated. This process includes adding a new tag to increment the version number and uploading the new release to PyPI. 

### Creating a development environment

You will need a local installation of `fastplotlib` which keeps up-to-date with any changes you make. To do so, you will need to fork and clone `fastplotlib` before checking out a new branch.

1. Fork the repo to your own GitHub account, click the "Fork" button at the top:

![image](https://github.com/kushalkolar/fastplotlib/assets/9403332/82612021-37b2-48dd-b7e4-01a919535c17)

2. We use [git-lfs](https://git-lfs.com) for storing large files, such as ground-truths for tests, so you will need 
to [install it](https://github.com/git-lfs/git-lfs#installing) before cloning the repo. If you already have `git-lfs`
installed, ignore this step. 

3. Clone the repo. Replace the `YOUR_ACCOUNT` in the repo URL to the fork on your account.

```bash
git clone https://github.com/YOUR_ACCOUNT/fastplotlib.git
cd fastplotlib
```

> **_NOTE:_** If you cloned the repo before installing `git-lfs`, you can run `git lfs pull` at any
> time to download the files stored on LFS

4. Install `fastplotlib` in editable mode with developer dependencies 

```bash
# install all extras in place
pip install -e ".[imgui, notebook, docs, tests]"
```

5. Add the upstream remote branch:

```bash
git remote add upstream https://github.com/fastplotlib/fastplotlib
```

At this point you have two remotes: `origin` (your fork) and `upstream` (the official fastplotlib org version). You won't have permission to push to upstream (only `origin`), but 
this makes it easy to keep your `fastplotlib` up-to-date with the official fastplotlib org version by pulling from upstream: `git pull upstream`.

### Creating a new branch

As mentioned previously, each feature in `fastplotlib` is worked on in a separate branch. This allows multiple people to develop multiple features simultaneously, without interfering with each other's work. To create
your own branch, run the following from within your `fastplotlib` directory:

```bash
# switch to the main branch on your local copy
git checkout main

# update your local copy from your fork
git pull origin main

# sync your local copy with upstream main
git pull upstream main

# update your fork's main branch with any changes from upstream
git push origin main

# create and switch to a new branch, where you'll work on your new feature
git checkout -b my_feature_branch
```

After you have made changes on this branch, add and commit them when you are ready:

```bash
# black format only the source code
black fastplotlib/

# run tests from the repo root dir
RENDERCANVAS_FORCE_OFFSCREEN=1 pytest tests/

# desktop examples
pytest -v examples

# notebook examples
FASTPLOTLIB_NB_TESTS=1 pytest --nbmake examples/notebooks/

# add your changed files, do not add any changes from the screenshot diff directory
git add my_changed_files

# commit your changes
git commit -m "A one-line message explaining the changes made"

# push to the remote origin
git push origin my_feature_branch
```
> **_NOTE:_** If your contributions modify how visualizations _look_, see the [Testing details](#testing-details) section at the very bottom.

> **_NOTE:_** If your contributions modify the API, you must regenerate the API docs before making a PR, see
> the [Documenation](#documentation) section below.

### Contributing your changes back to `fastplotlib`

You can make any number of changes on your branch. Once you are happy with your changes, add tests to check that they run correctly and add
documentation to properly note your changes.
See below for details on how to [add tests](#adding-tests) and properly [document](#adding-documentation) your code.

Now you are ready to make a Pull Request. You can open a pull request by clicking on the big `Compare & pull request` button that appears at the top of the `fastplotlib` repo 
after pushing to your branch (see [here](https://intersect-training.org/collaborative-git/03-pr/index.html) for a tutorial).

> **_NOTE:_** Please make sure that you initially make your PR as a **draft** PR against the `main` branch. When you think the PR is ready, mark
> it for review to trigger tests using our CI pipeline. If you need to make changes, please set the PR back to a draft when pushing further
> commits until it is ready for review again.

Your pull request should include the following:
- A summary including information on what you changed and why
- References to relevant issues or discussions
- Special notice to any portion of your changes where you have lingering questions (e.g., "was this the right way to implement this?") or
want reviewers to pay special attention to

Next, we will be notified of the pull request and will read it over. We will try to give an initial response quickly, and then do a longer in-depth
review, at which point you will probably need to respond to our comments, making changes as appropriate. We will then respond again, and proceed
in an iterative fashion until everyone is happy with the proposed changes.

Once your changes are integrated, you will be added as a GitHub contributor. Thank you for being 
a part of `fastplotlib`!

### Style Guide

As far as code style, please adhere to the following guidelines:

- Longer, descriptive names are preferred (e.g., `x` is not an appropriate name for a variable), especially for anything user-facing,
such as methods, attributes, or arguments
- Any public method, property, or attribute must have complete type-annotated docstrings (see below for details). Private methods or
attributes do not need to have a complete docstring, but they probably should.

### Releases

We create releases on GitHub and distribute via [pypi](https://pypi.org/), and try to follow [semantic versioning](https://semver.org/):

> Given a version number MAJOR.MINOR.PATCH, increment the:
> 1. MAJOR version when you make incompatible API changes
> 2. MINOR version when you add functionality in a backward compatible manner
> 3. PATCH version when you make backward compatible bug fixes

To release a new version, we [create a GitHub release](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) with a new tag incrementing the version as described above. 
Creating the GitHub release will trigger the deployment to pypi, via our `deploy` action (found in `.github/workflows/pypi-publish.yml`). 
The built version will grab the version tag from the GitHub release, using [setuptools_scm](https://github.com/pypa/setuptools_scm).

### Testing 

#### Testing Details

As a plotting library we require two layers of testing. 1) We use a backend test suite that verifies the basic functionality of buffer managers, 
graphics, layouts, etc., and 2) another test suite which verifies that the library renders plots that are visually correct.

In order to do this, each example within the `examples` directory is run and an image of the canvas is taken and compared 
with a ground-truth screenshot that we have manually inspected. Ground-truth images are stored using `git-lfs`.

The ground-truth images are located in:

```
examples/desktop/screenshots
examples/notebooks/screenshots
```

The tests will produce slightly different imperceptible (to a human) results on different hardware when compared to the 
ground-truth. A small RMSE tolerance has been chosen, `0.025` for most examples. If the output image and 
ground-truth image are within that tolerance the test will pass. 

Some feature development may require the ground-truth screenshots to be updated. In the event that your changes require
this, please do the following: 

1. Download the regenerated screenshots from the [`fastplotlib` GitHub Actions page](https://github.com/fastplotlib/fastplotlib/actions/workflows/screenshots.yml) for your specific PR

2. Replace only the screenshots that your PR changes in your local `fastplotlib` screenshots directories with those downloaded 

```
examples/desktop/screenshots
examples/notebooks/screenshots
```

3. Commit your new screenshots and push them to your branch to get picked up by `git-lfs`

```bash
# add changes
git add examples/desktop/screenshots/
git add examples/notebooks/screenshots/

# commit changes
git commit -m "update screenshots"

# push changes
git push origin my_feature_branch
```

#### Adding tests

Depending on the type of contribution you are making, new tests might need to be added to the repository. Unit tests for testing underlying functionality such as buffer managers, figure instantiation, and
more can be found in the `/tests` directory. However, we also test all of our desktop examples as well. 

If you are adding a new example to the library, you will need to add the following comments to the top of your `.py` file in order to make sure it is both tested and added to the gallery. 

```python
# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'
```

### Documentation

Documentation is a crucial part of open-source software and greatly influences the ability to use a codebase. As such, it is imperative that any new changes are
properly documented as outlined below. 

We use [`sphinx`](https://www.sphinx-doc.org/en/master/) for generating our documentation. In addition to this, we also use the [`sphinx-gallery`](https://sphinx-gallery.github.io/stable/index.html)
extension to build our examples gallery.

If you would like to build the documentation locally:

```bash
cd docs
# regenerate the api guide
python source/generate_api.py

# build locally
make html
```

#### Adding documentation

All public-facing functions and classes should have complete docstrings, which start with a one-line short summary of the function, 
a medium-length description of the function / class and what it does, and a complete description of all arguments and return values. 
Docstrings should be comprehensive, providing the information necessary for a user to use the method or property without going through the code.

Private functions and classes should have sufficient explanation that other developers know what the function / class does and how to use it, 
but do not need to be as extensive.

We follow the [numpydoc](https://numpydoc.readthedocs.io/en/latest/) conventions for docstring structure.

### Contributing Quick Guide

This section is a brief introduction to how to contribute to `fastplotlib`. It is intended for individuals who have prior experience with contributing 
to open source software packages. 

> **_NOTE:_** 
> We use [git-lfs](https://git-lfs.com) for storing large files, such as ground-truths for tests, so you will need 
> to [install it](https://github.com/git-lfs/git-lfs#installing) before cloning the repo.

1) Fork and clone the repo 

2) Install locally with developer dependencies 

```bash
# after cloning
cd fastplotlib
# install dev dependencies 
pip install -e ".[imgui, tests, docs, notebook]"
```

3) Check out a feature branch from `main`

4) Lint codebase and make sure tests pass 

```bash
# black format only the source code
black fastplotlib/

# run tests 
# backend tests 
RENDERCANVAS_FORCE_OFFSCREEN=1 pytest tests/

# desktop examples
pytest -v examples

# notebook examples
FASTPLOTLIB_NB_TESTS=1 pytest --nbmake examples/notebooks/
```

5) Update screenshots if necessary ([see testing](#testing-details))

6) Push and open a PR (pull request) against the `main` branch

> **Note:**
> The tests labeled "CI / Tests" must pass, but the tests labeled "CI / Tests - pygfx release" do not necessarily need to pass. The difference between these two workflows is "CI / Tests" uses the `main` branch of [`pygfx`](https://github.com/pygfx/pygfx) whereas "CI / Tests - pygfx release" uses the latest release of `pygfx`.
> Since `fastplotlib`, `pygfx`, and `wgpu` are all under rapid development we aim to keep `fastplotlib` up to date with `pygfx@main` until `pygfx` stabilizes. The workflow "CI / Tests - pygfx release" is to inform us if any test failures using the release version of `pygfx` are a significant release blocker for `fastplotlib`. Once you make a PR we will help guide you through any failures with "CI / Tests - pygfx release"!
