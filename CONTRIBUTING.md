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

Fastplotlib uses the [`pygfx`](https://github.com/pygfx/pygfx) rendering engine to give users a high-level scientific 
plotting library. Some degree of familiarity with [`pygfx`](https://github.com/pygfx/pygfx) or rendering engines may 
be useful depending on the type of contribution you're working on. 

There are currently 2 major subpackages within `fastplotlib`, `layouts` and `graphics`. The two user-facing public 
classes within `layouts` are `Plot` and `GridPlot`. A user is intended to create either a `Plot` or `GridPlot`, and 
then add *Graphics* to that layout, such as an `ImageGraphic`, `LineGraphic`, etc. 

### Graphics

A `Graphic` is something that can be added to a `PlotArea` (described in detail in a later section). All the various 
fastplotlib graphics, such as `ImageGraphic`, `ScatterGraphic`, etc. inherit from the `Graphic` base class in 
`fastplotlib/graphics/_base.py`. It has a few properties that mostly wrap `pygfx` `WorldObject` properties and transforms. 
These might change in the future (ex. `Graphic.position_x` etc.).

All graphics can be given a string name for the user's convenience. This allows graphics to be easily accessed from 
plots, ex: `plot["some_image"]`.

All graphics contain a `world_object` property which is just the `pygfx.WorldObject` that this graphic uses. Fastplotlib 
keeps a *private* global dictionary of all `WorldObject` instances and users are only given a weakref proxy to this world object. 
This is due to garbage collection. This may be quite complicated for beginners, for more details see this PR: https://github.com/fastplotlib/fastplotlib/pull/160 . 
If you are curious or have more questions on garbage collection in fastplotlib you're welcome to post an issue :D. 

#### Graphic Features

There is one important thing that `fastplotlib` uses which we call "graphic features". 
The "graphic features" subpackage can be found at `fastplotlib/graphics/_features`. As we can see this 
is a private subpackage and never meant to be accessible to users. In `fastplotlib` "graphic features" are the various 
aspects of a graphic that the user can change. Users can also run callbacks whenever a graphic feature changes.

##### LineGraphic

For example let's look at `LineGraphic` in `fastplotlib/graphics/line.py`. Every graphic has a class variable called 
`feature_events` which is a set of all graphic features. It has the following graphic features: "data", "colors", "cmap", "thickness", "present".

Now look at the constructor for `LineGraphic`, it first creates an instance of `PointsDataFeature`. This is basically a 
class that wraps the positions buffer, the vertex positions that define the line, and provides additional useful functionality. 
For example, every time that the `data` is changed event handlers will be called (if any event handlers are registered). 

`ColorFeature`behaves similarly, but it can perform additional parsing that can create the colors buffer from different forms of user input. For example if a user runs: 
`line_graphic.colors = "blue"`, then `ColorFeature.__setitem__()` will create a buffer that corresponds to what `pygfx.Color` thinks is "blue". 
Users can also take advantage of fancy indexing, ex: `line_graphics.colors[bool_array] = "red"` :smile: 

`LineGraphic` also has a `CmapFeature`, this is a subclass of `ColorFeature` which can parse colormaps, for example: 
`line_graphic.cmap = "jet"` or even `line_graphic.cmap[50:] = "viridis"`.

`LineGraphic` also has `ThicknessFeature` which is pretty simple, `PresentFeature` which indicates if a graphic is 
currently in the scene, and `DeletedFeature` which is useful if you need callbacks to indicate that the graphic has been 
deleted (for example, removing references to a graphic from a legend).

Other graphics have graphic features that are relevant to them, for example `ImageGraphic` has a `cmap` feature which is 
unique to images or heatmaps.

#### Selectors

Selectors are a fairly new subpackage at `fastplotlib/graphics/selectors` which is likely to change significantly 
after https://github.com/pygfx/pygfx/pull/665 . This subpackage contains selection tools, such as line selectors
(horizontal or vertical lines that can be moved), linear region selectors, and a primitive polygon drawing selection tool. 
All selector tools inherit from `BaseSelector` in `graphics/selectors/_base_selector.py` but this is likely to change 
after the aforementioned `Input` class PR in `pygfx` and after https://github.com/fastplotlib/fastplotlib/pull/413 .

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

Abstract method that must be implemented in subclasses:

* get_rect - musut return [x, y, width, height] that defines the viewport rect for this `PlotArea`

Properties specifically used by subplots in a gridplot:

* parent - A parent if relevant, used by individual `Subplots` in `GridPlot`, and by `Dock` which are "docked" subplots at the edges of a subplot.
* position - if a subplot within a gridplot, it is the position of this subplot within the `GridPlot`

Other important properties:

* graphics - a tuple of weakref proxies to all `Graphics` within this `PlotArea`, users are only given weakref proxies to `Graphic` objects, all `Graphic` objects are stored in a private global dict.
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

There's one more class to talk about, `Frame`. This is a class that "frames" a `Plot` or `GridPlot`. Depending on 
whether the plot's `Canvas` is a Qt or jupyter canvas, `Frame.show()` will create a plot toolbar and place this toolbar 
below the `Canvas`. If using a glfw canvas it just returns the canvas.

`Plot` and `GridPlot` both inherit from `Frame` which gives them `show()`. `Plot` is just a single `Subplot` with the 
addition of `Frame`. `GridPlot.__init__` basically does a lot of parsing of user arguments to determine how to create 
the subplots. All subplots within a `GridPlot` share the same canvas and use different viewports to create the subplots.

## Running tests

The CI pipeline for a plotting library is is supposed to produce things that "look visually correct" is a bit more 
complicated than the CI pipeline for most libraries. 

Our CI pipeline is modelled after `pygfx`. Basically, a bunch of examples exist within the `examples` dir. Each of these 
examples are run and a screenshot of the canvas is taken and compared with a ground-truth screenshot that we have 
manually inspected. Screenshots are stored using `git-lfs`.

At the moment these tests will produce slightly different imperceptible (to a human) results on different hardware, but 
nonetheless the image arrays will have a small difference. Because of this, we only run tests on GitHub actions. There 
is a specific actions workflow that only generate screenshots and doesn't run tests which is run specifically to create 
ground-truth screenshot on GitHub actions servers to use for test. 

If your contribution modifies a ground-truth test screenshot the general workflow is like this, if you have questions 
don't hesitate to ask us :smile: 

1. Create a PR with your code changes, **do not upload any new/modified test screenshots"
1. See if the CI failed, if so it will indicate the specific examples that have failed.
1. Go to the details page for the "Screenshots / Regenerate" workflow. Click on "Summary" in the top left, and download 
the build artifact which is named "screenshots". This is a zip file of generated ground-truth screenshots.
1. Visually inspect the specific new/modified screenshot that corresponds to your code change. Make sure it looks like, 
past a copy of it in the PR as a reply
1. Copy over the new/modified screenshots to your local repo.
1. Add and commit the new/modified screenshot files, and push. The tests should now pass.
