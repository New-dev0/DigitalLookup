from service.connectors.abstract import Connector
from logging import getLogger
from fastapi import WebSocket


class Facebook(Connector):
    service = "facebook"
    logger = getLogger(service)

    def __init__(self, username: str, websocket: WebSocket) -> None:
        super().__init__(username, websocket)
