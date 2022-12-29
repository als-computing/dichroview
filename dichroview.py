#!/usr/bin/env python

"""dichroview.py

    View a live bluesky event-model data stream
    * API to accept runs & data
    * Process and plot the data

    CREDIT for the websocket broadcasting solution 
      belongs to William Hayes.
      https://gist.github.com/wshayes/c22a07e9815d980a9a1d0bd1ab56a690
    
    CREDIT for the solution to mounting a Dash subapp in FastAPI
      belongs to SEary342 and Russell Snyder
      https://github.com/rusnyder/fastapi-plotly-dash/blob/master/app.py

"""

from typing import List
from datetime import datetime, date, time #, timedelta
# from dateutil import relativedelta as rel_date
import pytz

from fastapi import FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.websockets import WebSocket, WebSocketDisconnect
import json

from dichroview_dash import create_dash_app

import uvicorn


app = FastAPI()


@app.get("/")
async def get():
    return RedirectResponse("/docs")


class Notifier:
    def __init__(self):
        self.connections: List[WebSocket] = []
        self.generator = self.get_notification_generator()

    async def get_notification_generator(self):
        while True:
            message = yield
            await self._notify(message)

    async def push(self, msg):
        print(f'Push: {self.connections=}')
        await self.generator.asend(msg)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        print(f'Add: {self.connections=}')

    def remove(self, websocket: WebSocket):
        self.connections.remove(websocket)
        print(f'Remove: {self.connections=}')

    async def _notify(self, message: str):
        living_connections = []
        while len(self.connections) > 0:
            # Looping like this is necessary in case a disconnection is handled
            # during await websocket.send_text(message)
            websocket = self.connections.pop()
            await websocket.send_json(message)
            living_connections.append(websocket)
        self.connections = living_connections


start_notifier = Notifier()
event_notifier = Notifier()


@app.websocket("/new-run")
async def ws_add_data(websocket: WebSocket):
    await start_notifier.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        start_notifier.remove(websocket)


@app.websocket("/add-data")
async def ws_add_data(websocket: WebSocket):
    await event_notifier.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        event_notifier.remove(websocket)


# @app.get("/push/{message}")
# async def push_to_connected_websockets(message: str):
#     await notifier.push(f"! Push notification: {message} !")


@app.post("/start")
async def new_run(message: Request):
    doc = json.loads(await message.json())
    tz_id = 'America/Los_Angeles'
    timezone = pytz.timezone(tz_id)
    time = datetime.fromtimestamp(doc["time"], tz=timezone).isoformat()
    print(time)
    print(doc["uid"])
    # await start_notifier.push(doc)
    await start_notifier.push({"start": doc})


@app.post("/event")
async def add_data(message: Request):
    doc = json.loads(await message.json())
    # print(f'...doc["uid"]')
    # await event_notifier.push(doc)
    await event_notifier.push({"event": doc})


@app.on_event("startup")
async def startup():
    # Prime the push notification generator
    await start_notifier.generator.asend(None)
    await event_notifier.generator.asend(None)


# A bit odd, but the only way I've been able to get prefixing of the Dash app
# to work is by allowing the Dash/Flask app to prefix itself, then mounting
# it to root
dash_app = create_dash_app(requests_pathname_prefix="/dash/")
app.mount("/dash", WSGIMiddleware(dash_app.server))

if __name__ == '__main__':
    uvicorn.run(app, port=8003)
