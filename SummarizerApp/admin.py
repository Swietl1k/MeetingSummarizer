from django.contrib import admin
from .models import User, RecordingTime

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('UID', 'email') 
    search_fields = ('UID', 'email')  
    list_filter = ('UID',)  

@admin.register(RecordingTime)
class RecordingTimeAdmin(admin.ModelAdmin):
    list_display = ('RID', 'time_start', 'time_end') 
    search_fields = ('RID', 'time_start', 'time_end')  
    list_filter = ('time_start',)  
