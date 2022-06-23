# Birdhouse Instructions
### Don't worry, it's actually pretty easy.

Make sure to clone this repo to desktop!

1. When turning on the pi, as you know, make sure to have a monitor connected to it! If you turn the pi on without a microHDMI cable plugged in, it just won't output any image and it'll be pretty hard to do the rest of this.
2. Connect the Pi to the internet. The code pushes the data straight into influxDB-- no MQTT mumbo jumbo. It won't do anything otherwise. You should've received something to your student email regarding being added into the organization.
3. If not done already, install dependencies.
    `pip3 install adafruit-circuitpython-veml7700 influxdb influxdb-client`
4. In order to make sure that we stay connected to the internet, we will create a little script to ensure that for us. Let's created it with the following command:
    `sudo nano /usr/local/bin/wificheck.sh`
5. Add the following code and save it with `ctrl+x` followed by `enter` and `enter`
    `#!/bin/bash

    # Pinging the Cloudflare DNS to check if there's internet
    GATEWAY=1.1.1.1

    # Send two pings, with the output going to /dev/null
    ping -c2 ${GATEWAY} > /dev/null

    # Check to see if the returned value from ping ($?)
    # is not 0 and then act to restart wlan1 if necessary
    if [ $? == 0 ]
    then
        # Restart wlan1 (the wireless interface)
        ifconfig wlan1 down
        ifconfig wlan1 up
    fi`
6. Then we need to make it executable with the following:
    `sudo chmod +x /usr/local/bin/wificheck.sh`
7. Now we have to make both of these run on startup. Open the crontab file by doing the command `crontab -e`. If it's your first time using it, use selection 1 (nano is the easiest to work with)
8. Add the following lines to the bottom. The first runs the sensing program on boot, the second checks for internet connection every 5 minutes.
    `@reboot sleep 45; python3 /home/pi/Desktop/Birdhouse/call.py`
    `*/5 * * * * /usr/bin/sudo -H /usr/local/bin/wificheck.sh >> /dev/null 2>&1`
9. Press `ctrl+x` followed by `enter` followed by `enter`
10. Reboot! `sudo reboot`

That's pretty much it to be honest! It's as streamlined as it gets. I would have had it running automatically when you plug it in, but the initial internet connection is a bit tricky to do without the interface.

## *Happy sensing!*
