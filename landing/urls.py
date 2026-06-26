from django.urls import path

from landing import views

urlpatterns = [
    path('', views.landing_index, name='landing_index'),
    path('lead/', views.submit_lead, name='landing_lead'),
]
