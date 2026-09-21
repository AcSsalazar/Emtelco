from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health", health, name="health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.accounts.profile_urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.orders.urls")),
    path("api/", include("apps.conversations.urls")),
    # Documentation:
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path('docs/', SpectacularSwaggerView.as_view(), name='swagger-ui')
         
]

admin.site.site_header = "Emtelco — Administración"
admin.site.site_title = "Emtelco"
admin.site.index_title = "Datos del agente (pedidos, garantías, tickets, conversaciones)"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
