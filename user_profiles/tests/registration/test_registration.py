from django.urls import reverse
from django.contrib.auth.models import Group, User


def test_user_registration(
    api_client, user_group, staff_group, registration_payload
):
    url = reverse("signup")

    response = api_client.post(url, data=registration_payload, format="json")
    print(response)
    assert response.status_code == 201
    assert "pranab has been registered" in response.data

    user = User.objects.get(username=registration_payload["username"])
    assert (
        user.groups.first() == user_group
        if not registration_payload["is_staff"]
        else staff_group
    )


def test_user_login(api_client, registered_user, login_payload):
    url = reverse("login")

    response = api_client.post(url, data=login_payload, format="json")
    print(response)
    assert response.status_code == 200
    assert response.data["status"] == "success"
    assert "data" in response.data

    assert "ongoing_events_mail" in response.data["data"]
