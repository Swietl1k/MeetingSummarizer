from rest_framework import serializers
from .models import User, RecordingTime
from datetime import datetime 

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['UID', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User(
            email=validated_data['email']
        )
        user.set_hash_password(validated_data['password'])
        user.save()
        return user
    
class RecordingTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordingTime
        fields = ['RID', 'time_start', 'time_end']

    '''
    def create(self, validated_data):
        recording_time = RecordingTime(
            time_start = datetime.strptime(validated_data['time_start'], "%Y-%m-%d-%H-%M-%S"),
            end_start = datetime.strptime(validated_data['end_start'], "%Y-%m-%d-%H-%M-%S"),
        )
        recording_time.save()
        return recording_time
    '''