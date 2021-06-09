import pytest

from adapters import repository
from services import unit_of_work, messagebus, handlers
from domain import events
from datetime import date


class FakeRepository(repository.AbstractProductRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref):
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None,
        )


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_for_new_product():
    uow = FakeUnitOfWork()
    messagebus.handle(events.BatchCreated("b1", "CRUNCHY-ARMCHAIR", 100, None), uow)
    assert uow.products.get("CRUNCHY-ARMCHAIR") is not None
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    messagebus.handle(events.BatchCreated("b1", "GARISH-RUG", 100, None), uow)
    messagebus.handle(events.BatchCreated("b2", "GARISH-RUG", 99, None), uow)
    assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


def test_returns_allocation():
    uow = FakeUnitOfWork()
    messagebus.handle(events.BatchCreated("batch1", "COMPLICATED-LAMP", 100, None), uow)
    result = messagebus.handle(
        events.AllocationRequired("o1", "COMPLICATED-LAMP", 10), uow
    )
    assert result[0] == "batch1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    messagebus.handle(events.BatchCreated("b1", "AREALSKU", 100, None), uow)

    with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENTSKU"):
        messagebus.handle(events.AllocationRequired("o1", "NONEXISTENTSKU", 10), uow)


def test_allocate_commits():
    uow = FakeUnitOfWork()
    messagebus.handle(events.BatchCreated("b1", "OMINOUS-MIRROR", 100, None), uow)
    messagebus.handle(events.AllocationRequired("o1", "OMINOUS-MIRROR", 10), uow)
    assert uow.committed


def test_changes_available_quantity():
    uow = FakeUnitOfWork()
    messagebus.handle(events.BatchCreated("batch1", "ADORABLE-SETTEE", 100, None), uow)
    [batch] = uow.products.get(sku="ADORABLE-SETTEE").batches
    assert batch.available_quantity == 100

    messagebus.handle(events.BatchQuantityChanged("batch1", 50), uow)
    assert batch.available_quantity == 50


def test_reallocates_if_necessary():
    uow = FakeUnitOfWork()
    event_history = [
        events.BatchCreated("batch1", "OMINOUS-MIRROR", 50, None),
        events.BatchCreated("batch1", "OMINOUS-MIRROR", 50, date.today()),
        events.AllocationRequired("order1", "OMINOUS-MIRROR", 20),
        events.AllocationRequired("order2", "OMINOUS-MIRROR", 20),
    ]

    for e in event_history:
        messagebus.handle(e, uow)

    [batch1, batch2] = uow.products.get(sku="OMINOUS-MIRROR").batches
    assert batch1.available_quantity == 10
    assert batch2.available_quantity == 50

    messagebus.handle(events.BatchQuantityChanged("batch1", 25), uow)
    assert batch1.available_quantity == 5
    assert batch2.available_quantity == 30
