#!/bin/sh
# Generates and assembles the probes.
cd "$(dirname "$0")" || exit 1
/opt/homebrew/bin/python3.11 gen.py || exit 1
for f in tuples arrays vec user stack limits; do
  wasm-tools parse $f.wat -o $f.wasm && wasm-tools validate --features all $f.wasm && echo "$f ok"
done
