"""Port of ChefControllerTest.java.

The JUnit version asserts the H2 fixture (2 active chefs, chef 1 = "marta-k"). These tests run
against the live Postgres seed, so they look the data up through the API instead.
"""

from support.api import active_chefs


def test_get_active_chefs_returns_active_chefs_only(api):
    res = api.chefs.active(page=0, size=12)

    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["exploreChefResponseDtoList"], list)
    assert body["count"] > 0
    # Inactive chefs must not be listed.
    statuses = {chef["id"]: chef["status"] for chef in body["exploreChefResponseDtoList"]}
    assert all(s == "ACTIVE" for s in statuses.values()), f"non-active chefs listed: {statuses}"


def test_get_chef_by_id_returns_chef_with_dishes(api):
    listed = active_chefs(api)[0]

    res = api.chefs.by_id(listed["id"])

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == listed["id"]
    assert body["username"]
    assert body["username"] == listed["username"]
    assert isinstance(body["dishes"], list)
