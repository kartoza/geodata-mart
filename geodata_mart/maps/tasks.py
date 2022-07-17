from config import celery_app
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded

from PyQt5 import *
from qgis.core import *

import processing

from time import sleep
from os.path import join, basename
from os import environ, stat
from pathlib import Path

from django.core.files import File

# from django.core.files.storage import FileSystemStorage
from geodata_mart.maps.models import project_storage
from geodata_mart.maps.models import Job, ResultFile

from geodata_mart.utils.qgis import migrateProcessingScripts

logger = get_task_logger(__name__)

import shutil


def run_gdmclip_processing_script(
    LAYERS,
    CLIP_GEOM,
    OUTPUT,
    EXCLUDES,
    OUTPUT_CRS,
    PROJECT_CRS,
    PROJECTID,
    VENDORID,
    USERID,
    JOBID,
    process_feedback,
    process_context,
):
    """Run the default generic processing script"""

    LAYERS = LAYERS if bool(LAYERS) else None  # If nullish, make nonetype
    layers_param = ",".join(map(str, LAYERS)) if (type(LAYERS) == list) else LAYERS
    EXCLUDES = EXCLUDES if bool(EXCLUDES) else None  # If nullish, make nonetype
    excludes_param = (
        ",".join(map(str, EXCLUDES)) if type(EXCLUDES) == list else EXCLUDES
    )
    output_crs_param = (
        QgsCoordinateReferenceSystem(OUTPUT_CRS) if bool(OUTPUT_CRS) else None
    )
    project_crs_param = (
        QgsCoordinateReferenceSystem(PROJECT_CRS) if bool(PROJECT_CRS) else None
    )
    # TODO Get QgsTask object
    result = processing.run(
        "script:gdmclip",
        {
            "PROJECTID": PROJECTID,
            "VENDORID": VENDORID,
            "USERID": USERID,
            "JOBID": JOBID,
            "LAYERS": layers_param,
            "EXCLUDES": excludes_param,
            "CLIP_GEOM": CLIP_GEOM,
            "OUTPUT_CRS": output_crs_param,
            "PROJECT_CRS": project_crs_param,
            "OUTPUT": OUTPUT,
        },
        context=process_context,
        feedback=process_feedback,
    )
    return result


@celery_app.task()
def process_job_gdmclip(job_id):
    job = Job.objects.filter(job_id=job_id).first()
    if not job:
        raise ValueError(f"Processing Job {job_id} not found")
    else:
        logger.info(f"Processing Job: {job_id}")

    logger.info(f"Updating processing script availability")

    migrateProcessingScripts()

    # manually force script availability
    Path("/root/.local/share/profiles/default/processing/scripts/").mkdir(
        parents=True, exist_ok=True
    )
    shutil.copy2(
        "/qgis/processing/scripts/clip_project.py",
        "/root/.local/share/profiles/default/processing/scripts/clip_project.py",
    )

    logger.info(f"Configuring environment")
    parameters = job.parameters
    environ[
        "QT_QPA_PLATFORM"
    ] = "offscreen"  # https://gis.stackexchange.com/questions/379131/qgis-linux-qt-qpa-plugin-could-not-load-the-qt-platform-plugin-xcb-in-eve

    QgsApplication.setPrefixPath("/usr/bin/qgis", useDefaultPaths=True)

    qgs = QgsApplication(
        argv=[],
        GUIenabled=False,
        # profileFolder="profile/path",
        platformName="external",
        # platformName="qgis_process",
    )
    logger.info("Configuring QGIS")
    registry = (
        qgs.processingRegistry()
    )  # https://qgis.org/pyqgis/master/core/QgsProcessingRegistry.html
    # qgs.setAuthDatabaseDirPath(job.project_id.config_auth.file_object.path)

    qgs.setMaxThreads(1)
    qgs.initQgis()

    feedback = QgsProcessingFeedback()
    context = QgsProcessingContext()

    map_file = job.project_id.qgis_project_file.file_object.path
    logger.info(f"Processing project file: {map_file}")

    readflags = QgsProject.ReadFlags()
    readflags |= QgsProject.FlagDontLoadLayouts | QgsProject.FlagTrustLayerMetadata
    project = QgsProject()
    project.instance().read(map_file, readflags)
    context.setProject(project)
    output_path = join(project_storage.location, "output", str(job.job_id))
    logger.info("Executing processing command")

    processing.core.Processing.Processing.initialize()
    if registry.providerById("script"):
        registry.providerById("script").refreshAlgorithms()

    try:
        task = run_gdmclip_processing_script(
            LAYERS=parameters["LAYERS"],
            CLIP_GEOM=parameters["CLIP_GEOM"],
            OUTPUT=output_path,
            EXCLUDES=parameters["EXCLUDES"],
            OUTPUT_CRS=parameters["OUTPUT_CRS"],
            PROJECT_CRS=parameters["PROJECT_CRS"],
            PROJECTID=parameters["PROJECTID"],
            VENDORID=parameters["VENDORID"],
            USERID=parameters["USERID"],
            JOBID=str(job.job_id),
            process_feedback=feedback,
            process_context=context,
        )
        logger.info("Waiting for process to complete...")
        # Wait for processing script to run
        # while (
        #     not task.finished()
        # ):  # https://qgis.org/pyqgis/master/core/QgsTask.html#qgis.core.QgsTask.finished
        #     logger.info(task.progress())
        ### https://docs.celeryq.dev/en/latest/userguide/calling.html#on-message
        ### self.update_state(state="PROGRESS", meta={'progress': 50})
        #     sleep(5)  # 5 seconds is fine

        logger.info(f'Processed output: {task["OUTPUT"]}')

        # create new results file from this object
        results_file = task["OUTPUT"]
        if not project_storage.exists(results_file):
            raise Exception(f"{project_storage.path(results_file)} not found")
        results_file_record = ResultFile.objects.create(
            file_name=job.job_id,
            job_id=job,
        )
        # add results file object to results file record (upload_to=results)
        results_file_record.file_object.save(
            basename(results_file), project_storage.open(results_file), save=True
        )

        statinfo = stat(results_file)  # get stats on the output file

        with project_storage.open(results_file, "w") as f:
            f.write(
                str(statinfo)
            )  # replace actual file (now duplicate) with file stats

    except SoftTimeLimitExceeded:
        feedback.cancel()

    finally:
        qgs.exitQgis()
