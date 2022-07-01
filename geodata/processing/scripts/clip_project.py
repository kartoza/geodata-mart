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
    QgsProcessingUtils,
    QgsProcessingMultiStepFeedback,
    QgsProject,
    QgsFields,
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
    # QgsProcessingParameterGeometry,
    # QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFileDestination,
    QgsProcessingDestinationParameter,
)
from qgis import processing
import os


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

    # PROJECTID = "PROJECTID"
    # VENDORID = "VENDORID"
    # USERID = "USERID"
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

        # User id should probably be used to force the path of the output
        # so that proper permissions can be configured on web services (django/ s3 etc).

        # User/ vendor/ project id
        # parameter = QgsProcessingParameterString(
        #     name=self.USERID,
        #     description=self.tr("User ID"),
        #     isOptional=True,
        #     multiline=False,
        # )
        # self.addParameter(parameter)
        # del(parameter)

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
            defaultValue="EPSG:4326",
        )
        self.addParameter(parameter)
        del parameter

        # TODO: Integer used for simplicity, but double values should be supported
        parameter = QgsProcessingParameterNumber(
            self.BUFFER_DIST_KM, "Buffer", type=QgsProcessingParameterNumber.Integer
        )
        # parameter = QgsProcessingParameterNumber(
        #     self.BUFFER_DIST_KM, 'Buffer', type=QgsProcessingParameterNumber.Double
        # )
        # parameter.setMetadata( {'widget_wrapper':{ 'decimals': 2 }})
        self.addParameter(parameter)
        del parameter

        # Output geopackage
        parameter = QgsProcessingParameterFileDestination(
            # parameter = QgsProcessingDestinationParameter(
            name=self.OUTPUT,
            description=self.tr("Output File"),
        )
        parameter.setMetadata({"widget_wrapper": {"dontconfirmoverwrite": True}})
        self.addParameter(parameter)
        del parameter

    def zipOutputs(self, parameters, context, feedback):
        """
        Compile the outputs from the processing tool into a single zip file
        """
        try:
            feedback.pushInfo(f"Adding outputs to archive")
            from zipfile import ZipFile

            file_name = parameters["OUTPUT"] + f".zip"
            file_paths = []
            output_gpkg = parameters["OUTPUT"] + f".gpkg"
            outputs_dir = os.path.abspath(os.path.join(output_gpkg, os.pardir))
            max_depth = 1
            for root, directories, files in os.walk(outputs_dir):
                if root[len(outputs_dir) :].count(os.sep) < max_depth:
                    for filename in files:
                        # join the two strings in order to form the full filepath.
                        filepath = os.path.join(root, filename)
                        file_paths.append(filepath)

            with ZipFile(file_name, "w") as zip:
                # writing each file one by one
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
            output_gpkg = parameters["OUTPUT"] + f".gpkg"
            outputs_dir = os.path.abspath(os.path.join(output_gpkg, os.pardir))
            max_depth = 1
            for root, directories, files in os.walk(outputs_dir):
                if root[len(outputs_dir) :].count(os.sep) < max_depth:
                    for filename in files:
                        # join the two strings in order to form the full filepath.
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

    def initializeGpkg(self, parameters, context, feedback):
        """
        Remove an existing geopackage equivalent to the output gpkg uri,
        and instantiate a new geopackage with no data (or select metadata)

        Raises:
            QgsProcessingException: Issues with removal or cretion indicating permissions issues
        """
        # check if the output geopackage exists,
        # then remove and instantiate it.
        output_gpkg = parameters["OUTPUT"] + ".gpkg"
        feedback.pushInfo(f"Generating {output_gpkg}")
        if os.path.exists(output_gpkg):
            try:
                os.remove(output_gpkg)
                feedback.pushInfo(f"Existing {output_gpkg} has been removed")
            except OSError:
                raise QgsProcessingException(
                    "Unable to remove existing output geopackage. Check permissions and file locks."
                )
            except Exception as e:
                feedback.reportError(str(e), fatalError=True)

        try:
            md = QgsProviderRegistry.instance().providerMetadata("ogr")
            conn = md.createConnection(output_gpkg, {})
            conn.createVectorTable(
                "",
                "__geodatamart__",
                QgsFields(),
                QgsWkbTypes.NoGeometry,
                QgsCoordinateReferenceSystem(),
                True,
                {},
            )
        except Exception as e:
            raise QgsProcessingException(
                "Unable to create new output geopackage. Check permissions and file locks."
            )
        finally:
            del md, conn

    def setProjectExtent(self, parameters, context, feedback, layer):
        layer.updateExtents()
        extent = QgsReferencedRectangle(
            layer.extent(), QgsCoordinateReferenceSystem(parameters["OUTPUT_CRS"])
        )
        QgsProject.instance().viewSettings().setDefaultViewExtent(extent)
        print(f"set extent to {layer.extent()}")
        QgsProject.instance().write()

    def generateClippingGeometry(self, parameters, context, feedback):
        """
        Generate the buffered geometry used to clip data, save the
        geometry layer to file and return the result.
        """

        feedback.pushInfo(f"Generating clipping bounds")

        try:
            # Generate clipping geometry
            # Expects single wkt area atm. Should rather iterate over geojson featurecollection and
            # project individual features, then union everything into the final buffer + clip geom
            # QgsVectorLayer(GeojsonAsString,"mygeojson","ogr")
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

            projected = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": clip_layer,
                    # If we convert clipping geometries to equal earth, this forces
                    # metric map units for the buffer. Considering the global scope
                    # and accuracy requirements for a regional data clip, anywhere on earth
                    # this should be a suitable approach, at least initially. Note that the
                    # QGIS/ GDAL processes used for clipping have been tested to ensure that
                    # OTF projection is supported, so this may not be suitable for broader use cases.
                    # "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:8857"),
                    # Fallback due to 3857, as some operations (e.g. raster clipping) are not supported:
                    # >> PROJ: proj_as_wkt: Unsupported conversion method: Equal Earth
                    "TARGET_CRS": QgsCoordinateReferenceSystem("EPSG:3857"),
                    # "TARGET_CRS": QgsCoordinateReferenceSystem(parameters["OUTPUT_CRS"]),
                    "OPERATION": "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=webmerc +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84",
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=True,
            )["OUTPUT"]

            buffered = processing.run(
                "native:buffer",
                {
                    "INPUT": projected,
                    "DISTANCE": (float(parameters["BUFFER_DIST_KM"]) * 1000),
                    "SEGMENTS": 5,
                    "END_CAP_STYLE": 0,
                    "JOIN_STYLE": 0,
                    "MITER_LIMIT": 2,
                    "DISSOLVE": True,
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=True,
            )["OUTPUT"]

            clipping_geometry = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": buffered,
                    "TARGET_CRS": parameters["OUTPUT_CRS"],
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
            )["OUTPUT"]

            # Store clipping bounds as layer
            clip_file_output = parameters["OUTPUT"] + ".gpkg"
            save_clip_options = QgsVectorFileWriter.SaveVectorOptions()
            save_clip_options.layerName = "geodatamart"
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

        try:
            layer_name = layer.name().replace('"', "")
            uri = parameters["OUTPUT"] + f".gpkg"

            clipped_vector = processing.run(
                "native:clip",
                {
                    "INPUT": layer.source(),
                    "OVERLAY": clip_layer,
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=True,
            )["OUTPUT"]

            output_vector = processing.run(
                "native:reprojectlayer",
                {
                    "INPUT": clipped_vector,
                    "TARGET_CRS": QgsCoordinateReferenceSystem(
                        parameters["OUTPUT_CRS"]
                    ),
                    "OPERATION": "+proj=noop",
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=True,
            )["OUTPUT"]

            # Save the clipped layer result to file
            save_vector_options = QgsVectorFileWriter.SaveVectorOptions()
            save_vector_options.layerName = f"{layer_name}"
            save_vector_options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )
            save_vector_options.driverName = "GPKG"
            save_vector_options.symbologyExport = QgsVectorFileWriter.FeatureSymbology
            transform_context = QgsProject.instance().transformContext()
            feedback.pushInfo(f"Saving layer to {uri}")
            filesave_error = QgsVectorFileWriter.writeAsVectorFormatV3(
                output_vector,
                uri,
                transform_context,
                save_vector_options,
            )

            if filesave_error[0] == QgsVectorFileWriter.NoError:
                feedback.pushInfo(f"Clipped result saved to {uri}|{layer_name}")
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
            src_uri = parameters["OUTPUT"] + f".gpkg|layername={layer_name}"
            layer.setDataSource(
                src_uri,
                f"{layer_name}",
                f"ogr",
                vector_source_options,
            )
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

        try:
            layer_name = layer.name().replace('"', "")
            uri = parameters["OUTPUT"] + f".gpkg"

            clipped_raster = processing.run(
                "gdal:cliprasterbymasklayer",
                {
                    "INPUT": layer.source(),
                    "MASK": clip_layer,
                    "SOURCE_CRS": None,
                    "TARGET_CRS": None,
                    "TARGET_EXTENT": None,
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
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=True,
            )["OUTPUT"]

            # TODO: Get GPKG Raster Outputs working. For some reason, the behaviour
            # of these commands change depending on the context, despite being a gdal operation.
            # The commands that fail with QgsProcessing work when used directly from gdal cli,
            # and even using the QGIS GUI results in different behaviours (e.g. whether RASTER_TABLE works)

            # extra_options = "-co APPEND_SUBDATASET=YES"
            # extra_options = (
            #     extra_options + f" -co RASTER_TABLE={layer_name}"
            # )  # apparently suported but doesn't work
            # extra_options = (
            #     extra_options + f" -co TABLE={layer_name}"
            # )  # says unsupported but works from gui ¯\_(ツ)_/¯
            # try:
            #     projected_raster = processing.run(
            #         "gdal:warpreproject",
            #         {
            #             "INPUT": clipped_raster,
            #             "SOURCE_CRS": None,
            #             "TARGET_CRS": QgsCoordinateReferenceSystem(
            #                 parameters["OUTPUT_CRS"]
            #             ),
            #             "RESAMPLING": 0,
            #             "NODATA": None,
            #             "TARGET_RESOLUTION": None,
            #             "OPTIONS": "COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9",
            #             "DATA_TYPE": 0,
            #             "TARGET_EXTENT": None,
            #             "TARGET_EXTENT_CRS": None,
            #             "MULTITHREADING": False,
            #             "EXTRA": extra_options,
            #             # "OUTPUT": uri,
            #             "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            #         },
            #         context=context,
            #         feedback=feedback,
            #         is_child_algorithm=True,
            #     )["OUTPUT"]
            # except Exception as e:
            #     feedback.reportError(str(e), fatalError=False)
            projected_raster = processing.run(
                "gdal:warpreproject",
                {
                    "INPUT": clipped_raster,
                    "SOURCE_CRS": None,
                    "TARGET_CRS": QgsCoordinateReferenceSystem(
                        parameters["OUTPUT_CRS"]
                    ),
                    "RESAMPLING": 0,
                    "NODATA": None,
                    "TARGET_RESOLUTION": None,
                    "OPTIONS": "COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9",
                    "DATA_TYPE": 0,
                    "TARGET_EXTENT": None,
                    "TARGET_EXTENT_CRS": None,
                    "MULTITHREADING": False,
                    "EXTRA": "",
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=True,
            )["OUTPUT"]

            # TODO: translate (and warp) should be unnecessary. We should be
            # able to just use the clip tool with TARGET_CRS, but this is broken atm

            # output_uri = f"{layer_name}.tif"
            output_gpkg = parameters["OUTPUT"] + f".gpkg"
            output_dir = os.path.abspath(os.path.join(output_gpkg, os.pardir))
            output_uri = os.path.join(output_dir, f"{layer_name}.tif")
            processing.run(
                "gdal:translate",
                {
                    "INPUT": projected_raster,
                    "TARGET_CRS": None,
                    "NODATA": None,
                    "COPY_SUBDATASETS": False,
                    "OPTIONS": "",
                    "EXTRA": "",
                    "DATA_TYPE": 0,
                    "OUTPUT": output_uri,
                },
                context=context,
                feedback=feedback,
                # is_child_algorithm=False,  # skip this one in the feedback
            )

        except Exception as e:
            feedback.reportError(str(e), fatalError=False)

        finally:
            # Change the project layers source to the clipped output
            raster_source_options = QgsDataProvider.ProviderOptions()
            raster_source_options.transformContext = (
                QgsProject.instance().transformContext()
            )
            # src_uri = parameters["OUTPUT"] + f".gpkg|layername={layer_name}"
            # src_uri = f"{layer_name}.tif"
            output_gpkg = parameters["OUTPUT"] + f".gpkg"
            output_dir = os.path.abspath(os.path.join(output_gpkg, os.pardir))
            # TODO: Assuming tif output is NOT recommended. This should be
            # inferred from the input layer attributes, which is not managed
            # currently as gpkg raster outputs have their own requirements
            src_uri = os.path.join(output_dir, f"{layer_name}.tif")
            layer.setDataSource(
                src_uri,
                f"{layer_name}",
                f"gdal",
                raster_source_options,
            )
            layer.reload()
            # layer.updateExtents()

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

        # # Configure MultiStepFeedback
        # additional_steps = 2  # steps for clipping and buffering
        #                       # input clipping bounds etc
        # child_alg_steps = 2  # Child processes per layer
        # child_processes = (len(QgsProject.instance().mapLayers())*child_alg_steps)+additional_steps
        # feedback = QgsProcessingMultiStepFeedback(child_processes, model_feedback)

        self.initializeGpkg(parameters, context, feedback)

        # Save a copy of the project
        # TODO replace projectName with reasonable vendor-project identifier
        output_uri = "geopackage:" + parameters["OUTPUT"] + ".gpkg?projectName=geodata"
        QgsProject.instance().write(output_uri)
        # Load cloned project
        QgsProject.instance().read(output_uri)
        # Set the project coordinate reference system
        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem(parameters["OUTPUT_CRS"])
        )
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
