from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from geodata_mart.vendors.forms import VendorMessageForm

import logging

logger = logging.getLogger(__name__)


@login_required
def msg(request):
    if request.method == "GET":
        return render(request, "vendors/msg-sent.html")
    elif request.method == "POST":
        form = VendorMessageForm(request.POST)
        if form.errors:
            logger.error(f"{form.errors}")

        if form.is_valid():
            instance = form.save()
            return HttpResponseRedirect(reverse("vendors:msg"))
        else:
            messages.add_message(request, messages.ERROR, "The submission was invalid.")
            return HttpResponseRedirect(
                reverse(
                    "maps:results",
                )
            )
