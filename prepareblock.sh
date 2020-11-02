#!/bin/bash
set -e
python3 checksumsimos18.py -i $1 -b $2
lzss/lzss -i $1 -o $1.compressed
python3 encryptsimos18.py -i $1.compressed -o $1.flashable
