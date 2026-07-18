from django.db import models
class employee(models.Model):
    name = models.CharField(max_length=30)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    hire_date = models.DateField()

    def __str__(self):
        return self.name