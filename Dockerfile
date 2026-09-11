# start with nvidia docker
FROM --platform=linux/amd64 nvidia/cuda:12.4.1-cudnn-devel-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive

# get system dependencies
# minimal for using WGPU
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        build-essential \
        libvulkan1 \
        mesa-vulkan-drivers \
        xserver-xorg-core \

# for building python
RUN apt-get update && apt-get install -y --no-install-recommends \
        gdb lcov pkg-config \
        libbz2-dev libffi-dev libgdbm-dev libgdbm-compat-dev liblzma-dev \
        libncurses5-dev libreadline6-dev libsqlite3-dev libssl-dev \
        lzma lzma-dev tk-dev uuid-dev zlib1g-dev

# for faster remote frame buffer \
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg-turbo8-dev \
        libturbojpeg0-dev \

# build python from source, use conda instead if you prefer that
RUN wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
RUN tar -xvzf ./Python-3.11.9
WORKDIR Python-3.11.9/
RUN ./configure --enable-optimizations
RUN make -j 7
RUN altinstall
WORKDIR $HOME

# make a venv and activate
RUN python3 -m venv ./venv
RUN source ./venv/bin/activate

# install pip packages
RUN pip install setuptools --upgrade && pip install --upgrade pip
RUN pip install setuptools wheel
RUN pip install simplejpeg jupyterlab jupyter-rfb pygfx

# install fpl
RUN git clone https://github.com/fastplotlib/fastplotlib.git
WORKDIR fastplotlib/
RUN pip install -e .

ENTRYPOINT [ "/bin/bash" ]
