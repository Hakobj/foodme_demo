"""API client objects: the HTTP counterpart of the page objects in `pages/`.

Each client wraps one backend controller and returns the raw `requests.Response`, so tests keep
full control over status-code and body assertions.
"""

from clients.foodme_api import FoodMeApi

__all__ = ["FoodMeApi"]
