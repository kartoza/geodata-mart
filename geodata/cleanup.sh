#!/usr/bin/bash

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $THISDIR

patterns = ( "*.zip" "*.qgs" "*.qgz" "*.py" "*.db" "*.geojson" "*.gpkg" )

for i in "${patterns[@]}"
do
  # remove files
  find . \( -name "test" -o -name "seed" \) -prune -o -type f \( -name ${i} \) -print0 | xargs -0 rm -vf
done

# Remove empty directories
find . \( -name "test" -o -name "seed" \) -prune -o -type d -empty -print0 | xargs -0 -r rmdir -v
