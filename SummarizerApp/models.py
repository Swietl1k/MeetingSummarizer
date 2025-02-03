from django.db import models
from django.contrib.auth.models import User

class RecordingTime(models.Model):
    RID = models.AutoField(primary_key=True)
    UID = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='recordings', db_index=True)
    title = models.CharField(max_length=255)
    window_name = models.CharField(max_length=255, null=True, blank=True)
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()

    def __str__(self):
        return str(f"RID: {self.RID}, Title: {self.title}, Time Start: {self.time_start}, Time End: {self.time_end}")
    

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
