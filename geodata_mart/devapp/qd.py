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


def post_process(successful, results):
    """Run the default generic processing script"""
    logging.info("Create results from task")
    if not successful:
        logging.info("Task was unsuccessful")
    else:
        logging.info(results["OUTPUT"])


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
        task.run()
        # task.executed.connect(partial(post_process))
        # task_id = qgs.taskManager().addTask(task)
        # logging.info(task_id)
        # logging.info(qgs.taskManager().task(task_id).isActive())
        # logging.info(qgs.taskManager().task(task_id).progress())
        # task.run()
        # while task.isActive() and max_time < 40:
        #     logging.info(task.progress())
        #     sleep(1)
        #     max_time += 1
        # task_id = qgs.taskManager().addTask(task)  # segmentation fault
        # task.executed.connect(partial(post_process, context))
        # qgs.taskManager().addTask(task)
        # task_id = qgs.taskManager().addTask(task)
        # logging.info(task_id)
        # logging.info(qgs.taskManager().task(task_id).isActive())
        # logging.info(qgs.taskManager().task(task_id).progress())
        # max_time = 0
        # while qgs.taskManager().task(task_id).isActive() and max_time < 40:
        #     logging.info(qgs.taskManager().task(task_id).progress())
        #     sleep(1)
        #     max_time += 1

    except Exception as e:
        logging.info(e)

    finally:
        # manual cleanup to prevent segmentation fault
        del registry, project, task, feedback, context
        qgs.exitQgis()
