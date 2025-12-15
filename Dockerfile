FROM ubuntu@sha256:4e0171b9275e12d375863f2b3ae9ce00a4c53ddda176bd55868df97ac6f21a6e AS universal
RUN : change this value to rebuild whole image: 2025 10 27 01 59 39

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

apt update
DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get -y install tzdata
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y \\
    bind9 \\
    bind9-dnsutils \\
    bind9-host \\
    bind9-utils \\
    build-essential \\
    cmake \\
    coreutils \\
    curl \\
    dnsdist \\
    dnsutils \\
    easy-rsa \\
    gcc \\
    git \\
    gpg \\
    iproute2 \\
    iptables \\
    iputils-ping \\
    jq \\
    libc6-dev \\
    libcrypto++-dev \\
    libevent-core-2.1-7 \\
    libevent-dev \\
    libevent-extra-2.1-7 \\
    libmbedtls-dev \\
    libnss3-dev \\
    libssl-dev \\
    lsb-release \\
    lsof \\
    nano \\
    ncat \\
    net-tools \\
    netcat \\
    nmap \\
    openresolv \\
    openssh-server \\
    openvpn \\
    passwd \\
    python3-pip \\
    python3.11-full \\
    rsyslog \\
    shadowsocks-libev \\
    software-properties-common \\
    squid \\
    sshpass \\
    sudo \\
    tmux \\
    traceroute \\
    unzip \\
    wget \\
    wireguard \\
    wireguard-tools

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    (mkfifo fifo||:) && \\
    tmux new -d -s 3 && \\
    tmux send -t 3 -l 'script -f fifo ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    tmux send -t 3 -l 'rm -f /ok ; ( curl https://sh.rustup.rs -sSf | sh ) && touch /ok ; reset ; printf "\x1b" ; stty sane ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    (set +x ; while tmux capture -t 3 >/dev/null && sleep 0.3 ; do tmux send -t 3 C-m ; done & ) && \\
    cat fifo && \\
    [ -f /ok ]
    sleep 1
    test -z "$(tmux ls)"
    sleep 1
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    (mkfifo fifo||:) && \\
    tmux new -d && \\
    tmux send -l 'script -f fifo ; exit' && \\
    tmux send C-m && \\
    sleep 0.1 && \\
    tmux send -l 'rm -f /ok ; ( cargo install udp-over-tcp ) && touch /ok ; reset ; printf "\x1b" ; stty sane ; exit' && \\
    tmux send C-m && \\
    sleep 0.1 && \\
    cat fifo && \\
    [ -f /ok ]
    sleep 1
    test -z "$(tmux ls)"
    sleep 1
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

git clone --depth 1 https://github.com/KaranGauswami/socks-to-http-proxy.git

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    (mkfifo fifo||:) && \\
    tmux new -d -s 3 && \\
    tmux send -t 3 -l 'script -f fifo ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    tmux send -t 3 -l 'rm -f /ok ; ( cd socks-to-http-proxy && cargo build --release && cp target/release/sthp / ) && touch /ok ; reset ; printf "\x1b" ; stty sane ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    cat fifo && \\
    [ -f /ok ]
    sleep 1
    test -z "$(tmux ls)"
    sleep 1
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

rm -rf /socks-to-http-proxy

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

git clone --depth 1 https://github.com/mullvad/udp-over-tcp.git

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    (mkfifo fifo||:) && \\
    tmux new -d -s 3 && \\
    tmux send -t 3 -l 'script -f fifo ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    tmux send -t 3 -l 'rm -f /ok ; set -x ; ( cd udp-over-tcp && uname -a && cat ./build-static-bins.sh | grep -v -- --target | grep -v RUSTFLAGS | bash -x && cp target/release/*2*p / ) && touch /ok ; reset ; printf "\x1b" ; stty sane ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    cat fifo && \\
    [ -f /ok ]
    sleep 1
    test -z "$(tmux ls)"
    sleep 1
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

wget -O go.tar.gz 'https://go.dev/dl/go1.25.3.linux-'"$(uname -p | sed 's?aarch64?arm64?g' | sed 's?x86_64?amd64?g' )"'.tar.gz'

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

tar -C /usr/local -xzf go.tar.gz
/usr/local/go/bin/go install github.com/pufferffish/wireproxy/cmd/wireproxy@v1.0.9 # or @latest
/usr/local/go/bin/go clean -cache

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    (mkfifo fifo||:) && \\
    tmux new -d -s 3 && \\
    tmux send -t 3 -l 'script -f fifo ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    tmux send -t 3 -l 'rm -f /ok ; ( apt install -y sslh ) && touch /ok ; reset ; printf "\x1b" ; stty sane ; exit' && \\
    tmux send -t 3 C-m && \\
    sleep 0.1 && \\
    (while tmux capture -t 3 && sleep 0.3 ; do tmux send -t 3 2 ; tmux send -t 3 C-m ; done & ) && \\
    cat fifo && \\
    [ -f /ok ]
    sleep 1
    test -z "$(tmux ls)"
    sleep 1
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

wget -O curl.tar  'https://github.com/stunnel/static-curl/releases/download/8.16.0-ech/curl-linux-'"$(uname -p )"'-musl-8.16.0.tar.xz'
tar -xf ./curl.tar

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

wget -O wgcf 'https://github.com/ViRb3/wgcf/releases/download/v2.2.29/wgcf_2.2.29_linux_'"$(uname -p | sed 's?aarch64?arm64?g' | sed 's?x86_64?amd64?g' )"
chmod +x wgcf

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

git clone --depth 1 https://github.com/ambrop72/badvpn.git

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    cd badvpn && \\
    mkdir build && \\
    cd build && \\
    cmake .. -DBUILD_NOTHING_BY_DEFAULT=1 -DBUILD_TUN2SOCKS=1 -DBUILD_UDPGW=1 && \\
    make && \\
    sudo make install || \\
    ( cat /badvpn/build/CMakeFiles/CMakeOutput.log && false)
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

git clone --depth 1 https://github.com/rofl0r/microsocks.git microsocks_d

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    : && \\
    cd microsocks_d && \\
    make && \\
    cp ./microsocks /microsocks
)

EOF
RUN chmod +x /build.sh
RUN /build.sh



COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

mkdir /var/run/sshd
adduser --disabled-password --gecos '' gera
echo dXNlcm1vZCAtcCAnJDYkdEZuQXJyS3Y2eXBFTlJpcSRhbVZudGlKLjV3WlY1TjJ0Q3ZMdDBSZk5XbjVGRkR0S00ycmlsMmJObk1OdG02eGx6L1NpbVJCblRYY1locGdXVHcwdVJwalZyb1g3L2k2bDJKNGsvLicgZ2VyYQo= | base64 -d | bash -xeu
usermod -aG sudo gera
echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
echo 'LogLevel DEBUG3' >> /etc/ssh/sshd_config

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

python3 -m pip install PySocks pysocks dnspython dnspython ifaddr aiodns icecream psutil dnspython

EOF
RUN chmod +x /build.sh
RUN /build.sh

COPY <<-EOF /build.sh
#!/usr/bin/env bash
set -x -u -e -o pipefail

(
    mkdir ~/c
    cd ~/c
    wget 'https://raw.githubusercontent.com/sudo-gera/c/0d124b224485a0af4c7700d68f6896f30f47a1bf/tcp_dns.py'
    wget 'https://raw.githubusercontent.com/sudo-gera/c/0d124b224485a0af4c7700d68f6896f30f47a1bf/tls_terminator.py'
    wget 'https://raw.githubusercontent.com/sudo-gera/c/0d124b224485a0af4c7700d68f6896f30f47a1bf/stream.py'
    wget 'https://raw.githubusercontent.com/sudo-gera/c/0d124b224485a0af4c7700d68f6896f30f47a1bf/await_if_necessary.py'
    wget 'https://raw.githubusercontent.com/sudo-gera/c/0d124b224485a0af4c7700d68f6896f30f47a1bf/sign.py'
    wget 'https://raw.githubusercontent.com/sudo-gera/c/0d124b224485a0af4c7700d68f6896f30f47a1bf/forwarding_parser.py'
)

EOF
RUN chmod +x /build.sh
RUN /build.sh

RUN python3 -m pip install async-cache
RUN python3 -m pip install pytest coverage

COPY . /app

RUN /app/coverage.sh

RUN echo '/app/coverage.sh' >> /root/.bash_history

CMD cd /app ; bash
