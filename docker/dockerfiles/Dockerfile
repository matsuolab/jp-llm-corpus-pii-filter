FROM ubuntu:22.04

# Copy necessary files to temporary working directory `/workspace` for build
RUN mkdir -p /workspace
COPY install_mecab_ipadic/mecab-ipadic-2.7.0-20070801.tar.gz /workspace/
COPY install_mecab_ipadic/mecabrc_for_mecab_python /workspace/
COPY requirements.txt /workspace/

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
RUN cd /workspace && tar zxfv mecab-ipadic-2.7.0-20070801.tar.gz
RUN cd /workspace/mecab-ipadic-2.7.0-20070801 && ./configure --with-charset=utf8 --enable-utf8-only --with-dicdir=/usr/local/lib/mecab/dic/ipadic
RUN cd /workspace/mecab-ipadic-2.7.0-20070801 && make
RUN cd /workspace/mecab-ipadic-2.7.0-20070801 && make install
# cp mecab-setting for mecab-python
RUN cp /workspace/mecabrc_for_mecab_python /usr/local/etc/mecabrc
RUN chmod 777 /usr/local/etc/mecabrc

### Install python libralies
RUN pip3 install --upgrade pip
RUN cd /workspace && pip3 install -r requirements.txt
