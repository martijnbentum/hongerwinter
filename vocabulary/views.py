from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

def hello_world(request):
	return HttpResponse('hello_world')

# Create your views here.
