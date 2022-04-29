from setuptools import setup, find_packages

setup(
    name='fastplotlib',
    version='0.1.0.a1',
    packages=find_packages(),
    url='https://github.com/kushalkolar/fastplotlib',
    license='Apache 2.0',
    author='Kushal Kolar',
    author_email='',
    python_requires='>=3.8',
    install_requires=['numpy', 'pygfx', 'jupyterlab', 'jupyter-rfb'],
    description='A fast plotting library built using the pygfx render engine'
)
