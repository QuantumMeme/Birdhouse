# Birdhouse Instructions
### Don't worry, it's actually pretty easy.

1. When turning on the pi, as you know, make sure to have a monitor connected to it! If you turn the pi on without a microHDMI cable plugged in, it just won't output any image and it'll be pretty hard to do the rest of this.
2. Connect the Pi to the internet. The code pushes the data straight into influxDB-- no MQTT mumbo jumbo. It won't do anything otherwise. You should've received something to your student email regarding being added into the organization.
3. If not done already, install dependencies. `pip3 install adafruit-circuitpython-veml7700 influxdb influxdb-client paho-mqtt` 
4. Run **call.py** from the desktop. You can do it in the terminal or you can open the Thonny python editor and do it from there, it doesn't really matter. You don't need sudo privileges either.

That's pretty much it to be honest! It's as streamlined as it gets. I would have had it running automatically when you plug it in, but the internet connection is a bit tricky to do without the interface.

## *Happy sensing!*
