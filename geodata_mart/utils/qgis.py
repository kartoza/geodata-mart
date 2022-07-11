import os.path
import shutil
import glob
from qgis.core import QgsApplication
from processing.script import ScriptUtils


def migrateProcessingScripts():
    project_scripts_dir = "/qgis/processing/scripts/"
    count = 0
    qgis_scripts_dir = ScriptUtils.defaultScriptsFolder()

    # Copy scripts from your script dir to QGIS script dir
    for filename in glob.glob(os.path.join(project_scripts_dir, "*.py")):
        try:
            if not os.path.exists(filename):
                shutil.copy(filename, qgis_scripts_dir)
            count += 1
        except OSError as e:
            print("Couldn't install script '{}'!".format(filename))

    # Refresh algorithms
    if count and QgsApplication.processingRegistry().providerById("script"):
        QgsApplication.processingRegistry().providerById("script").refreshAlgorithms()
