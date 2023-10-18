from setuptools import setup, find_packages
from pathlib import Path


install_requires = [
    "numpy>=1.23.0",
    "pygfx>=0.1.14",
]


extras_require = {
    "docs": [
        "sphinx",
        "furo",
        "glfw",
        "jupyter-rfb>=0.4.1",  # required so ImageWidget docs show up
        "ipywidgets>=8.0.0,<9",
        "sphinx-copybutton",
        "sphinx-design",
        "nbsphinx",
        "pandoc",
        "jupyterlab",
        "sidecar"
    ],

    "notebook":
    [
        "jupyterlab",
        "jupyter-rfb>=0.4.1",
        "ipywidgets>=8.0.0,<9",
        "sidecar"
    ],

    "tests":
    [
        "pytest",
        "nbmake",
        "scipy",
        "imageio",
        "jupyterlab",
        "jupyter-rfb>=0.4.1",
        "ipywidgets>=8.0.0,<9",
        "scikit-learn",
        "tqdm",
        "sidecar"
    ],

    "tests-desktop":
    [
        "pytest",
        "scipy",
        "imageio",
        "scikit-learn",
        "tqdm",
    ]
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
    name='fastplotlib',
    version=ver,
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    url='https://github.com/fastplotlib/fastplotlib',
    license='Apache 2.0',
    author='Kushal Kolar, Caitlin Lewis',
    author_email='',
    python_requires='>=3.9',
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    description='A fast plotting library built using the pygfx render engine'
)

