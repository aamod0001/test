from django.urls import path
from . import views

urlpatterns = [
    # Frontend Serve Page
    path('', views.serve_dashboard, name='dashboard'),

    # Main search endpoint
    path('getbloodbanks/<str:latitude>/<str:longitude>/<str:type>', views.get_blood_banks, name='get_blood_banks'),
    
    # Write endpoint
    path('addBank', views.add_bank, name='add_bank'),
    
    # New REST APIs
    path('api/bloodbanks', views.get_all_bloodbanks, name='api_bloodbanks'),
    path('api/bloodbanks/<int:bank_id>/stock', views.manage_stock, name='api_manage_stock'),
    path('api/bloodrequests', views.manage_requests, name='api_manage_requests'),
    path('api/bloodrequests/<int:request_id>/fulfill', views.fulfill_request, name='api_fulfill_request'),
    path('api/stats', views.get_stats_dashboard, name='api_stats'),
    
    # Debug endpoints
    path('debug/junction-count', views.get_junction_count, name='get_junction_count'),
    path('debug/junction-data', views.get_junction_data, name='get_junction_data'),
    path('debug/available-types', views.get_available_types, name='get_available_types'),
    path('debug/test-join', views.test_join, name='test_join'),
]
