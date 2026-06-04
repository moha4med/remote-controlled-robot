from app import create_app
from app.extensions import socketio
from app.services.sensor_stream import sensor_loop

app = create_app()

if __name__ == "__main__":
    socketio.start_background_task(sensor_loop)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
