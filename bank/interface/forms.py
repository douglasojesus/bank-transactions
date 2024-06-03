from django import forms

class TransactionForm(forms.Form):
    value_to_transfer = forms.DecimalField(max_digits=10, decimal_places=2)
    port_to_transfer = forms.CharField(max_length=36, required=False)
    ip_to_transfer = forms.CharField(max_length=36, required=False)
    client_to_transfer = forms.CharField(max_length=100, required=False)

    