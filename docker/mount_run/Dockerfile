# Run this dockerfile under the project root directory
# $ cd <project_dir>/
# $ docker build -f ./docker/mount_run/Dockerfile -t ppi_filter_mount_run .

FROM ubuntu:22.04

# Copy [src, docker, data/db] directory to /app/
RUN mkdir -p /app/src
COPY ./src /app/src
RUN mkdir -p /app/docker
COPY ./docker /app/docker
RUN mkdir -p /app/data/db
COPY ./data/db /app/data/db


# disable interactive in install packages
ARG DEBIAN_FRONTEND=noninteractive

### Softwares
RUN apt update && \
    apt -y install emacs wget curl git

# Python
RUN apt -y install python3 python3-pip


### Support Japanese
RUN apt-get install -y locales
RUN locale-gen ja_JP.UTF-8
ENV LANG=ja_JP.UTF-8
# Time
ENV TZ=Asia/Tokyo

### MeCab
RUN apt install -y mecab libmecab-dev
# install mecab ipadic at workdir
RUN cd /app/docker/install_mecab_ipadic && tar zxfv mecab-ipadic-2.7.0-20070801.tar.gz
RUN cd /app/docker/install_mecab_ipadic/mecab-ipadic-2.7.0-20070801 && ./configure --with-charset=utf8 --enable-utf8-only --with-dicdir=/usr/local/lib/mecab/dic/ipadic
RUN cd /app/docker/install_mecab_ipadic/mecab-ipadic-2.7.0-20070801 && make
RUN cd /app/docker/install_mecab_ipadic/mecab-ipadic-2.7.0-20070801 && make install

# cp mecab-setting for mecab-python
RUN cp /app/docker/install_mecab_ipadic/mecabrc_for_mecab_python /usr/local/etc/mecabrc
RUN chmod 777 /usr/local/etc/mecabrc

### Install python libralies
RUN pip3 install --upgrade pip
RUN cd /app/docker/mount_run/ && pip3 install -r requirements.txt

### Use container for ephemeral
WORKDIR /app/src/filtering
ENTRYPOINT ["python3", "respect_PI_filter.py"]
