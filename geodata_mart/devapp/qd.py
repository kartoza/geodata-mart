"""qd: qgis_dev"""

from django.conf import settings
from sys import argv

from PyQt5 import *
from qgis.core import *

import processing

from functools import partial
from time import sleep
from os.path import join, basename
from os import environ, stat
from pathlib import Path

import logging

# from django.core.files.storage import FileSystemStorage
from geodata_mart.maps.models import project_storage
from geodata_mart.maps.models import Job, ResultFile

from geodata_mart.utils.qgis import migrateProcessingScripts
import shutil


class TaskCallerClass:
    def run(self, task, app):
        self.task = task
        task_id = app.taskManager().addTask(self.task)
        self.id = task_id


def post_process(successful, results):
    """Run the default generic processing script"""
    print("Create results from task")
    if not successful:
        print("Task was unsuccessful")
    else:
        print(results["OUTPUT"])


def do():
    try:

        import debugpy  # pylint: disable=import-outside-toplevel

        debugpy.listen(("0.0.0.0", 9999))
        debugpy.wait_for_client()

        environ[
            "QT_QPA_PLATFORM"
        ] = "offscreen"  # https://gis.stackexchange.com/questions/379131/qgis-linux-qt-qpa-plugin-could-not-load-the-qt-platform-plugin-xcb-in-eve

        QgsApplication.setPrefixPath("/usr", useDefaultPaths=True)

        qgs = QgsApplication(
            argv=[],
            GUIenabled=False,
            # profileFolder="profile/path",
            platformName="external",
            # platformName="qgis_process",
        )

        registry = (
            qgs.processingRegistry()
        )  # https://qgis.org/pyqgis/master/core/QgsProcessingRegistry.html
        # qgs.setAuthDatabaseDirPath(job.project_id.config_auth.file_object.path)

        qgs.setMaxThreads(2)
        qgs.initQgis()

        feedback = QgsProcessingFeedback()
        context = QgsProcessingContext()

        map_file = "/qgis/test/projects/ngi_sample.qgs"

        readflags = QgsProject.ReadFlags()
        readflags |= (
            QgsProject.FlagDontResolveLayers
            | QgsProject.FlagDontLoadLayouts
            | QgsProject.FlagTrustLayerMetadata
        )
        project = QgsProject()
        project.instance().read(map_file, readflags)
        context.setProject(project)

        migrateProcessingScripts()

        # manually force script availability
        Path("/root/.local/share/profiles/default/processing/scripts/").mkdir(
            parents=True, exist_ok=True
        )
        shutil.copy2(
            "/qgis/processing/scripts/clip_project.py",
            "/root/.local/share/profiles/default/processing/scripts/clip_project.py",
        )

        processing.core.Processing.Processing.initialize()

        if registry.providerById("script"):
            registry.providerById("script").refreshAlgorithms()

        worlddem = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.shortName() == "worlddem"
        ][0]

        roads = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.name() == "roads"
        ][0]

        script = QgsApplication.processingRegistry().algorithmById("script:gdmclip")
        params = {
            "LAYERS": "roads",
            "CLIP_GEOM": "POLYGON ((29.5 -28.0, 29.5 -28.1, 29.6 -28.1, 29.6 -28.0, 29.5 -28.0))",
            "OUTPUT": "/qgis/test/output",
        }
        task = QgsProcessingAlgRunnerTask(script, params, context, feedback)
        print("---")
        # https://gis.stackexchange.com/questions/296175/issues-with-qgstask-and-task-manager
        # taskCaller = TaskCallerClass()
        # taskCaller = taskCaller.run(task, qgs)
        taskCaller = TaskCallerClass().run(task, qgs)
        task_id = taskCaller.id
        print(task_id)
        print(qgs.taskManager().task(task_id).isActive())
        print(qgs.taskManager().task(task_id).progress())

    except Exception as e:
        print("exception")
        print(e)

    finally:
        print("end")
        # manual cleanup to prevent segmentation fault
        # del registry, project, task, feedback, context
        qgs.exitQgis()
