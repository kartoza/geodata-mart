import uuid
from config import celery_app
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded

from celery_progress.backend import ProgressRecorder

from PyQt5 import *
from qgis.core import *

import processing

import pickle
import codecs
from os.path import join, basename
from os import environ, stat
from pathlib import Path

from geodata_mart.maps.models import project_storage
from geodata_mart.maps.models import Job, ResultFile

from geodata_mart.utils.qgis import migrateProcessingScripts

logger = get_task_logger(__name__)

import shutil


@shared_task(bind=True)
def process_job_gdmclip(self, job_id):

    job = Job.objects.filter(job_id=job_id).first()
    if not job:
        raise ValueError(f"Processing Job {job_id} not found")
    else:
        logger.info(f"Processing Job: {job_id}")

    progress_recorder = ProgressRecorder(self)

    progress_recorder.set_progress(
        1, 100, description="Processing started"
    )  # current, total, description

    logger.info(f"Configuring environment")
    parameters = job.parameters
    environ[
        "QT_QPA_PLATFORM"
    ] = "offscreen"  # https://gis.stackexchange.com/questions/379131/qgis-linux-qt-qpa-plugin-could-not-load-the-qt-platform-plugin-xcb-in-eve

    qgs = QgsApplication(
        argv=[],
        GUIenabled=False,
        # profileFolder="profile/path",
        platformName="external",
        # platformName="qgis_process",
    )

    qgs.setPrefixPath("/usr", useDefaultPaths=True)

    logger.info("Configuring QGIS")
    registry = (
        qgs.processingRegistry()
    )  # https://qgis.org/pyqgis/master/core/QgsProcessingRegistry.html

    if job.project_id.config_auth:
        auth_config_path = Path("/qgis/.auth/")
        auth_config_path = Path.joinpath(auth_config_path, uuid.uuid4().hex)
        auth_config_path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            job.project_id.config_auth.file_object.path,
            Path.joinpath(auth_config_path, "qgis-auth.db"),
        )
        qgs.setAuthDatabaseDirPath(str(auth_config_path))
        auth_manager = qgs.authManager()
        auth_manager.setMasterPassword(job.project_id.config_auth.secret, True)

    qgs.setMaxThreads(1)
    qgs.initQgis()

    feedback = QgsProcessingFeedback()
    context = QgsProcessingContext()

    map_file = job.project_id.qgis_project_file.file_object.path
    logger.info(f"Processing project file: {map_file}")
    readflags = QgsProject.ReadFlags()
    readflags |= (
        QgsProject.FlagDontResolveLayers
        | QgsProject.FlagDontLoadLayouts
        | QgsProject.FlagTrustLayerMetadata
    )
    project = QgsProject()
    project.instance().read(map_file, readflags)
    context.setProject(project)

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

    logger.info("Refreshing processing registry")
    processing.core.Processing.Processing.initialize()
    if registry.providerById("script"):
        registry.providerById("script").refreshAlgorithms()

    logger.info("Configuring processing parameters")
    output_path = join(project_storage.location, "output", str(job.job_id))
    LAYERS = (
        parameters["LAYERS"] if bool(parameters["LAYERS"]) else None
    )  # If nullish, make nonetype
    layers_param = ",".join(map(str, LAYERS)) if (type(LAYERS) == list) else LAYERS
    EXCLUDES = (
        parameters["EXCLUDES"] if bool(parameters["EXCLUDES"]) else None
    )  # If nullish, make nonetype
    excludes_param = (
        ",".join(map(str, EXCLUDES)) if type(EXCLUDES) == list else EXCLUDES
    )
    output_crs_param = (
        QgsCoordinateReferenceSystem(parameters["OUTPUT_CRS"])
        if bool(parameters["OUTPUT_CRS"])
        else None
    )
    project_crs_param = (
        QgsCoordinateReferenceSystem(parameters["PROJECT_CRS"])
        if bool(parameters["PROJECT_CRS"])
        else None
    )
    # TODO validation of single polygon (& test multipolygon) WKT area feature
    clipping_geometry = parameters["CLIP_GEOM"]

    logger.info("Executing processing command")

    progress_recorder.set_progress(5, 100, description="Environment configured")

    try:
        script = QgsApplication.processingRegistry().algorithmById("script:gdmclip")
        params = {
            "PROGRESS_RECORDER": codecs.encode(
                pickle.dumps(progress_recorder), "base64"
            ).decode(),
            "PROJECTID": parameters["PROJECTID"],
            "VENDORID": parameters["VENDORID"],
            "USERID": parameters["USERID"],
            "JOBID": str(job.job_id),
            "LAYERS": layers_param,
            "EXCLUDES": excludes_param,
            "CLIP_GEOM": clipping_geometry,
            "OUTPUT_CRS": output_crs_param,
            "PROJECT_CRS": project_crs_param,
            "OUTPUT": output_path,
        }
        task = script.create()
        task.prepare(params, context, feedback)
        result = task.runPrepared(params, context, feedback)

        logger.info("Create results from task")
        results_file = result["OUTPUT"]
        if not project_storage.exists(results_file):
            raise Exception(
                f"Output file {project_storage.path(results_file)} not found"
            )
        logger.info(f"Saving to to result file")
        results_file_record = ResultFile.objects.create(
            file_name=job.job_id,
            job_id=job,
        )
        # add results file object to results file record (upload_to=results)
        with project_storage.open(results_file) as f:
            results_file_record.file_object.save(basename(results_file), f, save=True)

        progress_recorder.set_progress(95, 100, description="Results saved")

        logger.info(f"Remove artifact")
        statinfo = stat(results_file)  # get stats on the output file

        with project_storage.open(results_file, "w") as f:
            f.write(
                str(statinfo)
            )  # replace actual file (now duplicate) with file stats

        progress_recorder.set_progress(100, 100, description="Task completed")
        job.state = job.JobStateChoices.PROCESSED
        job.save()

    except SoftTimeLimitExceeded:
        feedback.cancel()

    finally:
        logger.info(f"Closing QGIS")
        # manual cleanup to prevent segmentation fault
        for var in [registry, project, task, feedback, context]:
            if var in locals():
                del var
        qgs.exitQgis()
        if auth_config_path:
            shutil.rmtree(auth_config_path)
