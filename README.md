# Birdhouse Instructions
### Don't worry, it's actually pretty easy.

Make sure to clone this repo to desktop!

1. When turning on the pi, as you know, make sure to have a monitor connected to it! If you turn the pi on without a microHDMI cable plugged in, it just won't output any image and it'll be pretty hard to do the rest of this.
2. Connect the Pi to the internet. The code pushes the data straight into influxDB-- no MQTT mumbo jumbo. It won't do anything otherwise. You should've received something to your student email regarding being added into the organization.
3. If not done already, install dependencies.
    `pip3 install adafruit-circuitpython-veml7700 influxdb influxdb-client board` 
5. Now we have to make this run on startup. Open the crontab file by doing the command `crontab -e`. If it's your first time using it, use selection 1 (nano is the easiest to work with)
6. Add this to the bottom `@reboot sleep 45; python3 /home/pi/Desktop/Birdhouse/call.py` Change the filepath to wherever you save it if not the desktop.
7. Press `ctrl+x` followed by `enter` followed by `enter`
8. Reboot! `sudo reboot`

That's pretty much it to be honest! It's as streamlined as it gets. I would have had it running automatically when you plug it in, but the internet connection is a bit tricky to do without the interface.

## *Happy sensing!*
