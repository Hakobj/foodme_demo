"""Port of DishControllerTest.java.

The JUnit version uses chef 1 from the H2 fixture (2 active dishes, first = "Lavash Wrap").
Against the Postgres seed the chef and its menu are looked up through the API.
"""

from support.api import active_chefs, chef_detail


def test_get_active_dishes_for_chef_returns_only_active_dishes(api):
    chef_id = active_chefs(api)[0]["id"]

    res = api.dishes.active_for_chef(chef_id)

    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["dishDtoList"], list)
    assert body["count"] > 0
    assert all(d["status"] == "ACTIVE" for d in body["dishDtoList"])


# FM-FLAKE-03
def test_get_active_dishes_for_chef_first_result_is_first_menu_dish(api):
    chef_id = active_chefs(api)[0]["id"]
    expected_first = chef_detail(api, chef_id)["dishes"][0]["nameEn"]

    res = api.dishes.active_for_chef(chef_id)

    assert res.status_code == 200
    assert res.json()["dishDtoList"][0]["nameEn"] == expected_first
