from domain import events
from typing import List, Dict, Type, Callable
from services import handlers
from services import unit_of_work


def handle(event: events.Event, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [event]
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            results.append(handler(event, uow=uow))
        return results


HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.BatchCreated: [handlers.add_batch],
    events.AllocationRequired: [handlers.allocate],
    events.BatchQuantityChanged: [handlers.change_batch_quantity]
}  # type: Dict[Type[events.Event], List[Callable]]
