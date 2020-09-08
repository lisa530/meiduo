from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^qq/login/$',views.QQAuthURLView.as_view())
]