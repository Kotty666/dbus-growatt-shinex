# dbus-growatt-shinex
Integrate Growatt-ShineWifi into Victron Energies Venus OS
 - https://github.com/OpenInverterGateway/OpenInverterGateway

## Purpose
With the scripts in this repo it should be easy possible to install, uninstall, restart a service that connects the Growatt Inverter to the VenusOS and GX devices from Victron.
Idea is inspired on @fabian-lauer & @vikt0rm projects linked below.



## Inspiration
This is my first project with the Victron Venus OS on GitHub, so I took some ideas and approaches from the following projects - many thanks for sharing the knowledge:
- https://github.com/fabian-lauer/dbus-shelly-3em-smartmeter
- https://github.com/vikt0rm/dbus-shelly-1pm-pvinverter
- https://github.com/victronenergy/venus/wiki/dbus#pv-inverters



------------------------------------ Update below needed ----------------------------------------------------

## How it works
### My setup
- Growatt ShineWifi-X
  - Measuring AC output of Growatt MIC 600TL-X on phase L1
  - Connected to Wifi netowrk "A" with a known IP
- Venus OS on Raspberry PI 3B - Firmware v2.89
  - No other devices from Victron connected
  - Connected to Wifi netowrk "A"

### Details / Process
As mentioned above the script is inspired by @fabian-lauer dbus-shelly-3em-smartmeter implementation.
So what is the script doing:
- Running as a service
- connecting to DBus of the Venus OS `com.victronenergy.pvinverter.http_{DeviceInstanceID_from_config}`
- After successful DBus connection the Growatt Inverter WifiDongle is accessed via REST-API - simply the /status is called and a JSON is returned with all details
- Paths are added to the DBus with default value 0 - including some settings like name, etc
- After that a "loop" is started which pulls data every 750ms from the REST-API and updates the values in the DBus

Thats it 😄

### Pictures
![Tile Overview](img/OverView.JPG)
![Device List - Overview](img/DeviceList.JPG) 
![Growatt - Values](img/Growatt_Detail.JPG)
![Growatt - Device Details](img/Device_Detail.JPG)


## Install & Configuration
### Get the code
Just grap a copy of the main branche and copy them to a folder under `/data/` e.g. `/data/dbus-growatt-shinex`.
After that call the install.sh script.

The following script should do everything for you:
```
wget https://github.com/Kotty666/dbus-growatt-shinex/archive/refs/heads/main.zip
unzip main.zip "dbus-growatt-shinex-main/*" -d /data
mv /data/dbus-growatt-shinex-main /data/dbus-growatt-shinex
chmod a+x /data/dbus-growatt-shinex/install.sh
/data/dbus-growatt-shinex/install.sh
rm main.zip
```
⚠️ Check configuration after that - because service is already installed an running and with wrong connection data (host, username, pwd) you will spam the log-file

### Change config.ini
Within the project there is a file `/data/dbus-growatt-shinex/config.ini` - just change the values - most important is the deviceinstance, custom name and phase under "DEFAULT" and host, username and password in section "ONPREMISE". More details below:

| Section  | Config vlaue | Explanation |
| ------------- | ------------- | ------------- |
| DEFAULT  | AccessType | Fixed value 'OnPremise' |
| DEFAULT  | SignOfLifeLog  | Time in minutes how often a status is added to the log-file `current.log` with log-level INFO |
| DEFAULT  | Deviceinstance | Unique ID identifying the shelly 1pm in Venus OS |
| DEFAULT  | CustomName | Name shown in Remote Console (e.g. name of pv inverter) |
| DEFAULT  | Phase | Valid values L1, L2 or L3: represents the phase where pv inverter is feeding in |
| ONPREMISE  | Host | IP or hostname of on-premise Shelly 3EM web-interface |
| ONPREMISE  | Username | Username for htaccess login - leave blank if no username/password required |
| ONPREMISE  | Password | Password for htaccess login - leave blank if no username/password required |



## Used documentation
- https://github.com/victronenergy/venus/wiki/dbus#pv-inverters   DBus paths for Victron namespace
- https://github.com/victronenergy/venus/wiki/dbus-api   DBus API from Victron
- https://www.victronenergy.com/live/ccgx:root_access   How to get root access on GX device/Venus OS

## Discussions on the web

