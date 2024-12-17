from django.urls import path
from . import views 

urlpatterns = [
    path('start_recording', views.start_recording, name='start_recording'),
    path('end_recording', views.end_recording, name='end_recording'),
    path('schedule_recording', views.schedule_recording, name='schedule_recording'),
    path('test', views.test, name='test'),
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
    path('logout', views.logout, name='logout'),
    path('start_monitoring', views.start_monitoring, name='start_monitoring'),



]
