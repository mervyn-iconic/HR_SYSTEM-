from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('HR', 'HR  Manager'),
        ('SUPERVISOR', 'Supervisor'),
        ('EMPLOYEE', 'Employee'),
    ]

    role = models.CharField( 
        max_length=20,
        choices=ROLE_CHOICES,
        default='EMPLOYEE'
    )