from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class ClientManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, username, password=None, balance=0, is_superuser=False, is_joint_account=False, user_one='', user_two=''):
        if not email:
            raise ValueError('Usuário precisa de um email')

        email = self.normalize_email(email)
        user = self.model(first_name=first_name, last_name=last_name, 
                          email=email, username=username, balance=balance, 
                          is_superuser=is_superuser, is_joint_account=is_joint_account,
                          user_one=user_one, user_two=user_two)

        user.set_password(password)
        user.save()

        return user

class Client(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField('Email', unique=True)
    username = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    blocked_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0) 
    in_transaction = models.BooleanField(default=False)
    in_transaction_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    is_staff = models.BooleanField('Staff', default=True)
    is_active = models.BooleanField('Ativo', default=True)
    is_superuser = models.BooleanField(default=False)
    is_joint_account = models.BooleanField(default=False)
    user_one = models.CharField(max_length=255, null=True, blank=True)
    user_two = models.CharField(max_length=255, null=True, blank=True)

    objects = ClientManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username
    
    def __str__(self):
        return self.username
