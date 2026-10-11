from django.urls import path
from . import views

urlpatterns = [
    path("boost/", views.boost_view, name="boost"),
    path("boost/status/", views.boost_order_status, name="boost_status"),
]