from service.connectors.abstract import Connector
from logging import getLogger
from fastapi import WebSocket


class Whatsapp(Connector):
    service = "whatsapp"
    logger = getLogger(service)

    def __init__(self, phone_number: str, websocket: WebSocket):
        self.phone_number = phone_number
        super().__init__(phone_number, websocket)
