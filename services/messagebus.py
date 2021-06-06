from domain import events
from typing import List, Dict, Type, Callable
from adapters import email


def handle(event: events.Event):
    for handler in HANDLERS[type(event)]:
        handler(event)


def send_out_of_stock_notification(event: events.OutOfStock):
    email.send_email("stock@made.com", f"Out of stock for {event.sku}")


HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification],
}  # type: Dict[Type[events.Event], List[Callable]]
