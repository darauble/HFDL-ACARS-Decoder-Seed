FROM ubuntu:24.04
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential cmake pkg-config libliquid-dev libconfig++-dev libglib2.0-dev libfftw3-dev zlib1g-dev libxml2-dev libjansson-dev libsqlite3-dev python3 python3-numpy >/dev/null
COPY libacars /src/libacars
COPY dumphfdl-up /src/dumphfdl
RUN cd /src/libacars && mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. >/dev/null && make -j8 >/dev/null && make install >/dev/null && ldconfig
RUN cd /src/dumphfdl && mkdir build && cd build && cmake -DCMAKE_BUILD_TYPE=Release -DSOAPYSDR=OFF .. && make -j8 >/dev/null && make install >/dev/null
