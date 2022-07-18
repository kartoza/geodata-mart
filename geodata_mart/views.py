from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

import mimetypes
from pathlib import Path
from django.conf import settings
from geodata_mart.maps.models import project_storage


@login_required
def geodata(request, path):
    if request.method == "GET":
        BASE_DIR = Path(settings.QGIS_DATA_ROOT)
        protected_paths = ["projects", "processing", "test"]
        protected_paths = [BASE_DIR / protected for protected in protected_paths]
        filepath = BASE_DIR / Path(project_storage.path(path))
        filename = filepath.name

        is_protected = False
        for protected in protected_paths:
            if protected in filepath.parents:
                is_protected = True

        if is_protected and not request.user.is_staff:
            raise PermissionDenied()

        if project_storage.exists(filepath):
            result = project_storage.open(filepath, "rb")
            mime_type, _ = mimetypes.guess_type(filepath)
            response = HttpResponse(result, content_type=mime_type)
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        else:
            raise Http404("File does not exist")
