from django import forms

class TransactionForm(forms.Form):
    value_to_transfer = forms.DecimalField(max_digits=10, decimal_places=2)
    bank_to_transfer = forms.CharField(max_length=100)
    client_to_transfer = forms.CharField(max_length=100)

    