from django.db import models

# Create your models here.
class Bank(models.model):
    ip = models.CharField(max_length=50)
    porta = models.CharField(max_length=7)
    