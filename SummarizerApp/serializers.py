from rest_framework import serializers
from .models import User, RecordingTime, Summary
from datetime import datetime 
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'username']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
class RecordingTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordingTime
        fields = ['RID', 'time_start', 'time_end', 'UID', 'title', 'window_name']
        extra_kwargs = {
            'window_name': {'required': False},
        }


    '''
    def create(self, validated_data):
        recording_time = RecordingTime(
            time_start = datetime.strptime(validated_data['time_start'], "%Y-%m-%d-%H-%M-%S"),
            end_start = datetime.strptime(validated_data['end_start'], "%Y-%m-%d-%H-%M-%S"),
        )
        recording_time.save()
        return recording_time
    '''

class SummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = ['SID', 'UID', 'title', 'time_start', 'time_end', 'transcription', 'summary']