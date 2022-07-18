WPS
======================================================================

This stack leverages the `Py-QGIS-WPS <https://github.com/3liz/py-qgis-wps>`_ by 3-Liz for the Web Processing Service.

It is going to expect a QGIS Server `MAP` parameter in order to resolve the relevant process context.

    ::

        http://127.0.0.1:8080/ows/?service=WPS&VERSION=1.0.0&request=GetCapabilities&MAP=project
