from django.db import models
from django.contrib.auth.hashers import make_password, check_password  # Import hash functions

class User(models.Model):
    UID = models.AutoField(primary_key=True)
    email = models.EmailField()
    password = models.CharField(max_length=255)  # hashed

    def set_hash_password(self, raw_password):
        ''' set a hashed password '''
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return str(self.email)
    

class RecordingTime(models.Model):
    RID = models.AutoField(primary_key=True)
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()

    def __str__(self):
        return str(self.time_start)