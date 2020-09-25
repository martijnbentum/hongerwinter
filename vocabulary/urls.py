from django.urls import include,path,re_path

from . import views

app_name = 'vocabulary'
urlpatterns = [
	path('',views.hello_world,name='hello_world'),
]
