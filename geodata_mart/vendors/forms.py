from django import forms

from crispy_forms.helper import FormHelper
from geodata_mart.vendors.models import VendorMessage


class VendorMessageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = "msg-form"

    class Meta:
        model = VendorMessage
        fields = [
            "sender",
            "receiver",
            "content",
            "subject",
            "category",
            "project",
            "job",
        ]
