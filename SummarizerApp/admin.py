from django.contrib import admin
from .models import RecordingTime

@admin.register(RecordingTime)
class RecordingTimeAdmin(admin.ModelAdmin):
    list_display = ('RID', 'time_start', 'time_end', 'title', 'window_name') 
    search_fields = ('RID', 'time_start', 'time_end')  
    list_filter = ('time_start',)  
