from setuptools import setup, find_packages
from pathlib import Path


install_requires = [
    "numpy>=1.23.0",
    "pygfx~=0.9.0",
    "wgpu>=0.20.0",
    "cmap>=0.1.3",
]


extras_require = {
    "docs": [
        "sphinx",
        "sphinx-gallery",
        "pydata-sphinx-theme",
        "glfw",
        "ipywidgets>=8.0.0,<9",
        "sphinx-copybutton",
        "sphinx-design",
        "pandoc",
        "imageio[ffmpeg]",
        "matplotlib",
        "scikit-learn",
    ],
    "notebook": [
        "jupyterlab",
        "jupyter-rfb>=0.5.1",
        "ipywidgets>=8.0.0,<9",
        "sidecar",
    ],
    "tests": [
        "pytest",
        "nbmake",
        "black",
        "scipy",
        "imageio[ffmpeg]",
        "scikit-learn",
        "tqdm",
    ],
    "imgui": ["imgui-bundle"],
}


with open(Path(__file__).parent.joinpath("README.md")) as f:
    readme = f.read()

with open(Path(__file__).parent.joinpath("fastplotlib", "VERSION"), "r") as f:
    ver = f.read().split("\n")[0]


classifiers = [
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering :: Visualization",
    "License :: OSI Approved :: Apache Software License",
    "Intended Audience :: Science/Research",
]


setup(
    name="fastplotlib",
    version=ver,
    long_description=readme,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    url="https://github.com/fastplotlib/fastplotlib",
    license="Apache 2.0",
    author="Kushal Kolar, Caitlin Lewis",
    author_email="",
    python_requires=">=3.10",
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    description="A fast plotting library built using the pygfx render engine",
)
