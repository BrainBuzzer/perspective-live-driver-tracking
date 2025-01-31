import random
import logging
import tornado.websocket
import tornado.web
import tornado.ioloop
from datetime import date, datetime
import perspective
import perspective.handlers.tornado
import json

# Override the default JSON encoder to handle datetime and date objects
old = json.JSONEncoder.default

def new_encoder(self, obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # Use ISO format for better compatibility
    return old(self, obj)

json.JSONEncoder.default = new_encoder

# Generate 500 unique driver IDs
DRIVER_IDS = [f"driver_{i}" for i in range(5000)]

# Generate random geolocation within Manila, Philippines
def random_lat_lng():
    return {
        "lat": random.uniform(14.55, 14.75),  # Approximate latitude range
        "lng": random.uniform(120.95, 121.05),  # Approximate longitude range
    }

# Simulate a data source providing driver location updates
def data_source():
    rows = []
    for _ in range(200):  # Generate data for 200 drivers per update cycle
        location = random_lat_lng()
        rows.append(
            {
                "driver_id": random.choice(DRIVER_IDS),
                "lat": location["lat"],  # Assign random latitude in Manila
                "lng": location["lng"],  # Assign random longitude in Manila
                "lastUpdate": datetime.now(),  # Timestamp of last update
            }
        )
    return rows

# Run a Perspective server in a separate thread to update the data periodically
def perspective_thread(perspective_server):
    client = perspective_server.new_local_client()
    table = client.table(
        {
            "driver_id": "string",
            "lat": "float",
            "lng": "float",
            "lastUpdate": "datetime",
        },
        limit=25000,  # Limit the table to 25,000 records to prevent overflow
        name="data_source_one",
    )

    # Update the table with new data every 50 milliseconds
    def updater():
        table.update(data_source())

    callback = tornado.ioloop.PeriodicCallback(callback=updater, callback_time=50)
    callback.start()

# Configure Tornado web application and WebSocket handlers
def make_app(perspective_server):
    return tornado.web.Application(
        [
            (
                r"/websocket",
                perspective.handlers.tornado.PerspectiveTornadoHandler,
                {"perspective_server": perspective_server},
            ),
            (
                r"/node_modules/(.*)",
                tornado.web.StaticFileHandler,
                {"path": "../../node_modules/"},
            ),
            (
                r"/(.*)",
                tornado.web.StaticFileHandler,
                {"path": "./", "default_filename": "index.html"},
            ),
        ]
    )

if __name__ == "__main__":
    perspective_server = perspective.Server()
    app = make_app(perspective_server)
    app.listen(8080)
    logging.critical("Listening on http://localhost:8080")
    loop = tornado.ioloop.IOLoop.current()
    loop.call_later(0, perspective_thread, perspective_server)
    loop.start()
