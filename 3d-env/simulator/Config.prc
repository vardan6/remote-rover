# Disable audio — WSL2 has no audio hardware and this simulator uses none
audio-library-name null

# Disable evdev input device scanning — /dev/input doesn't exist in WSL2
# (keyboard input still works via X11)
evdev-no-udev 1
want-directtools 0
