#!/bin/sh
# Build the Force (ARMv7) engine library. ALSA headers are copied from the build machine (not committed).
set -e
cd "$(dirname "$0")"
W=${WRAPPER:-/home/claude/sunskiefer/mpc-vst-plugins/wrapper}
mkdir -p build/inc
[ -d build/inc/alsa ] || cp -r /usr/include/alsa build/inc/
python3 -m ziglang cc -target arm-linux-gnueabihf.2.31 -O2 -fPIC -shared -fvisibility=hidden -std=gnu11 \
  -Wall -I"$W" -Isrc -Ibuild/inc -c src/engine.c -o build/engine.o
echo compiled
