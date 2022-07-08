from config import celery_app
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded

from qgis.core import *

# from qgis.core import (
#     QgsProject,
#     QgsPathResolver,
#     QgsProcessingContext,
#     QgsProcessingFeedback,
#     QgsCoordinateReferenceSystem,
# )
from qgis.gui import (
    QgsLayerTreeMapCanvasBridge,
    QgsMapCanvas,
)
import processing

from time import sleep
from os.path import join

from django.core.files import File

# from django.core.files.storage import FileSystemStorage
from geodata_mart.maps.models import project_storage
from geodata_mart.maps.models import Job, ResultFile

logger = get_task_logger(__name__)


def run_gdmclip_processing_script(
    process_feedback,
    process_context,
    PROJECTID,
    VENDORID,
    USERID,
    JOBID,
    LAYERS,
    EXCLUDES,
    CLIP_GEOM,
    OUTPUT_CRS,
    PROJECT_CRS,
    OUTPUT,
):
    """Run the default generic processing script"""

    layers_param = ",".join(map(str, LAYERS)) if LAYERS else None
    output_crs_param = QgsCoordinateReferenceSystem(OUTPUT_CRS) if OUTPUT_CRS else None
    project_crs_param = (
        QgsCoordinateReferenceSystem(PROJECT_CRS) if PROJECT_CRS else None
    )
    excludes_param = ",".join(map(str, EXCLUDES)) if EXCLUDES else None

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
    QgsApplication.setPrefixPath("/usr/bin/qgis", True)
    qgs = QgsApplication([], False)  # nogui
    qgs.initQgis()
    qgs.exitQgis()
    job = Job.objects.filter(job_id=job_id).first()
    logger.info(f"Processing Job: {job}")
    parameters = job.parameters
    feedback = QgsProcessingFeedback()
    context = QgsProcessingContext()
    map_file = job.project_id.project_file.file_object.path
    # logger.info("nnnnnn")
    # # canvas = QgsMapCanvas()
    # logger.info("---")
    # bridge = QgsLayerTreeMapCanvasBridge(
    #     QgsProject.instance().layerTreeRoot(), QgsMapCanvas()
    # )
    readflags = QgsProject.ReadFlags()
    readflags |= QgsProject.FlagDontResolveLayers
    logger.info("***")
    project = QgsProject.instance().read(map_file, readflags)
    context.setProject(project)
    logger.info("####")
    output_path = join(project_storage.path, "output", job.job_id)
    try:
        logger.info("aaaaaaaaaaaaaaaaaaaaa")
        task = run_gdmclip_processing_script(
            process_feedback=feedback,
            process_context=context,
            PROJECTID=parameters["PROJECTID"],
            VENDORID=parameters["VENDORID"],
            USERID=parameters["USERID"],
            JOBID=job.job_id,
            LAYERS=parameters["LAYERS"],
            EXCLUDES=parameters["EXCLUDES"],
            CLIP_GEOM=parameters["CLIP_GEOM"],
            OUTPUT_CRS=parameters["OUTPUT_CRS"],
            PROJECT_CRS=parameters["PROJECT_CRS"],
            OUTPUT=output_path,
        )
        logger.info("bbbbbbbbbbbbbbbbbbbbbbbb")
        # Wait for procesing script to run
        while (
            not task.finished()
        ):  # https://qgis.org/pyqgis/master/core/QgsTask.html#qgis.core.QgsTask.finished
            sleep(5)  # 5 seconds is fine

        logger.info(task["OUTPUT"])

        # create new results file from this object
        results_file = task["OUTPUT"]
        if not project_storage.exists(results_file):
            raise Exception(f"{project_storage.path(results_file)} not found")
        results_file = project_storage.open(results_file, "rb")
        results_file_object = File(results_file)
        results_file = ResultFile.objects.create(
            file_name=job.job_id,
            file_object=results_file_object,
            job_id=job,
        )
        results_file_object.close()

    except SoftTimeLimitExceeded:
        feedback.cancel()
