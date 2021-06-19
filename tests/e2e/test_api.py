import pytest
from tests.random_refs import random_sku, random_batchref, random_orderid
from tests.e2e.api_client import post_to_add_batch, post_to_allocate, get_allocation


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_batch_is_allocated():
    orderid = random_orderid()
    sku, othersku = random_sku(), random_sku("other")
    early_batch = random_batchref(1)
    later_batch = random_batchref(2)
    other_batch = random_batchref(3)

    post_to_add_batch(later_batch, sku, 100, "2011-01-02")
    post_to_add_batch(early_batch, sku, 100, "2011-01-01")
    post_to_add_batch(other_batch, othersku, 100, None)

    response = post_to_allocate(orderid, sku, 3)

    assert response.status_code == 202

    r = get_allocation(orderid)
    assert r.ok
    assert r.json() == [
        {"sku": sku, 
        "batchref": early_batch
        },
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, order_id = random_sku(), random_orderid()
    response = post_to_allocate(order_id, unknown_sku, 20, False)

    assert response.status_code == 400
    assert response.json()["message"] == f"Invalid sku {unknown_sku}"

    r = get_allocation(order_id)
    assert r.status_code == 404
