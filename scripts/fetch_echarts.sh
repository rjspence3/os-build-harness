#!/usr/bin/env bash
# One-shot bundler: downloads Apache ECharts 5.5.1 minified bundle and places
# it in data/assets/echarts/.
# Safe to re-run; overwrites if already present.
set -euo pipefail

ECHARTS_VERSION="5.5.1"
DEST="data/assets/echarts"
JS_URL="https://cdn.jsdelivr.net/npm/echarts@${ECHARTS_VERSION}/dist/echarts.min.js"

echo "Fetching ECharts ${ECHARTS_VERSION} from ${JS_URL} ..."

mkdir -p "${DEST}"

curl -fsSL -o "${DEST}/echarts.min.js" "${JS_URL}"

echo "${ECHARTS_VERSION}" > "${DEST}/VERSION"

echo "Done. ECharts ${ECHARTS_VERSION} bundle in ${DEST}/"
ls -lh "${DEST}/"
