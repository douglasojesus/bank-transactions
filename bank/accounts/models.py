from django.db import models
from django.contrib.auth.models import AbstractUser # Importar AbstractUser

class Client(models.Model, AbstractUser):
    # Fields in User: password, username, first_name, last_name, email.
    _balance = models.DecimalField()

    def __str__(self):
        return self.first_name + self.last_name
    
    def get_saldo(self):
        return self._balance

    def receive_transaction(self, value):
        self._balance += value
        return True
    
