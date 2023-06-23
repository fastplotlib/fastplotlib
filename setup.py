from setuptools import setup, find_packages
from pathlib import Path


install_requires = [
    'numpy',
    'pygfx>=0.1.13',
]


extras_require = {
    "docs": [
        "sphinx",
        "pydata-sphinx-theme<0.10.0",
        "glfw",
        "jupyter_rfb"  # required so ImageWidget docs show up
    ],

    "notebook":
    [
        'jupyterlab',
        'jupyter-rfb',
    ],

    "tests":
    [
        "pytest",
        "nbmake",
        "scipy",
        "imageio",
        "jupyterlab",
        "jupyter-rfb",
        "scikit-learn",
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

]


setup(
    name='fastplotlib',
    version=ver,
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    url='https://github.com/kushalkolar/fastplotlib',
    license='Apache 2.0',
    author='Kushal Kolar',
    author_email='',
    python_requires='>=3.8',
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    description='A fast plotting library built using the pygfx render engine'
)
