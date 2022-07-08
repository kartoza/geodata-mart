from django import forms

# from datetime import datetime
# from django.urls import reverse_lazy
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import UneditableField
from geodata_mart.maps.models import Job


class JobForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = "job-form"
        self.helper.layout = Layout(
            UneditableField("job_id", readonly=True),
            UneditableField("user_id", readonly=True),
            UneditableField("project_id", readonly=True),
            UneditableField("layers", readonly=True),
            UneditableField("state", readonly=True),
            UneditableField("parameters", readonly=True),
        )

    class Meta:
        model = Job
        fields = ["job_id", "user_id", "project_id", "layers", "state", "parameters"]
