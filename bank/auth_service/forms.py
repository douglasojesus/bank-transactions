from django import forms
from accounts.models import Client

class FormCreateClient(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'email', 'username', 'password']
        

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Client.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso. Por favor, escolha outro.")
        return username
    
class FormCreateJointAccount(forms.Form):
    second_person_username = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField()
    
class FormLoginClient(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


