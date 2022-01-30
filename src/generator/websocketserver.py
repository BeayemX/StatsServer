# Standard library
import sys
import time
import datetime # Needed for test values

# PIP
import psutil

# Network
import requests
import json

# Websockets
import asyncio
import websockets


# Config
with open('config.json') as f:
    conf = json.load(f)


# Constants
HOST = conf['host']
RECONNECT_TIME = 5


# Variables
class GlobalVars:
    def __init__(self) -> None:
        self.pending_requests = []

Globals = GlobalVars()


# Functions
async def main():
    async with websockets.connect(HOST) as websocket:
        async def send(data):
            await websocket.send(json.dumps(data))

        print("Connection established")

        while True:
            if len(Globals.pending_requests) > 0:
                working_queue = Globals.pending_requests
                Globals.pending_requests = []

                for data in working_queue:
                    await send(data)

            await asyncio.sleep(1)


async def start():
    print("Starting WebSocket server.")
    while True:
        try:
            #asyncio.get_event_loop().run_until_complete(main())
            await main()

        except ConnectionRefusedError:
            now = datetime.datetime.now()
            print(f"Connection refused: {now.strftime('%Y-%m-%d_%H:%M:%S')}")
            time.sleep(RECONNECT_TIME)

        except KeyboardInterrupt:
            print("Exiting")
            sys.exit(0)

        except Exception as e:
            print(e)