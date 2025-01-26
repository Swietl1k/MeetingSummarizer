from django.urls import path
from . import views 

urlpatterns = [
    path('start_recording/', views.start_recording, name='start_recording'),
    path('end_recording/', views.end_recording, name='end_recording'),
    path('schedule_recording/', views.schedule_recording, name='schedule_recording'),
    path('test/', views.test, name='test'),
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('start_monitoring/', views.start_monitoring, name='start_monitoring'),
    path('get_recordings/', views.get_recordings, name='get_recordings'),
    path('get_summaries/', views.get_summaries, name='get_summaries'),
    path('delete_recording/', views.delete_recording, name='delete_recording'),
    path('delete_summary/', views.delete_summary, name='delete_summary'),
    path('generate_pdf/', views.generate_pdf, name='generate_pdf'),
]   
