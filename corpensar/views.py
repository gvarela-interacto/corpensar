from decimal import Decimal
import json
import locale
from django.contrib import messages  
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse, HttpResponseForbidden,HttpResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib.auth.hashers import make_password
from .models import *
from django.contrib.auth.decorators import login_required
locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django import forms
from django.core.exceptions import ValidationError
import re
from .decorators import *
import csv
from datetime import datetime

def registro_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)  # Usamos el formulario por defecto
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/registro.html', {'form': form})

def custom_logout(request):
    logout(request)
    return redirect('login')

@login_required
def index_view(request):
    
    return render(request, 'index.html')
