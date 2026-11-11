#!/bin/sh
# Run ParetoBench with no install: ./pb harness ... (Python 3.11+, stdlib only)
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m paretobench.cli "$@"
