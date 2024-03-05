This example shows how to use a zmq publisher-subscriber pattern to perform a computation in one process and visualize results in another process. First, run all cells in `multiprocessing_zmq_plot.ipynb`, and then run cells in `multiprocessing_zmq_compute.ipynb`. The raw bytes for the numpy array are sent using zmq in the compute notebook and received in the plot notebook and displayed.

For more information on zmq see: https://zeromq.org/languages/python/
