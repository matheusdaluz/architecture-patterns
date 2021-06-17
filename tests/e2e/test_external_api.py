import json
import pytest
from tests.random_refs import random_orderid, random_sku, random_batchref
from tenacity import Retrying, stop_after_delay
from  tests.e2e.api_client import post_to_add_batch, post_to_allocate
from  tests.e2e.redis_client import subscribe_to, publish_message


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
# @pytest.mark.usefixtures("restart_redis_pubsub")
def test_change_batch_quantity_leading_to_reallocation():
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("newer")
    post_to_add_batch(earlier_batch, sku, qty=10, eta="2011-01-02")
    post_to_add_batch(later_batch, sku, qty=10, eta="2011-01-02")
    response = post_to_allocate(orderid, sku, 10)
    assert response.json()["batchref"] == earlier_batch

    subscription = subscribe_to("line_allocated")
    publish_message(
        "change_batch_quantity",
        {
            "batchref": earlier_batch,
            "qty": 5,
        },
    )

    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(messages)
            data = json.loads(messages[0]["data"])
            assert data["orderid"] == orderid
            assert data["batchref"] == later_batch
