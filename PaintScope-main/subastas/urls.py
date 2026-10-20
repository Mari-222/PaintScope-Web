from django.urls import path

from . import views

app_name = "subastas"

urlpatterns = [
    path("", views.explorar, name="explorar"),
    path("en-vivo/", views.en_vivo, name="en_vivo"),
    path("mis-pujas/", views.mis_pujas, name="mis_pujas"),
    path("api/dashboard/", views.api_dashboard, name="api_dashboard"),
    path("api/<int:pk>/", views.api_estado, name="api_estado"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/pujar/", views.pujar, name="pujar"),
]
