#!/bin/sh
# Оновлює шаблон po/facetfall.pot з коду та підтягує нові рядки в усі po/*.po
set -e
cd "$(dirname "$0")/.."
xgettext --language=Python --keyword=_ --from-code=UTF-8 \
    --package-name=facetfall -o po/facetfall.pot src/facetfall/*.py
for po in po/*.po; do
    msgmerge --update --backup=none "$po" po/facetfall.pot
done
