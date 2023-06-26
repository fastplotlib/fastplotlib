from typing import *

import numpy
import weakref

from ..graphics import *


class GraphicMethodsMixin:
    def __init__(self):
        pass

    def add_heatmap(self, data: Any, vmin: int = None, vmax: int = None, cmap: str = 'plasma', filter: str = 'nearest', chunk_size: int = 8192, isolated_buffer: bool = True, *args, **kwargs) -> weakref.proxy(HeatmapGraphic):
        """
        
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            Tensorflow Tensors also work **probably**, but not thoroughly tested
            | shape must be ``[x_dim, y_dim]``
        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided
        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided
        cmap: str, optional, default "plasma"
            colormap to use to display the data
        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"
        chunk_size: int, default 8192, max 8192
            chunk size for each tile used to make up the heatmap texture
        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.
        args:
            additional arguments passed to Graphic
        kwargs:
            additional keyword arguments passed to Graphic


        Features
        --------

        **data**: :class:`.HeatmapDataFeature`
            Manages the data buffer displayed in the HeatmapGraphic

        **cmap**: :class:`.HeatmapCmapFeature`
            Manages the colormap

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene


        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            # create a `Plot` instance
            plot = Plot()

            # make some random 2D heatmap data
            data = np.random.rand(10_000, 8_000)

            # add a heatmap
            plot.add_heatmap(data=data)

            # show the plot
            plot.show()
        
        """
        g = HeatmapGraphic(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_histogram(self, data: numpy.ndarray = None, bins: Union[int, str] = 'auto', pre_computed: Dict[str, numpy.ndarray] = None, colors: numpy.ndarray = 'w', draw_scale_factor: float = 100.0, draw_bin_width_scale: float = 1.0, **kwargs) -> weakref.proxy(HistogramGraphic):
        """
        
        Create a Histogram Graphic

        Parameters
        ----------
        data: np.ndarray or None, optional
            data to create a histogram from, can be ``None`` if pre-computed values are provided to ``pre_computed``

        bins: int or str, default is "auto", optional
            this is directly just passed to ``numpy.histogram``

        pre_computed: dict in the form {"hist": vals, "bin_edges" : vals}, optional
            pre-computed histogram values

        colors: np.ndarray, optional

        draw_scale_factor: float, default ``100.0``, optional
            scale the drawing of the entire Graphic

        draw_bin_width_scale: float, default ``1.0``
            scale the drawing of the bin widths

        kwargs
            passed to Graphic
        
        """
        g = HistogramGraphic(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_image(self, data: Any, vmin: int = None, vmax: int = None, cmap: str = 'plasma', filter: str = 'nearest', isolated_buffer: bool = True, *args, **kwargs) -> weakref.proxy(ImageGraphic):
        """
        
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            Tensorflow Tensors also work **probably**, but not thoroughly tested
            | shape must be ``[x_dim, y_dim]`` or ``[x_dim, y_dim, rgb]``
        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided
        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided
        cmap: str, optional, default "plasma"
            colormap to use to display the image data, ignored if data is RGB
        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"
        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.
        args:
            additional arguments passed to Graphic
        kwargs:
            additional keyword arguments passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the data buffer displayed in the ImageGraphic

        **cmap**: :class:`.ImageCmapFeature`
            Manages the colormap

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene



        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            # create a `Plot` instance
            plot = Plot()
            # make some random 2D image data
            data = np.random.rand(512, 512)
            # plot the image data
            plot.add_image(data=data)
            # show the plot
            plot.show()
        
        """
        g = ImageGraphic(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_line_collection(self, data: List[numpy.ndarray], z_position: Union[List[float], float] = None, thickness: Union[float, List[float]] = 2.0, colors: Union[List[numpy.ndarray], numpy.ndarray] = 'w', alpha: float = 1.0, cmap: Union[List[str], str] = None, name: str = None, metadata: Union[list, tuple, numpy.ndarray] = None, *args, **kwargs) -> weakref.proxy(LineCollection):
        """
        
        Create a Line Collection

        Parameters
        ----------

        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        z_position: list of float or float, optional
            | if ``float``, single position will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        thickness: float or list of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, list of RGBA array, or list of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | if ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        cmap: list of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines
            **Note:** ``cmap`` overrides any arguments passed to ``colors``

        name: str, optional
            name of the line collection

        metadata: list, tuple, or array
            metadata associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        args
            passed to GraphicCollection

        kwargs
            passed to GraphicCollection


        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        .. code-block:: python

            # slice only the collection
            line_collection[10:20].colors = "blue"

            # slice the collection and a feature
            line_collection[20:30].colors[10:30] = "red"

            # the data feature also works like this

        See :class:`LineGraphic` details on the features.


        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            from fastplotlib.graphics import LineCollection

            # creating data for sine and cosine waves
            xs = np.linspace(-10, 10, 100)
            ys = np.sin(xs)

            sine = np.dstack([xs, ys])[0]

            ys = np.sin(xs) + 10
            sine2 = np.dstack([xs, ys])[0]

            ys = np.cos(xs) + 5
            cosine = np.dstack([xs, ys])[0]

            # creating plot
            plot = Plot()

            # creating a line collection using the sine and cosine wave data
            line_collection = LineCollection(data=[sine, cosine, sine2], cmap=["Oranges", "Blues", "Reds"], thickness=20.0)

            # add graphic to plot
            plot.add_graphic(line_collection)

            # show plot
            plot.show()

            # change the color of the sine wave to white
            line_collection[0].colors = "w"

            # change certain color indexes of the cosine data to red
            line_collection[1].colors[0:15] = "r"

            # toggle presence of sine2 and rescale graphics
            line_collection[2].present = False

            plot.autoscale()

            line_collection[2].present = True

            plot.autoscale()

            # can also do slicing
            line_collection[1:].colors[35:70] = "magenta"

        
        """
        g = LineCollection(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_line(self, data: Any, thickness: float = 2.0, colors: Union[str, numpy.ndarray, Iterable] = 'w', alpha: float = 1.0, cmap: str = None, z_position: float = None, collection_index: int = None, *args, **kwargs) -> weakref.proxy(LineGraphic):
        """
        
        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        thickness: float, optional, default 2.0
            thickness of the line

        colors: str, array, or iterable, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually, this
            overrides any argument passed to "colors"

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the line [x, y, z] positions data buffer, allows regular and fancy indexing.
            ex: ``scatter.data[:, 0] = 5```, ``scatter.data[xs > 5] = 3``

        **colors**: :class:`.ColorFeature`
            Manages the color buffer, allows regular and fancy indexing.
            ex: ``scatter.data[:, 1] = 0.5``, ``scatter.colors[xs > 5] = "cyan"``

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene, set to ``True`` or ``False``

        
        """
        g = LineGraphic(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_line_stack(self, data: List[numpy.ndarray], z_position: Union[List[float], float] = None, thickness: Union[float, List[float]] = 2.0, colors: Union[List[numpy.ndarray], numpy.ndarray] = 'w', cmap: Union[List[str], str] = None, separation: float = 10, separation_axis: str = 'y', name: str = None, *args, **kwargs) -> weakref.proxy(LineStack):
        """
        
        Create a line stack

        Parameters
        ----------
        data: list of array-like
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        z_position: list of float or float, optional
            | if ``float``, single position will be used for all lines
            | if ``list`` of ``float``, each value will apply to individual lines

        thickness: float or list of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, list of RGBA array, or list of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | is ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``list`` of ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        cmap: list of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines
            **Note:** ``cmap`` overrides any arguments passed to ``colors``

        name: str, optional
            name of the line stack

        separation: float, default 10
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated

        name: str, optional
            name of the line stack

        args
            passed to LineCollection

        kwargs
            passed to LineCollection


        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        .. code-block:: python

            # slice only the collection
            line_collection[10:20].colors = "blue"

            # slice the collection and a feature
            line_collection[20:30].colors[10:30] = "red"

            # the data feature also works like this

        See :class:`LineGraphic` details on the features.


        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            from fastplotlib.graphics import LineStack

            # create plot
            plot = Plot()

            # create line data
            xs = np.linspace(-10, 10, 100)
            ys = np.sin(xs)

            sine = np.dstack([xs, ys])[0]

            ys = np.sin(xs)
            cosine = np.dstack([xs, ys])[0]

            # create line stack
            line_stack = LineStack(data=[sine, cosine], cmap=["Oranges", "Blues"], thickness=20.0, separation=5.0)

            # add graphic to plot
            plot.add_graphic(line_stack)

            # show plot
            plot.show()

            # change the color of the sine wave to white
            line_stack[0].colors = "w"

            # change certain color indexes of the cosine data to red
            line_stack[1].colors[0:15] = "r"

            # more slicing
            line_stack[0].colors[35:70] = "magenta"

        
        """
        g = LineStack(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_scatter(self, data: numpy.ndarray, sizes: Union[int, numpy.ndarray, list] = 1, colors: numpy.ndarray = 'w', alpha: float = 1.0, cmap: str = None, z_position: float = 0.0, *args, **kwargs) -> weakref.proxy(ScatterGraphic):
        """
        
        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        sizes: float or iterable of float, optional, default 1.0
            size of the scatter points

        colors: str, array, or iterable, default "w"
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors"

        alpha: float, optional, default 1.0
            alpha value for the colors

        z_position: float, optional
            z-axis position for placing the graphic

        args
            passed to Graphic

        kwargs
            passed to Graphic

        Features
        --------

        **data**: :class:`.ImageDataFeature`
            Manages the scatter [x, y, z] positions data buffer, allows regular and fancy indexing.
            ex: ``scatter.data[:, 0] = 5```, ``scatter.data[xs > 5] = 3``

        **colors**: :class:`.ColorFeature`
            Manages the color buffer, allows regular and fancy indexing.
            ex: ``scatter.data[:, 1] = 0.5``, ``scatter.colors[xs > 5] = "cyan"``

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene, set to ``True`` or ``False``

        
        """
        g = ScatterGraphic(data=data, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

    def add_text(self, text: str, position: Tuple[int] = (0, 0, 0), size: int = 10, face_color: Union[str, numpy.ndarray] = 'w', outline_color: Union[str, numpy.ndarray] = 'w', outline_thickness=0, name: str = None) -> weakref.proxy(TextGraphic):
        """
        
        Create a text Graphic

        Parameters
        ----------
        text: str
            display text
        position: int tuple, default (0, 0, 0)
            int tuple indicating location of text in scene
        size: int, default 10
            text size
        face_color: str or array, default "w"
            str or RGBA array to set the color of the text
        outline_color: str or array, default "w"
            str or RGBA array to set the outline color of the text
        outline_thickness: int, default 0
            text outline thickness
        name: str, optional
            name of graphic, passed to Graphic
        
        """
        g = TextGraphic(text=text, *args, **kwargs)
        self.add_graphic(g)

        return weakref.proxy(g)

