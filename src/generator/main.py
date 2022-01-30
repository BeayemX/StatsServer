# System
import asyncio

# Custom
import websocketserver
import generator


# Start generator
generator.start()

# Start WebSocket server
try:
    asyncio.get_event_loop().run_until_complete(websocketserver.start())
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    print()
    print("Server stopped manually")


print("Exited.")
