FROM ubuntu:noble

# Install KiCad build dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install --no-install-recommends \
    # Build tools
    build-essential \
    cmake \
    cmake-curses-gui \
    ninja-build \
    ccache \
    pkg-config \
    git \
    # Compilers and linkers
    clang \
    lld \
    mold \
    # KiCad build dependencies from Build-Depends
    libbz2-dev \
    libcairo2-dev \
    libglu1-mesa-dev \
    libgl1-mesa-dev \
    libglew-dev \
    libx11-dev \
    libwxgtk3.2-dev \
    libwxgtk-webview3.2-dev \
    mesa-common-dev \
    libssl-dev \
    libzstd-dev \
    python3-dev \
    swig \
    python3-wxgtk4.0 \
    libgit2-dev \
    libsecret-1-dev \
    libboost-all-dev \
    libglm-dev \
    libcurl4-openssl-dev \
    libgtk-3-dev \
    libngspice0-dev \
    libocct-modeling-algorithms-dev \
    libocct-modeling-data-dev \
    libocct-data-exchange-dev \
    libocct-visualization-dev \
    libocct-foundation-dev \
    libocct-ocaf-dev \
    unixodbc-dev \
    libspnav-dev \
    libnng-dev \
    libprotobuf-dev \
    protobuf-compiler \
    zlib1g-dev \
    shared-mime-info \
    python3-pytest \
    python3-cairosvg \
    python3-numpy \
    libzint-dev \
    libpoppler-dev \
    libpoppler-glib-dev \
    doxygen \
    dblatex \
    po4a \
    asciidoc \
    source-highlight \
    # EGL/OpenGL dependencies
    libegl1-mesa-dev \
    libgles2-mesa-dev \
    # System dependencies
    zip \
    npm \
    nano \
    openjdk-17-jdk \
    python3-tk \
    procps \
    software-properties-common \
    xclip \
    gpg-agent \
    dirmngr \
    unzip \
    xdotool \
    imagemagick \
    python3-pip \
    xvfb \
    && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /code
COPY . .
RUN uv pip install --system --no-cache --break-system-packages -e .

EXPOSE 8080
CMD ["python3", "-u", "/app/main.py", "--headless"]