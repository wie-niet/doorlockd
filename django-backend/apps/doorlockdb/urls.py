from django.urls import path

from . import views

urlpatterns = [
    # long pull
    path(
        "api/lock/long_poll_events",
        views.api_poll_events,
        name="api_poll_events",
    ),
    # ex: /doorlockdb/details/person/<person_id>
    path("details/person/<int:person_id>", views.details_person, name="details_person"),
    # ex: /doorlockdb/details/access/
    path("details/access/", views.details_access, name="details_access"),
    # ex: /doorlockdb/details/person/<person_id>
    path("details/lock/<int:lock_id>", views.details_lock, name="details_lock"),
]
