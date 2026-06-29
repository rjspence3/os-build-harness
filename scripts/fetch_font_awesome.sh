#!/usr/bin/env bash
# One-shot bundler: downloads FontAwesome Free 6.5.2 web kit and places the
# required files in data/assets/font-awesome/.
# Safe to re-run; overwrites if already present.
set -euo pipefail

FA_VERSION="6.5.2"
DEST="data/assets/font-awesome"
TMP_DIR="$(mktemp -d)"
ZIP_URL="https://use.fontawesome.com/releases/v${FA_VERSION}/fontawesome-free-${FA_VERSION}-web.zip"
ZIP_FILE="${TMP_DIR}/fa.zip"

echo "Fetching FontAwesome Free ${FA_VERSION} from ${ZIP_URL} ..."
curl -fsSL -o "${ZIP_FILE}" "${ZIP_URL}"

echo "Extracting ..."
unzip -q "${ZIP_FILE}" -d "${TMP_DIR}"

EXTRACTED="${TMP_DIR}/fontawesome-free-${FA_VERSION}-web"

mkdir -p "${DEST}/css" "${DEST}/webfonts"

cp "${EXTRACTED}/css/all.min.css"                 "${DEST}/css/all.min.css"
cp "${EXTRACTED}/webfonts/fa-solid-900.woff2"     "${DEST}/webfonts/fa-solid-900.woff2"
cp "${EXTRACTED}/webfonts/fa-regular-400.woff2"   "${DEST}/webfonts/fa-regular-400.woff2"
cp "${EXTRACTED}/webfonts/fa-brands-400.woff2"    "${DEST}/webfonts/fa-brands-400.woff2"
cp "${EXTRACTED}/LICENSE.txt"                     "${DEST}/LICENSE.txt"

echo "${FA_VERSION}" > "${DEST}/VERSION"

rm -rf "${TMP_DIR}"

echo "Done. FontAwesome ${FA_VERSION} assets in ${DEST}/"
ls -lh "${DEST}/css/" "${DEST}/webfonts/"
