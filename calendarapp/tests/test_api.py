import pytest
from django.urls import reverse
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_user_list_api():
    client = APIClient()
    url = reverse('user-list')
    response = client.get(url)
    assert response.status_code in (200, 403)