from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

import mimetypes
from pathlib import Path
from urllib.parse import unquote
from django.conf import settings
from geodata_mart.maps.models import project_storage

import logging

logger = logging.getLogger(__name__)


def geodata(request, path):
    if request.method == "GET":
        BASE_DIR = Path(settings.QGIS_DATA_ROOT)
        protected_paths = ["projects", "processing", "test"]
        protected_paths = [BASE_DIR / protected for protected in protected_paths]
        public_paths = ["images", "__sized__"]
        public_paths = [BASE_DIR / public for public in public_paths]
        filepath = BASE_DIR / Path(project_storage.path(unquote(path)))
        filename = filepath.name

        is_protected = False
        for protected in protected_paths:
            if protected in filepath.parents:
                is_protected = True

        if is_protected and not request.user.is_staff:
            raise PermissionDenied()

        is_public = False
        for public in public_paths:
            if public in filepath.parents:
                is_public = True

        if project_storage.exists(filepath) and request.user.is_authenticated:
            result = project_storage.open(filepath, "rb")
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "text/plain"
            response = HttpResponse(result, content_type=mime_type)
            response["Content-Disposition"] = f"attachment; filename={filename}"
            logger.info(f"{filename} downloaded by {request.user.id}")
            return response
        elif project_storage.exists(filepath) and not is_public:
            raise PermissionDenied()
        elif project_storage.exists(filepath):
            result = project_storage.open(filepath, "rb")
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "text/plain"
            response = HttpResponse(result, content_type=mime_type)
            response["Content-Disposition"] = f"attachment; filename={filename}"
            logger.info(f"{filename} downloaded by {request.user.id}")
            return response
        else:
            raise Http404("File does not exist")
