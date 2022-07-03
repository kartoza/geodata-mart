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

# from uuid import uuid4  # output_id = uuid4()
from inspect import Parameter
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProject,
    QgsFields,
    QgsField,
    QgsMapLayer,
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
    QgsProcessingParameterNumber,
)
from PyQt5.QtCore import QVariant
from qgis import processing
import os
from pathlib import Path
from datetime import date


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

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    PROJECTID = "PROJECTID"
    VENDORID = "VENDORID"
    USERID = "USERID"
    JOBID = "JOBID"
    LAYERS = "LAYERS"
    CLIP_GEOM = "CLIP_GEOM"
    OUTPUT_CRS = "OUTPUT_CRS"
    BUFFER_DIST_KM = "BUFFER_DIST_KM"
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

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Clip and publish QGIS Project layers with GeoData Mart")

    def initAlgorithm(self, config=None):
        """
        Define input and outputs parameters.
        """

        parameter = QgsProcessingParameterString(
            name=self.PROJECTID,
            description=self.tr("Project"),
            optional=True,
        )
        self.addParameter(parameter)
        del parameter
        parameter = QgsProcessingParameterString(
            name=self.VENDORID,
            description=self.tr("Vendor"),
            optional=True,
        )
        self.addParameter(parameter)
        del parameter
        parameter = QgsProcessingParameterString(
            name=self.USERID,
            description=self.tr("User"),
            optional=True,
        )
        self.addParameter(parameter)
        del parameter

        parameter = QgsProcessingParameterString(
            name=self.JOBID,
            description=self.tr("Job"),
            optional=True,
        )
        self.addParameter(parameter)
        del parameter

        parameter = QgsProcessingParameterString(  # Enum QgsProcessingParameterMapLayer
            name=self.LAYERS,
            description=self.tr("Map Layers"),
        )
        self.addParameter(parameter)
        del parameter

        # TODO: This should probably support input feature collections in geojson format
        # Currently expects WKT definition of an area feature
        parameter = QgsProcessingParameterString(  # QgsProcessingParameterGeometry
            name=self.CLIP_GEOM,
            description=self.tr("Clip Geometry"),
        )
        self.addParameter(parameter)
        del parameter

        parameter = QgsProcessingParameterCrs(
            name=self.OUTPUT_CRS,
            description=self.tr("Output CRS"),
            optional=True,
        )
        self.addParameter(parameter)
        del parameter

        parameter = QgsProcessingParameterNumber(
            self.BUFFER_DIST_KM, "Buffer", type=QgsProcessingParameterNumber.Double
        )
        parameter.setMetadata({"widget_wrapper": {"decimals": 2}})
        self.addParameter(parameter)
        del parameter

        # Output geopackage
        self.addParameter(
            QgsProcessingParameterString(
                name=self.OUTPUT,
                description=self.tr("Output File"),
            )
        )

    def zipOutputs(self, parameters, context, feedback):
        """
        Compile the outputs from the processing tool into a single zip file
        """
        try:
            feedback.pushInfo(f"Adding outputs to archive")
            from zipfile import ZipFile

            file_name = os.path.join(self.output_path, self.jobid + ".zip")
            file_paths = []
            max_depth = 1
            for root, directories, files in os.walk(self.output_path):
                if root[len(self.output_path) :].count(os.sep) < max_depth:
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        file_paths.append(filepath)

            with ZipFile(file_name, "w") as zip:
                for file in file_paths:
                    zip.write(file, arcname=os.path.basename(file))

            zip = ZipFile(file_name, "r")

            return zip

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

    def removeOutputs(self, parameters, context, feedback, extensions: list[str]):
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
                + f'\'{parameters["USERID"] if "USERID" in parameters else "NULL"}\','
                + f' \'{parameters["VENDORID"] if "VENDORID" in parameters else "NULL"}\','
                + f' \'{parameters["PROJECTID"] if "PROJECTID" in parameters else "NULL"}\','
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
            # Generate clipping geometry
            # To be used with geodjango/ turfjs -
            # Expects single wkt area supplied by the client/ server process
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

            feedback.setProgress(feedback.progress() + self.increment)

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
        layer_name = layer.name().replace('"', "")
        output_gpkg = os.path.join(self.output_path, self.jobid + ".gpkg")

        try:
            clipped_vector = processing.run(
                "native:clip",
                {
                    "INPUT": layer.source(),
                    "OVERLAY": clip_layer,
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
            )["OUTPUT"]

            feedback.setProgress(feedback.progress() + self.increment)

            if self.output_crs:
                output_vector = processing.run(
                    "native:reprojectlayer",
                    {
                        "INPUT": clipped_vector,
                        "TARGET_CRS": QgsCoordinateReferenceSystem(self.output_crs),
                        "OPERATION": "+proj=noop",
                        "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                    },
                    context=context,
                    feedback=feedback,
                )["OUTPUT"]

                feedback.setProgress(feedback.progress() + self.increment)
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
            feedback.reportError(str(e), fatalError=False)

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
                    "INPUT": layer.source(),
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

            feedback.setProgress(feedback.progress() + self.increment)

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

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
            elif layer.type() == QgsMapLayer.RasterLayer:
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
        if "OUTPUT_CRS" in parameters:
            self.output_crs = parameters["OUTPUT_CRS"]
        else:
            self.output_crs = None

        # Assess project layers and requested layers
        process_layer_names = parameters["LAYERS"]
        process_layer_names = process_layer_names.split(",")
        process_layer_names = [
            a.strip()
            for a in process_layer_names
            if (a.strip() != " ") and a.strip() != ""
        ]
        # Exclude layers from project that aren't pertinent to operation
        for layer in QgsProject.instance().mapLayers().values():
            if not layer.name() in process_layer_names and (
                not layer.source() in process_layer_names
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
        vector_child_alg_steps = 2 if self.output_crs else 1  # Child processes per vector layer
        raster_child_alg_steps = 1  # Child processes per raster layer
        vector_lyrs = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.VectorLayer
        ]
        rasters_lyrs = [
            layer
            for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.RasterLayer
        ]

        child_processes = (
            (len(vector_lyrs) * vector_child_alg_steps)
            + (len(rasters_lyrs) * raster_child_alg_steps)
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
            rasters_lyrs,
        )

        # Set jobid (defines output filenames) and destination path
        self.jobid = "OUTPUT" if not "JOBID" in parameters else parameters["JOBID"]

        self.output_path = os.path.dirname(os.path.abspath(parameters["OUTPUT"]))

        self.output_path = (
            os.path.join(
                self.output_path,
                parameters["USERID"],
            )
            if "USERID" in parameters
            else self.output_path
        )
        self.output_path = (
            os.path.join(
                self.output_path,
                parameters["VENDORID"],
            )
            if "VENDORID" in parameters
            else self.output_path
        )
        self.output_path = (
            os.path.join(
                self.output_path,
                parameters["PROJECTID"],
            )
            if "PROJECTID" in parameters
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
        if self.output_crs:
            QgsProject.instance().setCrs(QgsCoordinateReferenceSystem(self.output_crs))

        # Save changes
        QgsProject.instance().write()

        clipping_geometry = self.generateClippingGeometry(parameters, context, feedback)

        self.setProjectExtent(parameters, context, feedback, clipping_geometry)

        for layer in QgsProject.instance().mapLayers().values():
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
        zip = self.zipOutputs(parameters, context, feedback)
        # Remove obsolete files
        self.removeOutputs(parameters, context, feedback, [".gpkg", ".tif"])

        return {self.OUTPUT: zip}
