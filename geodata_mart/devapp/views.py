from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def devapp_map_view(request):
    return render(request, "maps/default.html")
