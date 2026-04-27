from django.urls import path
from . import views


app_name = 'main'


urlpatterns = [
     path('', views.MainView.as_view(), name='main_page'),
     path('search_houses/', views.SearchView.as_view(), name='search_houses'),
]