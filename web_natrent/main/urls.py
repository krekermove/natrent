from django.urls import path
from . import views


app_name = 'main'


urlpatterns = [
     path('', views.MainView.as_view(), name='main_page'),
     path('search_houses/', views.SearchView.as_view(), name='search_houses'),
     path('houses/<int:house_id>/', views.HouseDetailView.as_view(), name='house_detail'),
     path('book-house/', views.BookHouseView.as_view(), name='book_house'),
]