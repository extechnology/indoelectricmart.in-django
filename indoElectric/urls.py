"""
URL configuration for indoElectric project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from indoApp.views import *

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="categories")
router.register("brands", BrandViewSet, basename="brands")
router.register("products", ProductViewSet, basename="products")
router.register("attributes", AttributeViewSet, basename="attributes")
router.register("category-attributes", CategoryAttributeViewSet, basename="category-attributes")
router.register("product-attributes", ProductAttributeValueViewSet, basename="product-attributes")

router.register("home-banner", HomeBannerViewSet, basename="home-banner")
router.register("latest-launches", LatestLaunchesViewSet, basename="latest-launches")



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path("search/", SearchAPIView.as_view(), name="search"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
