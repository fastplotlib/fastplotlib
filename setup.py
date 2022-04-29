from setuptools import setup

setup(
    name='fastplotlib',
    version='0.1.0.a1',
    packages=['fastplotlib'],
    url='https://github.com/kushalkolar/fastplotlib',
    license='Apache 2.0',
    author='Kushal Kolar',
    author_email='',
    python_requires='>=3.8',
    install_requires=['numpy', 'pygfx', 'jupyterlab', 'jupyter_rfb'],
    description='A fast plotting library built using the pygfx render engine'
)
