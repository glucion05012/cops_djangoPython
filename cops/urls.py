"""
URL configuration for cops project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from crs import views
from cps import views as cps_views
from crs import views_permittee
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # settings
    path('admin/', admin.site.urls),
    path('test/', views.test, name='test'),
    
    # login page
    path('', views.index, name='index'),
    path('check_existing/', views.check_existing, name='check_existing'),
    path('create_account/', views.create_account, name='create_account'),
    path('login/', views.login, name='login'),
    
    # get session from dashboard
    path('get_session/', views.get_session, name='get_session'),
    
    # dashbaord
    path('dashboard/', views.dashboard, name='dashboard'),
    path('myapplications/', views.myApplications, name='myApplications'),
    
    
    # permittee enrollment
    path('permittee_enrollment/', views_permittee.index, name='permittee_enrollment'),
    
    # get ajax list
    path('permittee_list_json', views_permittee.permittee_list_json, name='permittee_list_json'), 
    path('add_permittee', views_permittee.add_permittee, name='add_permittee'),
    
    
    
    #chainsaw_permit_system
    #import
    path('cps/apply', cps_views.index, name='import_apply'),
    path('submit-import/', cps_views.submit_import, name='submit_import'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)