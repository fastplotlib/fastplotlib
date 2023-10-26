import fastplotlib as fpl
import imageio.v3 as iio


movie = iio.imread("imageio:cockatoo.mp4", plugin="pyav", index=None)

num_frames = movie.shape[0]
movie_width = movie.shape[2]

plot = fpl.Plot()

movie_graphic = plot.add_image(movie[0], vmin=0, vmax=movie.max())

linear_selector = movie_graphic.add_linear_selector()


def update(event):
    idx = int(num_frames * (event.pick_info["new_data"] / movie_width))
    movie_graphic.data = movie[idx]


linear_selector.selection.add_event_handler(update)

plot.show()

plot.camera.world.scale_y *= -1

if __name__ == "__main__":
    fpl.run()
