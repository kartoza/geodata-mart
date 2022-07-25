#!/usr/bin/bash

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $THISDIR

# remove files
find . \( -name "test" -o -name "seed" \) -prune -o -type f \( -name "*.py" -o -name "*.qgs" -o -name "*.qgz" -o -name ".zip" -o -name ".db" -o -name ".geojson" \) -print0 | xargs -0 rm -vf

# Remove empty directories
find . \( -name "test" -o -name "seed" \) -prune -o -type d -empty -print0 | xargs -0 -r rmdir -v
