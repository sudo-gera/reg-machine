FROM ubuntu@sha256:4e0171b9275e12d375863f2b3ae9ce00a4c53ddda176bd55868df97ac6f21a6e AS universal
RUN : change this value to rebuild whole image: 2025 10 27 01 59 39

RUN \
    apt update && \
    DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata && \
    apt install -y software-properties-common && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt update && \
    apt install -y \
        coreutils \
        gcc \
        git \
        gpg \
        libc6-dev \
        libcrypto++-dev \
        libevent-core-2.1-7 \
        libevent-dev \
        libevent-extra-2.1-7 \
        libmbedtls-dev \
        libnss3-dev \
        libssl-dev \
        lsb-release \
        python3-pip \
        python3.11-full \
        shadowsocks-libev \
        software-properties-common

RUN python3 -m pip install pytest coverage

COPY . /app

RUN git -C /app clean -f /app

RUN /app/coverage.sh

RUN echo '/app/coverage.sh' >> /root/.bash_history

CMD cd /app ; bash
