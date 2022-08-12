#!/bin/bash

pip3 install influxdb influxdb-client board 
sudo apt-get install pijuice-gui

#DO THIS IN THE BIRDHOUSE DIRECTORY
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.71.tar.gz
#Whatever the name of it is, extract it and move into the dir
tar zxvf bcm2835-1.71.tar.gz
cd bcm2835-1.71
./configure
make
sudo make check # to verify if it's all okay
sudo make install
cd ..
gcc getlight.c -o getlight -l bcm2835
