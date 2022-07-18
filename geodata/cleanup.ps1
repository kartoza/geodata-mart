# change to this parent directory
cd (Split-Path -Parent $MyInvocation.MyCommand.Path)

# remove files by pattern
Get-ChildItem -Path $pwd -Include *.zip, *.qgs, *.qgz, *.py, *.geojson -Recurse | Where {$_.fullname -notmatch "test" } | Where {$_.fullname -notmatch "seed" } | Remove-Item -Verbose

# clobber blank directories
# note that this needs to be iterated because empty directories with empty directories are not caught
function ClobberBlankDirs {
  Get-ChildItem -Path $pwd -Recurse | foreach {
    if( $_.psiscontainer -eq $true){
      if((gci $_.FullName) -eq $null){
        $_.FullName | Remove-Item -Force -Verbose
      }
    }
  }
}

for ($i = 1 ; $i -le 10 ; $i++) {ClobberBlankDirs}
