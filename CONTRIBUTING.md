# Contribution guide

Contributions are welcome! :smile: 

## Installation

1. Fork the repo to your own GitHub account, click the "Fork" button at the top:

![image](https://github.com/kushalkolar/fastplotlib/assets/9403332/82612021-37b2-48dd-b7e4-01a919535c17)

2. Clone the repo and install according to the development instructions. Replace the `YOUR_ACCOUNT` in the repo URL to the fork on your account.  Note that fastplotlib uses [git-lfs](https://git-lfs.com) for storing large files, so you will need to [install it](https://github.com/git-lfs/git-lfs#installing) before cloning the repo.

```bash
git clone https://github.com/YOUR_ACCOUNT/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests]
```

> If you cloned before installing `git-lfs`, you can run `git lfs pull` at any
> time to properly download files.

3. Checkout the `main` branch, and then checkout your feature or bug fix branch, and run tests:

> **Warning**
> Do not commit or add any changes from `examples/desktop/screenshots`.
> If you are creating new test examples that generate or change screenshots please post an issue on the repo and we will help you. The screenshots will be generated on github actions servers, which you can then copy into the screenshots dir. :)

```bash
cd fastplotlib

git checkout main

# checkout your new branch from main
git checkout -b my-new-feature-branch

# make your changes
# run tests
REGENERATE_SCREENSHOTS=1 pytest -v -k examples

# make some changes, lint with black, and commit
black .

# add only your changed files, not the entire repo, do not add changes to examples/screenshots
git add my_changed_files

# commit changes
git commit -m "my new feature"

# push changes to your fork
git push origin my-new-feature-branch
```

4. Finally make a **draft** PR against the `main` branch. When you think the PR is ready, mark it for review to trigger tests using our CI pipeline. If you need to make changes, please set the PR to a draft when pushing further commits until it's ready for review scion. We will get back to your with any further suggestions!

## How fastplotlib works

Fastplotlib uses the [`pygfx`](https://github.com/pygfx/pygfx) rendering engine to give user a high-level scientific 
plotting library. Some degree of familiarity with [`pygfx`](https://github.com/pygfx/pygfx) or rendering engines may 
be useful depending on the type of contribution you're working on. 

There are currently 2 major subpackages within `fastplotlib`, `layouts` and `graphics`. The two user-facing public 
classes within `layouts` are `Plot` and `GridPlot`. A user is intended to create either a `Plot` or `GridPlot`, and 
then add *Graphics* to that layout, such as an `ImageGraphic`, `LineGraphic`, etc. 

### Layouts

#### PlotArea

This is the main base class within layouts. Every kind of "plot area", whether it's a single `Plot`, subplots within a 
`GridPlot`, or `Dock` area, use `PlotArea` in some way.

`PlotArea` has the following key properties that allow it to be a "plot area" that can be used to view graphical objects:

* scene - instance of `pygfx.Scene`
* canvas - instance of `WgpuCanvas`
* renderer - instance of `pygfx.WgpuRenderer`
* viewport - instance of `pygfx.Viewport`
* camera - instance of `pygfx.PerspectiveCamera`, we always just use `PerspectiveCamera` and just set `camera.fov = 0` for orthographic projections
* controller - instance of `pygfx.Controller`

Abstact method that must be implemented in subclasses:
* get_rect - 

Properties specifically used by subplots in a gridplot:

* parent - A parent if relevant, used by individual `Subplots` in `GridPlot`, and by `Dock` which are "docked" subplots at the edges of a subplot.
* position - if a subplot within a gridplot, it is the position of this subplot within the `GridPlot`

Other important properties:

* graphics - a tuple of weakref proxies to all `Graphics` within this `PlotArea`
* selectors - a tuple of weakref proxies to all selectors within this `PlotArea`
* legend - a tuple of weakref proxies to all legend graphics within this `PlotArea`
* name - plot areas are allowed to have names that the user can use for their convenience

Important methods:

* add_graphic - add a `Graphic` to the `PlotArea`, append to the end of the `PlotArea._graphics` list
* insert_graphic - insert a `Graphic` to the `PlotArea`, insert to a specific position of the `PlotArea._graphics` list
* remove_graphic - remove a graphic from the `Scene`, **does not delete it**
* delete_graphic - delete a graphic from the `PlotArea`, performs garbage collection
* clear - deletes all graphics from the `PlotArea`
* center_graphic - center camera w.r.t. a `Graphic`
* center_scene - center camera w.r.t. entire `Scene`
* auto_scale - Auto-scale the camera w.r.t to the `Scene`

In addition, `PlotArea` supports `__getitem__`, so you can do: `plot_area["graphic_name"]` to retrieve a `Graphic` by 
name :smile: 

You can also check if a `PlotArea` has certain graphics, ex: `"some_image_name" in plot_area`, or `graphic_instance in plot_area`

#### Subplot

This class inherits from `PlotArea` and `GraphicMethodsMixin`.

`GraphicMethodsMixin` is a simple class that just has all the `add_<graphic>` methods. It is autogenerated by a utility script like this:

```bash
python fastplotlib/utils/generate_add_methods.py
```

Each `add_<graphic>` method basically creates an instance of `Graphic`, adds it to the `Subplot`, and returns a weakref 
proxy to the `Graphic`.

Subplot has one property that is not in `PlotArea`:

* docks: a `dict` of `PlotAreas` which are located at the "top", "right", "left", and "bottom" edges of a `Subplot`. By default their size is `0`. They are useful for putting things like histogram LUT tools.

The key method in `Subplot` is an implementation of `get_rect` that returns the viewport rect for this subplot.

#### Plot, GridPlot, and Frame

Now that we have understood `PlotArea` and `Subplot` we need a way for the user to create either single plots or gridplots 
and display them!

