from django.db import models
from django.contrib.auth.models import User

class Client(User):
    # AbstractUser já inclui os campos: password, username, first_name, last_name, email
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    blocked_balance = models.FloatField(default=0.0)  # Novo campo para saldo bloqueado

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_saldo(self):
        return self.balance

    def receive_transaction(self, value):
        self.balance += value
        self.save()
        return True
