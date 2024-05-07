#!/usr/bin/env bash
set -eu

DATA_DIR="movie-data/data"
DATA_TARGET="./docs/data2"

cat ${DATA_DIR}/log.txt

echo "copy csv"
mkdir -p ${DATA_TARGET}
cp ${DATA_DIR}/csv-top/*.csv ${DATA_TARGET}/

echo "build site"
mkdocs build
