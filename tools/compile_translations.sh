#!/bin/sh
# Компілює po/*.po у src/facetfall/locale/<мова>/LC_MESSAGES/facetfall.mo
# Потрібен пакет gettext:  sudo apt install gettext
set -e
cd "$(dirname "$0")/.."
for po in po/*.po; do
    lang=$(basename "$po" .po)
    mkdir -p "src/facetfall/locale/$lang/LC_MESSAGES"
    msgfmt --check -o "src/facetfall/locale/$lang/LC_MESSAGES/facetfall.mo" "$po"
    echo "  $lang: OK"
done
