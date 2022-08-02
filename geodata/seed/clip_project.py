# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from inspect import Parameter
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProject,
    QgsFields,
    QgsField,
    QgsMapLayer,
    QgsMapLayerType,
    QgsDataProvider,
    QgsProviderRegistry,
    QgsGeometry,
    QgsReferencedRectangle,
    QgsVectorLayer,
    QgsVectorLayerUtils,
    QgsCoordinateReferenceSystem,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsProcessingParameterString,
    QgsProcessingParameterCrs,
)
from PyQt5.QtCore import QVariant
from qgis import processing

# import processing
import os
from pathlib import Path
from datetime import date
from math import floor


class GdmClipProjectLayers(QgsProcessingAlgorithm):
    """
    This algorithm is designed for use with the GeoDataMart API and
    WPS infrastructure. The purpose and function is to iterate over
    a provided project and clip the specified layers to the bounding
    area provided, then package all outputs with the appropriate styles
    and content into a geopackage with a qgis project, which is then
    published to a storage system for retrieval by the user, returned
    as a response, or provided as a dynamic service accordingly.
    """

    PROJECTID = "PROJECTID"
    VENDORID = "VENDORID"
    USERID = "USERID"
    JOBID = "JOBID"
    LAYERS = "LAYERS"
    EXCLUDES = "EXCLUDES"
    CLIP_GEOM = "CLIP_GEOM"
    OUTPUT_CRS = "OUTPUT_CRS"
    PROJECT_CRS = "PROJECT_CRS"
    PROGRESS_RECORDER = "PROGRESS_RECORDER"
    OUTPUT = "OUTPUT"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return GdmClipProjectLayers()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "gdmclip"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Clip Project Layers")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr("GeoData Mart")

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "geodatamart"

    def helpString(self):
        """
        Returns a localised help string for the algorithm.
        """
        return self.tr(
            "Clip and publish a QGIS Project file with GeoData Mart,"
            + " returning the path to the output zip file."
            + "\nThis is not intended for use with QGIS Desktop Applications."
        )

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it.
        """
        return self.tr(
            "Clip and publish a QGIS Project file with GeoData Mart,"
            + " returning the path to the output zip file."
        )

    def initAlgorithm(self, config=None):
        """
        Define input and outputs parameters.
        """

        self.addParameter(
            QgsProcessingParameterString(
                name=self.PROJECTID,
                description=self.tr("Project"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.VENDORID,
                description=self.tr("Vendor"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.USERID,
                description=self.tr("User"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.JOBID,
                description=self.tr("Job"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.LAYERS,
                description=self.tr("Map Layers"),
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.EXCLUDES,
                description=self.tr("Excluded Layers"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.CLIP_GEOM,
                description=self.tr("Clip Geometry"),
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                name=self.OUTPUT_CRS,
                description=self.tr("Output CRS"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                name=self.PROJECT_CRS,
                description=self.tr("Project CRS"),
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name=self.PROGRESS_RECORDER,
                description=self.tr(
                    "Celery Progress Recorder Object. GeoData Mart Use Only."
                ),
                optional=True,
            )
        )

        # Output geopackage
        self.addParameter(
            QgsProcessingParameterString(
                name=self.OUTPUT,
                description=self.tr("Output File"),
            )
        )

    def getParameterValue(self, parameters, parameter_name):
        """Test whether an input parameter is available and truthy,
        then return the retrieved parameter value"""
        if parameter_name in parameters:
            if bool(parameters[parameter_name]):
                return_value = parameters[parameter_name]
            else:
                return_value = None
        else:
            return_value = None
        return return_value

    def getCleanListFromCsvString(self, input_string):
        """Convert an input comma separated string into a list of clean values"""
        input_string = input_string.replace("[", "")
        input_string = input_string.replace("]", "")
        input_string = input_string.replace("\\", "")
        input_string = input_string.replace('"', "")
        output_list = input_string.split(",")
        output_list = [
            a.replace(",", "").strip() for a in output_list if bool(a.strip())
        ]
        output_list = [
            a.replace("'", "").strip() for a in output_list if bool(a.strip())
        ]
        output_list = [
            a.replace('"', "").strip() for a in output_list if bool(a.strip())
        ]
        return output_list

    def incrementProgress(self, feedback, msg="Processing step complete"):
        feedback.setProgress(feedback.progress() + self.increment)
        if self.progress_recorder:
            self.progress_recorder.set_progress(
                floor(feedback.progress() * 0.8) + 10, 100, description=msg
            )  # current, total, description

    def zipOutputs(self, parameters, context, feedback, extensions, file_name):
        """
        Compile the outputs from the processing tool into a single zip file
        """
        try:
            feedback.pushInfo(f"Adding outputs to archive")
            from zipfile import ZipFile

            file_paths = []
            max_depth = 1
            for root, directories, files in os.walk(self.output_path):
                if root[len(self.output_path) :].count(os.sep) < max_depth:
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        file_paths.append(filepath)

            # Exclude redundant files from output
            for extension in extensions:
                file_paths = [
                    filepath
                    for filepath in file_paths
                    if not filepath.endswith(extension)
                ]

            with ZipFile(file_name, "w") as zip:
                for file in file_paths:
                    zip.write(file, arcname=os.path.basename(file))

            # zip = ZipFile(file_name, "rb")

            # return zip.read()

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

    def removeOutputs(self, parameters, context, feedback, extensions):
        """
        Walk through the parent directory for the output geopackage and remove
        all the outputs matching a particular set of extensions.
        """
        try:
            feedback.pushInfo(f"Removing obsolete files")
            file_paths = []
            max_depth = 1
            for root, directories, files in os.walk(self.output_path):
                if root[len(self.output_path) :].count(os.sep) < max_depth:
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        file_paths.append(filepath)

            obsolete_files = [
                file for ext in extensions for file in file_paths if file.endswith(ext)
            ]
            for file in obsolete_files:
                try:
                    os.remove(file)
                except Exception as e:
                    feedback.reportError(str(e), fatalError=False)

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

    def initializeOutputs(self, parameters, context, feedback):
        """
        Remove existing zip outputs matching the expected output path,
        and instantiate a new geopackage with select metadata

        Raises:
            QgsProcessingException: Issues with removal or creation indicating permissions issues
        """
        feedback.pushInfo(f"Initializing Outputs")
        output_gpkg = os.path.join(self.output_path, self.jobid + ".gpkg")
        output_zip = os.path.join(self.output_path, self.jobid + ".zip")
        if os.path.exists(output_gpkg):
            try:
                os.remove(output_gpkg)
                feedback.pushInfo(f"Existing {output_gpkg} has been removed")
            except OSError:
                raise QgsProcessingException(
                    "Unable to remove existing target output files. Check permissions and file locks."
                )
            except Exception as e:
                feedback.reportError(str(e), fatalError=True)
        if os.path.exists(output_zip):
            try:
                os.remove(output_zip)
                feedback.pushInfo(f"Existing {output_zip} has been removed")
            except OSError:
                raise QgsProcessingException(
                    "Unable to remove existing target output files. Check permissions and file locks."
                )
            except Exception as e:
                feedback.reportError(str(e), fatalError=True)

        try:
            md = QgsProviderRegistry.instance().providerMetadata("ogr")
            conn = md.createConnection(output_gpkg, {})
            fields = QgsFields()
            fields.append(QgsField("user", QVariant.String))
            fields.append(QgsField("vendor", QVariant.String))
            fields.append(QgsField("project", QVariant.String))
            fields.append(QgsField("job", QVariant.String))
            fields.append(QgsField("date", QVariant.Date))
            conn.createVectorTable(
                "",
                "__geodatamart__",
                fields,
                QgsWkbTypes.NoGeometry,
                QgsCoordinateReferenceSystem(),
                True,
                {},
            )
            sql = (
                "INSERT INTO __geodatamart__ (user,vendor,project,job,date) VALUES ("
                + f'\'{parameters["USERID"] if self.getParameterValue(parameters, "USERID") else "NULL"}\','
                + f' \'{parameters["VENDORID"] if self.getParameterValue(parameters, "VENDORID") else "NULL"}\','
                + f' \'{parameters["PROJECTID"] if self.getParameterValue(parameters, "PROJECTID") else "NULL"}\','
                + f' \'{self.jobid}\', \'{date.today().strftime("%Y/%m/%d")}\');'
            )
            conn.execSql(sql, feedback)

        except Exception as e:
            raise QgsProcessingException(
                f"Unable to create new output geopackage. {str(e)}"
            )
        finally:
            del md, conn

    def setProjectExtent(self, parameters, context, feedback, layer):
        layer.updateExtents()
        extent = QgsReferencedRectangle(layer.extent(), layer.crs())
        QgsProject.instance().viewSettings().setDefaultViewExtent(extent)
        QgsProject.instance().write()

    def generateClippingGeometry(self, parameters, context, feedback):
        """
        Generate the clipping geometry from the supplied WKT definition, save the
        geometry layer to file, and return the result.
        """

        feedback.pushInfo(f"Generating clipping bounds")

        try:
            # Expects single wkt polygon/ area feature
            wkt_geom = QgsGeometry.fromWkt(parameters["CLIP_GEOM"])
            clip_layer = QgsVectorLayer(
                "polygon?crs=epsg:4326&field=id:integer&index=yes",
                "Clip layer",
                "memory",
            )
            clip_layer.setCustomProperty("skipMemoryLayersCheck", 1)
            clip_layer.startEditing()
            clip_layer.addFeature(
                QgsVectorLayerUtils.createFeature(
                    clip_layer,
                    wkt_geom,
                )
            )
            clip_layer.commitChanges(stopEditing=True)
            clip_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

            if self.output_crs:
                clipping_geometry = processing.run(
                    "native:reprojectlayer",
                    {
                        "INPUT": clip_layer,
                        "TARGET_CRS": self.output_crs,
                        "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                    },
                )["OUTPUT"]
            else:
                clipping_geometry = clip_layer

            self.incrementProgress(feedback, msg="Clipping geometry created")

            # Store clipping bounds as layer
            clip_file_output = os.path.join(self.output_path, self.jobid + ".gpkg")
            save_clip_options = QgsVectorFileWriter.SaveVectorOptions()
            save_clip_options.layerName = "__aoi__"
            save_clip_options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )
            save_clip_options.driverName = "GPKG"
            transform_context = QgsProject.instance().transformContext()
            feedback.pushInfo(f"Saving layer to {clip_file_output}")
            filesave_error = QgsVectorFileWriter.writeAsVectorFormatV3(
                clipping_geometry,
                clip_file_output,
                transform_context,
                save_clip_options,
            )

            if filesave_error[0] == QgsVectorFileWriter.NoError:
                feedback.pushInfo(f"Clipping bounds saved to {clip_file_output}")
            else:
                feedback.reportError(str(filesave_error), fatalError=False)

            del filesave_error

            return clipping_geometry

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

    # #####  CLIPPING ALGORITHMS  #####
    # TODO support other data types, e.g. mesh
    # https://qgis.org/pyqgis/master/core/QgsMapLayerType.html

    def clipVector(self, parameters, context, feedback, layer, clip_layer):
        """
        Clip vector layer to a given geometry mask

        Args:
            feedback (QgsProcessingFeedback): Feedback item for progress reporting and warnings
            layer (QgsMapLayer): Input layer to be clipped
            clip_layer (QgsGeometry): Masking geometry to use for clipping
        """

        # Try and resolve invalid layers
        if not layer.isValid():
            layer.dataProvider.forceReload()  # Attempt reload
            if not layer.isValid():
                QgsProject.instance().removeMapLayer(layer.id())
                feedback.reportError(
                    str(f"Layer {layer.name()} is not valid"), fatalError=False
                )

        layer_name = layer.name().replace('"', "")
        output_gpkg = os.path.join(self.output_path, self.jobid + ".gpkg")

        try:
            clipped_vector = processing.run(
                "native:clip",
                {
                    "INPUT": layer,
                    "OVERLAY": clip_layer,
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
            )["OUTPUT"]

            self.incrementProgress(
                feedback,
                msg=f"Vector layer {layer.name()} clipped",
            )

            if self.output_crs:
                output_vector = processing.run(
                    "native:reprojectlayer",
                    {
                        "INPUT": clipped_vector,
                        "TARGET_CRS": QgsCoordinateReferenceSystem(self.output_crs),
                        "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                    },
                    context=context,
                    feedback=feedback,
                )["OUTPUT"]

                self.incrementProgress(
                    feedback,
                    msg=f"Vector layer {layer.name()} processed",
                )

            else:
                output_vector = clipped_vector

            # Save the clipped layer result to file
            save_vector_options = QgsVectorFileWriter.SaveVectorOptions()
            save_vector_options.layerName = f"{layer_name}"
            save_vector_options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )
            save_vector_options.driverName = "GPKG"
            save_vector_options.symbologyExport = QgsVectorFileWriter.FeatureSymbology
            transform_context = QgsProject.instance().transformContext()
            feedback.pushInfo(f"Saving layer to {output_gpkg}")
            filesave_error = QgsVectorFileWriter.writeAsVectorFormatV3(
                output_vector,
                output_gpkg,
                transform_context,
                save_vector_options,
            )

            if filesave_error[0] == QgsVectorFileWriter.NoError:
                feedback.pushInfo(f"Clipped result saved to {output_gpkg}|{layer_name}")
            else:
                feedback.reportError(str(filesave_error), fatalError=False)

            del filesave_error

        except Exception as e:
            QgsProject.instance().removeMapLayer(layer.id())
            feedback.reportError(str(e), fatalError=False)

            self.incrementProgress(
                feedback, msg=f"Vector layer {layer.name()} encountered an error"
            )

        finally:
            # Change the project layers source to the clipped output
            vector_source_options = QgsDataProvider.ProviderOptions()
            vector_source_options.transformContext = (
                QgsProject.instance().transformContext()
            )
            lyr_uri = os.path.join(
                self.output_path, self.jobid + f".gpkg|layername={layer_name}"
            )
            layer.setDataSource(
                lyr_uri,
                f"{layer_name}",
                f"ogr",
                vector_source_options,
            )
            feedback.pushInfo(f"Set layer datasource to {lyr_uri}")
            layer.reload()
            layer.updateExtents()

    def clipRaster(self, parameters, context, feedback, layer, clip_layer):
        """
        Clip raster layer to a given geometry mask

        Args:
            feedback (QgsProcessingFeedback): Feedback item for progress reporting and warnings
            layer (QgsMapLayer): Input layer to be clipped
            clip_layer (QgsGeometry): Masking geometry to use for clipping
        """

        # Try and resolve invalid layers
        if not layer.isValid():
            layer.dataProvider.forceReload()  # Attempt reload
            if not layer.isValid():
                QgsProject.instance().removeMapLayer(layer.id())
                feedback.reportError(
                    str(f"Layer {layer.name()} is not valid"), fatalError=False
                )

        layer_name = layer.name().replace('"', "")
        output_img = os.path.join(self.output_path, f"{layer_name}.tif")

        try:
            if self.output_crs:
                crs = QgsCoordinateReferenceSystem(self.output_crs)
            else:
                crs = None
            clipped_raster = processing.run(
                "gdal:cliprasterbymasklayer",
                {
                    "INPUT": layer,
                    "MASK": clip_layer,
                    "SOURCE_CRS": None,
                    "TARGET_CRS": None,
                    "TARGET_EXTENT": crs,
                    "NODATA": None,
                    "ALPHA_BAND": True,
                    "CROP_TO_CUTLINE": True,
                    "KEEP_RESOLUTION": True,
                    "SET_RESOLUTION": False,
                    "X_RESOLUTION": None,
                    "Y_RESOLUTION": None,
                    "MULTITHREADING": False,
                    "OPTIONS": "",
                    "DATA_TYPE": 0,
                    "EXTRA": "",
                    "OUTPUT": output_img,
                },
                context=context,
                feedback=feedback,
            )["OUTPUT"]

            self.incrementProgress(
                feedback,
                msg=f"Raster layer {layer.name()} clipped",
            )

        except Exception as e:
            QgsProject.instance().removeMapLayer(layer.id())
            feedback.reportError(str(e), fatalError=False)
            self.incrementProgress(
                feedback, msg=f"Raster layer {layer.name()} encountered an error"
            )

        finally:
            # Change the project layers source to the clipped output
            raster_source_options = QgsDataProvider.ProviderOptions()
            raster_source_options.transformContext = (
                QgsProject.instance().transformContext()
            )
            layer.setDataSource(
                output_img,
                f"{layer_name}",
                f"gdal",
                raster_source_options,
            )
            feedback.pushInfo(f"Set layer datasource to {output_img}")
            layer.reload()

    def clipLayer(self, parameters, context, feedback, layer, clip_layer):
        """
        Check layer type and determine appropriate processing
        requirements and algorithm to be used. Sets target data
        source and saves the project state after each layer iteration.

        Args:
            feedback (QgsProcessingFeedback): Feedback item for progress reporting and warnings
            layer (QgsMapLayer): Input layer to be clipped
            clip_layer (QgsGeometry): Masking geometry to use for clipping
        """

        try:
            if layer.type() == QgsMapLayer.VectorLayer:
                feedback.pushInfo(f"Clipping Vector {layer.name()}")
                self.clipVector(parameters, context, feedback, layer, clip_layer)
            elif layer.type() in [QgsMapLayer.RasterLayer, QgsMapLayerType.RasterLayer]:
                feedback.pushInfo(f"Clipping Raster {layer.name()}")
                self.clipRaster(parameters, context, feedback, layer, clip_layer)
            else:
                feedback.pushWarning(
                    f"{layer.name()} is not a valid vector or raster layer and will be skipped."
                )

            # Save project instance
            QgsProject.instance().write()

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

    def processAlgorithm(self, parameters, context, feedback):
        """
        Run processing algorithm
        """

        self.output_crs = self.getParameterValue(parameters, "OUTPUT_CRS")
        self.project_crs = self.getParameterValue(parameters, "PROJECT_CRS")

        # Setup Progress recorder
        self.progress_recorder = self.getParameterValue(parameters, "PROGRESS_RECORDER")

        if self.progress_recorder:  # Should be the Celery Async task ID

            import pickle  # pylint: disable=import-outside-toplevel
            import codecs  # pylint: disable=import-outside-toplevel

            self.progress_recorder = pickle.loads(
                codecs.decode(self.progress_recorder.encode(), "base64")
            )

            try:
                self.progress_recorder.set_progress(
                    10, 100, description="QGIS Processing Initialized"
                )  # current, total, description
            except:
                raise ValueError("Invalid progress recorder definition")

        # Assess project layers and requested layers
        map_layers = self.getCleanListFromCsvString(parameters["LAYERS"])

        if not map_layers:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.LAYERS)
            )

        exclude_layers = []
        if self.getParameterValue(parameters, "EXCLUDES"):
            # Identify layers to be excluded from processing,
            # ensuring that they remain available as a default
            exclude_layers = self.getCleanListFromCsvString(
                self.getParameterValue(parameters, "EXCLUDES")
            )
            map_layers += [layer for layer in exclude_layers]

        # Exclude layers from project that aren't pertinent to operation

        for layer in QgsProject.instance().mapLayers().values():
            if (
                (not layer.shortName() in map_layers)
                and (not layer.name() in map_layers)
                and (not layer.source() in map_layers)
            ):
                QgsProject.instance().removeMapLayer(layer.id())

        if len(QgsProject.instance().mapLayers()) < 1:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.LAYERS)
            )

        # Configure MultiStepFeedback
        # note that is_child_algorithm=True removes temporary outputs, so
        # manually setting the feedback progress is done for now
        additional_steps = 1  # steps for clipping and buffering clipping bounds etc
        vector_child_alg_steps = (
            2 if self.output_crs else 1
        )  # Child processes per vector layer
        raster_child_alg_steps = 1  # Child processes per raster layer
        vector_lyrs = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.VectorLayer
            and (not layer.shortName() in exclude_layers)
            and (not layer.name() in exclude_layers)
            and (not layer.source() in exclude_layers)
        ]
        raster_lyrs = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.RasterLayer
            and (not layer.shortName() in exclude_layers)
            and (not layer.name() in exclude_layers)
            and (not layer.source() in exclude_layers)
        ]

        child_processes = (
            (len(vector_lyrs) * vector_child_alg_steps)
            + (len(raster_lyrs) * raster_child_alg_steps)
            + additional_steps
        )

        self.increment = 100.0 / child_processes
        feedback.setProgress(0.0)

        # feedback = QgsProcessingMultiStepFeedback(child_processes, feedback)
        del (
            child_processes,
            additional_steps,
            vector_child_alg_steps,
            raster_child_alg_steps,
            vector_lyrs,
            raster_lyrs,
        )

        # Set jobid (defines output filenames) and destination path
        self.jobid = (
            "OUTPUT"
            if not self.getParameterValue(parameters, "JOBID")
            else str(parameters["JOBID"])
        )

        self.output_path = os.path.dirname(os.path.abspath(parameters["OUTPUT"]))

        self.output_path = (
            os.path.join(
                self.output_path,
                str(parameters["USERID"]),
            )
            if self.getParameterValue(parameters, "USERID")
            else self.output_path
        )
        self.output_path = (
            os.path.join(
                self.output_path,
                str(parameters["VENDORID"]),
            )
            if self.getParameterValue(parameters, "VENDORID")
            else self.output_path
        )
        self.output_path = (
            os.path.join(
                self.output_path,
                str(parameters["PROJECTID"]),
            )
            if self.getParameterValue(parameters, "PROJECTID")
            else self.output_path
        )
        self.output_path = (
            os.path.join(
                self.output_path,
                str(parameters["JOBID"]),
            )
            if self.getParameterValue(parameters, "JOBID")
            else self.output_path
        )

        Path(self.output_path).mkdir(parents=True, exist_ok=True)

        self.initializeOutputs(parameters, context, feedback)

        # Save a copy of the project
        # TODO replace projectName with reasonable vendor-project identifier
        output_uri = "geopackage:" + os.path.join(
            self.output_path, self.jobid + ".gpkg?projectName=geodata"
        )
        QgsProject.instance().write(output_uri)
        # Load cloned project
        QgsProject.instance().read(output_uri)
        # Set the project coordinate reference system
        if self.project_crs:
            QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(self.project_crs))
        # Save changes
        QgsProject.instance().write()

        clipping_geometry = self.generateClippingGeometry(parameters, context, feedback)

        self.setProjectExtent(parameters, context, feedback, clipping_geometry)

        for layer in QgsProject.instance().mapLayers().values():
            if (
                not layer.shortName() in exclude_layers
                and (not layer.name() in exclude_layers)
                and (not layer.source() in exclude_layers)
            ):
                feedback.pushInfo(f"Processing Layer {layer.name()}")
                self.clipLayer(
                    parameters,
                    context,
                    feedback,
                    layer,
                    clipping_geometry,
                )
            if feedback.isCanceled():
                break

        # Close the project to prevent write locks and permissions issues
        QgsProject.instance().clear()
        # Package the outputs
        output_zip_path = str(os.path.join(self.output_path, self.jobid + ".zip"))
        exclude_files_ext = [".gpkg-shm", ".gpkg-wal", ".gpkg-wal", ".gpkg-journal"]
        zip = self.zipOutputs(
            parameters, context, feedback, exclude_files_ext, output_zip_path
        )
        if self.progress_recorder:
            self.progress_recorder.set_progress(
                90, 100, description="QGIS Processing Complete"
            )  # current, total, description
        # Remove obsolete files
        remove_files_ext = [".gpkg", ".gpkg-shm", ".gpkg-wal", ".gpkg-journal", ".tif"]
        self.removeOutputs(parameters, context, feedback, remove_files_ext)

        return {self.OUTPUT: output_zip_path}
