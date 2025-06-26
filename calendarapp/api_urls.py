from rest_framework.routers import DefaultRouter
from .api_views import UserViewSet, EventViewSet, AppointmentViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'events', EventViewSet)
router.register(r'appointments', AppointmentViewSet)

urlpatterns = router.urls