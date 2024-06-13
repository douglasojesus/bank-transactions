from django.db import models

# Create your models here.
class Bank(models.Model):
    ip = models.CharField(max_length=50)
    port = models.CharField(max_length=8)
    name = models.CharField(max_length=100)
    