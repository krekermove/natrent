from django.urls import path
from . import views


app_name = 'main'


urlpatterns = [
     path('', views.MainView.as_view(), name='main_page'),
     path('feedback/', views.FeedbackView.as_view(), name='feedback'),
     path('search_houses/', views.SearchView.as_view(), name='search_houses'),
     path('houses/<int:house_id>/', views.HouseDetailView.as_view(), name='house_detail'),
     path('houses/<int:house_id>/book/', views.BookHouseView.as_view(), name='book_house'),
     path('legal/personal-data-consent/', views.PersonalDataConsentView.as_view(), name='personal_data_consent'),
     path('legal/user-agreement/', views.UserAgreementView.as_view(), name='user_agreement'),
     path('legal/privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
]