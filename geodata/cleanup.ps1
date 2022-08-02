# change to this parent directory
Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)

# remove files by pattern
$patterns = (
  "*.zip",
  "*.png",
  "*.tif",
  "*.jpg",
  "*.jpeg",
  "*.qgs",
  "*.qgz",
  "*.py",
  "*.db",
  "*.geojson",
  "*.gpkg")

Get-ChildItem -Path $pwd -Include $patterns -Recurse | Where-Object { $_.fullname -notmatch "test" } | Where-Object { $_.fullname -notmatch "seed" } | Remove-Item -Verbose

# clobber blank directories
# note that this needs to be iterated because empty directories with empty directories are not caught
function ClobberBlankDirs {
  Get-ChildItem -Path $pwd -Recurse | ForEach-Object {
    if ( $_.psiscontainer -eq $true) {
      if ($null -eq (Get-ChildItem $_.FullName)) {
        $_.FullName | Remove-Item -Force -Verbose
      }
    }
  }
}

for ($i = 1 ; $i -le 10 ; $i++) { ClobberBlankDirs }
