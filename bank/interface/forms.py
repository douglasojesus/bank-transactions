from django.forms import ModelForm
from accounts.models import Client

class FormClient(ModelForm):
    class Meta:
        model = Client
        fields = ("*")