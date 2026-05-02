Please read all the text below, correct it: spelling and grammar. If really necessary drop onto paragraphs and structure (if really necessary )or  it or change paragraph order. Merge or combine repeating ideas if needed:

What is the best platform to model 3D objects, particularly I need to create a virtual environment for off-road car. I want to have some kind of model which will move forward, backward, turn left and right as the rover can do. Maybe flat surface or 2D model is good enough, but it's preferable to have 3D. I would prefer to have some environment already built with lots of flat surface, so I can use it for testing. If the environment already has some physics, that is even better. That is actually very desired, but if this is very difficult, we can consider it. But I would like to consider these both options. I would like to have with 3D physics. So I would like to have 3D environment with physics and rover car on it. I will send commands to car via keyboard signals like in game. Mostly we can say it's part of a game, but it is a simulator to simulate and design and develop a web server which should connect the actual rover, but I want to do my development in the virtual environment so far. What platforms are best? I am going to do it with Vibe coding using CloudCode, cloud code, preferably with Python. I also highly may consider it having a web interface to be able to access it via web server, this GUI environment.

So again, please conclude, I want to write it by Python, I want to have it in the web interface, I want it to be as simple as possible.

I want to develop this in the cloud code CLI using VS Code, and I want it to be able to drive the rover via the arrow keys on the keyboard. And from the settings, I should be able to choose to connect it via MQTT protocol. I need this MQTT protocol template, so it will subscribe to some broker. Each key will have its topic and the topic will receive some values. Some values will be published in the broker. Your subscription of this simulator will receive these published token values and will act the rover accordingly. It should have four or more tokens. The token addresses I will list. Please make a Cloud Code prompt so I can launch it in the Cloud Code CLI and it will make this project. Thank you. Please make sure you include all the details I mentioned to you. Also, please make a markdown file, create a Rover3DEnva.md markdown file so I can download it. Thank you.

Now, please add the functionality that accepts MQTT. It must connect via REST API to a dedicated server. This server should be implemented separately, but please think about what this server should look like and how the rover should be connected to the server. Another device will be connected to this same server, which will receive commands from a remote control or a ground command station. So, ground command station will connect to server, rover will connect to server. So far, rover will be the virtual one, but later it will be replaced with actual real rover. So, server should receive, for example, forward, backward, left, right, and other control commands, remote control commands, and send to the rover as fast as possible. Please think about what protocols to use for the lowest latency, lowest delay, lowest ping, or lowest communication latency from the remote control to server to rover.

Accept simple control commands. It can have also some messages for updating configuration or other commands for internal settings change. This will be designed later. I need to have a room later to implement anything which is possibly probable to be able to configure the rover remotely or update its configuration remotely. Many other control commands also may be possible, but so far we concentrate on the moving, moving, but with high potential to later include any command transmission to the rover via the server. The transmission may be done via MQTT, for example, for example, JSON structures, JSON messages. Please consider this information building the server. Also, rover should be able to pass back information from it to the ground control station via the same server, including video signals. Robot should be able to connect to the server via. And from the web interface on the server, we should be able to see robot current state, which may be transmitted to the server, for example, its geometric position, its angle, altitude, and physical orientation. All those signals will be received on the rover and will be passed to the server. So server will show the robot current state. This may be done not so fast, but at least once a second. This is also important if you can retrieve this data from the 3D model and organize design sending this data to the server, to the same server, that is even better. It must not be the same server, but possibly please suggest one server being able to reside all this functionality.


Please read and understand the project we are going to work on next steps planning details.
We are going to work on the ground station(GS) implementation know.
It is going to be web application.
What technology stack should we use for it ? I would prefer to have it in Python, but if you think that other technology stack is better, please suggest.
It should be web application, so it can be accessed from anywhere.
It should have a dashboard to show the current state of the rover, which will be transmitted from the rover to possibly this `server`.
Most probably this would be the server with real IP where any clinet opened it by Browser can became ground control station.

So, it should have a control panel with buttons for forward, backward, left, right, (ASDW) and other commands.
It should also have a video feed from the rover's camera. The video feed can be implemented later, but it is important to plan for it now. The communication between the ground station and the server should be done via MQTT protocol for low latency. The ground station will subscribe to certain topics to receive updates from the rover and will publish commands to certain topics to control the rover. Please plan for this functionality in the ground station implementation.

It can run on a PC or on a server with real AP.
It should have so far MQTT client.
We should connect to the same MQTT broker and receive whatever rover is sending.
GUI should have control keyboard bindings to current open machine so it can be driven manually from GS. using the Rover 3D environment with camera feet/stream and OSD.
There should be control arrow buttons on the screen so when one press control buttons it is indicated on the screen buttons.
Of course corresponding messages should be sent to corresponding topics when press buttons to drive the rover.

Please in this pass implement also video feed via the MQTT server/broker. let's do it let's plan for it. 
Please make it optional so later can most probably will enhance it using UDP protocol for example, but now let's do it via MQTT broker, so we can have it working and we can see the video feed from the rover's camera in the ground station web interface. We can have a separate topic for the video feed, for example, */camera-feed, and the rover will publish the video frames to this topic, or what is the best approach ?
And the ground station will subscribe to this topic and display the video feed in the web interface ?
Please plan for this functionality in the ground station and 3d model backend and settings implementation as well.
Make this in the settings optional as well so we can choose current streaming version over the MQTT broker later we can add whatever it is, possibly UDP stream ?
I want to see either OSD or separate posting for the status info, all the physical and electrical status data.
WRT: I want to see the broker status:
 - if it will "ping" and disturb connection every second or regularly I don't want it. It seems should be possible to cleverly get the connection status or it is natively provided, because for example when I used other MQTT dashboards including i. e. mobile applications they show the status of MQTT broker I was thinking it is a simple thing but I don't know if it's simple or not. But spending any resources for that mostly not acceptable, I donr want to spend any regular sent  message  just getting status, either get the connection status in intended clever way or drop this idea.
 - We need a plan for camera feed/stream via the MQTT broker Let's discuss and plan it.


Pleased do the following
1. Rename the GS to GCS (Ground Control Station) to better reflect its purpose.
2. Research for better solutions for:
    > 5. Video transport is abstracted behind a backend VideoProvider interface:
    >    - mqtt
    >    - webrtc
    >    - udp
    >    - disabled
3. Research for better solutions for:
    > 2. GS(GCS) backend skeleton
    >   - New module, e.g. gs_backend/
    >   - FastAPI app
    >   - MQTT service
    >   - WebSocket hub
    >   - in-memory state store for latest telemetry, broker state, controller session, video mode