from django.db import models
from django.contrib.auth.hashers import make_password, check_password  # Import hash functions

class User(models.Model):
    UID = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=20, unique=True)
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
    UID = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='recordings', db_index=True)
    title = models.CharField(max_length=255)
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()

    def __str__(self):
        return str(self.title)
    

class Summary(models.Model):
    SID = models.AutoField(primary_key=True)
    UID = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='summaries', db_index=True)  # Links to User
    title = models.CharField(max_length=255)
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()
    transcription = models.TextField()  
    summary = models.TextField()  

    def __str__(self):
        return f"Summary for {self.title} by {self.UID.username}"

