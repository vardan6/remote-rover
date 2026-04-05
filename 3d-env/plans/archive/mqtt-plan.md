> Deprecated: superseded by `mqtt-plan-canonical-2026-04-05_00-58-36.md`.
> Kept for historical context only.


# MQTT Setup
## MQTT Clients
Now we should plan for MQTT client functionality of the 3d-env-simulator.
The rover should receive control commands and settings from MQTT broker.
The rover should publish his current state or whatever asked to the MQTT broker.

There will be one or more control stations which also will be connected to the same MQTT broker and should subscribe and publish messages to it.
The rover 3d model will subscribe to specified topics and publish and receive certain messages.

Rover model sends his current state to the MQTT broker, which includes:
 - Current position: GPS coordinates
 - Angle, orientation
 - Accelerometer: 3 axes and gyroscope 3 axes data
 - Altitude: Barometer sensor data
 - Current speed: m/s
 - Camera feed when enabled(default: yes)

Additionally rover sends this data:
 - Battery level: 67% (or 22.56V, 10A, 17°C) ?
 - Voltage: 22.56V
 - Current: 10A
 - Temperature: 17°C
> Please use constant values for the below parameters for now, we can make them dynamic later

## Control
???
Rover can receive control commands from MQTT broker, which includes:
 - Move forward: speed in m/s ? probably just that button press can be used to start moving and release to stop
 - Move backward: speed in m/s ?
 - Turn left: angle in degrees ?
 - Turn right: angle in degrees ?
 - Stop: no parameters ?
 - Camera toggle: on/off ?
> we need to define control commands and its mechanics, for example, if we want to have speed control, we can have a button press to start moving and release to stop, or we can have a button press to move for a certain distance or time, or we can have a button press to move at a certain speed until another command is received.

Questions do discuss and plan now:
> For now, we can start with simple button press to move and release to stop, and throttled forward backward and proportional left right control should be implemented and used optionally.
We need to plan the MQTT topics structure and message formats for both control commands and state updates. We can use JSON format for messages, and we can have a topic structure like:
 - /projects/remote-rover/control
 - /projects/remote-rover/state
 - /projects/remote-rover/camera-feed ?
This optional settings should be implemented in the Settings menu as well for example in Settings -> Controls.
The throttle and proportional controls allow RC transmitters and joystick support.
