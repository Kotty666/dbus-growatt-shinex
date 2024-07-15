#!/usr/bin/env python

# import normal packages
import platform
import logging
import logging.handlers
import sys
import os
import sys
import json
if sys.version_info.major == 2:
    import gobject
else:
    from gi.repository import GLib as gobject
import sys
import time
import requests # for http GET
import configparser # for config/ini file

# our own packages from victron
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService


class DbusGrowattShineXService:
  def __init__(self, servicename, paths, productname='Growatt ShineX', connection='Growatt ShineX HTTP Json Connection'):
    config = self._getConfig()
    deviceinstance = int(config['DEFAULT']['Deviceinstance'])
    customname = config['DEFAULT']['CustomName']

    self._dbusservice = VeDbusService("{}.http_{:02d}".format(servicename, deviceinstance))
    self._paths = paths

    logging.info("%s /DeviceInstance = %d" % (servicename, deviceinstance))

    # Create the management objects, as specified in the ccgx dbus-api document
    self._dbusservice.add_path('/Mgmt/ProcessName', __file__)
    self._dbusservice.add_path('/Mgmt/ProcessVersion', 'Unkown version, and running on Python ' + platform.python_version())
    self._dbusservice.add_path('/Mgmt/Connection', connection)

    # Create the mandatory objects
    self._dbusservice.add_path('/DeviceInstance', deviceinstance)
    self._dbusservice.add_path('/ProductId', 0xFFFF) # id needs to be assigned by Victron Support current value for testing
    self._dbusservice.add_path('/ProductName', productname)
    self._dbusservice.add_path('/CustomName', customname)
    self._dbusservice.add_path('/Latency', None)
    self._dbusservice.add_path('/FirmwareVersion', 0.2)
    self._dbusservice.add_path('/HardwareVersion', 0)
    self._dbusservice.add_path('/Connected', 1)
    self._dbusservice.add_path('/Role', 'pvinverter')
    self._dbusservice.add_path('/Position', int(config['DEFAULT']['Position'])) # normaly only needed for pvinverter
    self._dbusservice.add_path('/Serial', self._getShineXSerial())
    self._dbusservice.add_path('/UpdateIndex', 0)
    self._dbusservice.add_path('/StatusCode', 7)

    # add path values to dbus
    for path, settings in self._paths.items():
      self._dbusservice.add_path(
        path, settings['initial'], gettextcallback=settings['textformat'], writeable=True, onchangecallback=self._handlechangedvalue)

    # last update
    self._lastUpdate = 0

    # add _update function 'timer'
    gobject.timeout_add(2000, self._update) # pause 1000ms before the next request

    # add _signOfLife 'timer' to get feedback in log every 5minutes
    gobject.timeout_add(self._getSignOfLifeInterval()*60*1000, self._signOfLife)

  def _getShineXSerial(self):
    meter_data = self._getShineXData()
    try:
      serial = meter_data['Mac']
    except:
      serial = '00:00:00:00:00:00'
    return serial.replace(':','')


  def _getConfig(self):
    config = configparser.ConfigParser()
    config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))
    return config;


  def _getSignOfLifeInterval(self):
    config = self._getConfig()
    value = config['DEFAULT']['SignOfLifeLog']

    if not value:
        value = 0

    return int(value)


  def _getShineXStatusUrl(self):
    config = self._getConfig()
    accessType = config['DEFAULT']['AccessType']

    if accessType == 'OnPremise':
        URL = "http://%s:%s@%s/status" % (config['ONPREMISE']['Username'], config['ONPREMISE']['Password'], config['ONPREMISE']['Host'])
        URL = URL.replace(":@", "")
    else:
        raise ValueError("AccessType %s is not supported" % (config['DEFAULT']['AccessType']))

    return URL


  def _getShineXData(self):
    URL = self._getShineXStatusUrl()
    headers={}
    headers['Content-Type'] = 'application/json'

    meter_data = {"InverterStatus":0}

    try:
      meter_r = requests.get(url = URL, timeout=10,headers=headers)
      if ( meter_r.status_code == 200 and meter_r.headers.get('Content-Type').startswith('text/html')):
        REBOOT_URL = URL.replace('/status','/restart')
        resp = requests.get(url = REBOOT_URL, timeout = 10)
        logging.info("Reboot triggered")
    except requests.exceptions.Timeout:
      logging.info("RequestTimeout")
    except requests.exceptions.TooManyRedirects:
      print("Too Many Redirects")
    except requests.exceptions.RequestException as e:
      logging.info("No response from Shine X - %s" % (URL))
      print(e)
    except:
      logging.info("No response from Shine X - %s" % (URL))

    try:
      meter_data = meter_r.json()
    except:
        logging.info("Got no Json. meter_data set to: %s" % (meter_data))

    return meter_data


  def _signOfLife(self):
    logging.info("--- Start: sign of life ---")
    logging.info("Last _update() call: %s" % (self._lastUpdate))
    logging.info("Last '/Ac/Power': %s" % (self._dbusservice['/Ac/Power']))
    logging.info("Last '/Ac/Energy/Forward': %s" % (self._dbusservice['/Ac/Energy/Forward']))
    logging.info("--- End: sign of life ---")
    return True

  def _update(self):
    try:
      config = self._getConfig()
      LocalPhase = config['DEFAULT']['Phase']
      allPhase = ['L1','L2','L3']
      nuPhase = list(set(allPhase) - set(LocalPhase))
      #get data from Shine X
      cosphi = 1

      #send data to DBus
      meter_data = self._getShineXData()
      if meter_data is False:
        logging.info("Did not got valid Json.")
        return True

      self._dbusservice['/Connected'] = meter_data['InverterStatus']
      if meter_data['InverterStatus'] == 0:
        PhaseList = ['L1','L2','L3']
        for Phase in PhaseList:
          dbCur = '/Ac/{}/Current'.format(Phase)
          dbPow = '/Ac/{}/Power'.format(Phase)
          dbVol = '/Ac/{}/Voltage'.format(Phase)
          mCur = '{}ThreePhaseGridOutputCurrent'.format(Phase)
          mPow = '{}ThreePhaseGridOutputPower'.format(Phase)
          mVol = '{}ThreePhaseGridVoltage'.format(Phase)

          self._dbusservice[dbCur] = 0
          self._dbusservice[dbPow] = 0
          self._dbusservice[dbVol] = 0

        self._dbusservice['/Ac/Power'] = 0
        return True


      if meter_data['PV1InputPower'] == 0 and meter_data['PV1InputPower'] == 0 and meter_data['PV2InputPower'] == 0 and meter_data['PV2InputPower'] == 0:
        self._dbusservice['/Ac/Energy/Forward'] = meter_data['TotalGenerateEnergy']
        self._dbusservice['/Ac/Power'] = 0
        return True

      if meter_data['L3ThreePhaseGridOutputPower'] > 0:
        PhaseList = allPhase
        for Phase in PhaseList:
          dbsname = '/Ac/{}/Energy/Forward'.format(Phase)
          self._dbusservice[dbsname] = ( meter_data['TotalGenerateEnergy'] / 3 )
        if meter_data['L1ThreePhaseGridOutputCurrent'] <= 0.5 and meter_data['L2ThreePhaseGridOutputCurrent'] <= 0.5 and meter_data['L2ThreePhaseGridOutputCurrent'] <= 0.5:
          meter_data['OutputPower'] = 0
      else:
        PhaseList = [LocalPhase]
        ef = '/Ac/{}/Energy/Forward'.format(LocalPhase)
        self._dbusservice[ef] = meter_data['TotalGenerateEnergy']
        if meter_data['L1ThreePhaseGridOutputCurrent'] <= 0.5:
            meter_data['OutputPower'] = 0

      LAll = meter_data['L1ThreePhaseGridOutputPower'] + meter_data['L2ThreePhaseGridOutputPower'] + meter_data['L3ThreePhaseGridOutputPower']
      Pct1 = 100 / LAll
      Pct2 = Pct1 * meter_data['OutputPower']
      cosphi = Pct2 / 100
      if meter_data['OutputPower'] > 0:
        self._dbusservice['/Ac/Energy/Forward'] = meter_data['TotalGenerateEnergy']
        self._dbusservice['/Ac/Power'] = meter_data['OutputPower']

        for Phase in PhaseList:
          if len(PhaseList) == 1:
            LPhase = 'L1'
          else:
            LPhase = Phase
          dbCur = '/Ac/{}/Current'.format(Phase)
          dbPow = '/Ac/{}/Power'.format(Phase)
          dbVol = '/Ac/{}/Voltage'.format(Phase)

          mCur = '{}ThreePhaseGridOutputCurrent'.format(LPhase)
          mPow = '{}ThreePhaseGridOutputPower'.format(LPhase)
          mVol = '{}ThreePhaseGridVoltage'.format(LPhase)

          if meter_data[mCur] <= 0.5:
            meter_data[mCur] = (meter_data['OutputPower'] / len(PhaseList))/meter_data[mVol]
            self._dbusservice[dbPow] = meter_data['TotalGenerateEnergy'] / len(PhaseList)
          else:
            self._dbusservice[dbPow] = meter_data[mPow] * cosphi
          self._dbusservice[dbCur] = meter_data[mCur]
          self._dbusservice[dbVol] = meter_data[mVol]

      #logging
      logging.info("House Consumption (/Ac/Power): %s" % (self._dbusservice['/Ac/Power']))
      logging.info("House Forward (/Ac/Energy/Forward): %s" % (self._dbusservice['/Ac/Energy/Forward']))
      logging.info("---");

      self._dbusservice['/UpdateIndex'] = (self._dbusservice['/UpdateIndex'] + 1 ) % 256
      self._lastUpdate = time.time()
    except Exception as e:
      logging.critical('Error at %s', '_update', exc_info=e)

    # return true, otherwise add_timeout will be removed from GObject - see docs http://library.isr.ist.utl.pt/docs/pygtk2reference/gobject-functions.html#function-gobject--timeout-add
    return True

  def _handlechangedvalue(self, path, value):
    logging.info("someone else updated %s to %s" % (path, value))
    return True # accept the change



def main():
  #configure logging
  logging_level = "ERROR"
  logging.basicConfig(format="%(levelname)s %(message)s",level=logging_level,)
  try:
      logging.info("Start");
      from dbus.mainloop.glib import DBusGMainLoop
      # Have a mainloop, so we can send/receive asynchronous calls to and from dbus
      DBusGMainLoop(set_as_default=True)

      config = configparser.ConfigParser()
      config.read("%s/config.ini" % (os.path.dirname(os.path.realpath(__file__))))

      #formatting
      _kwh = lambda p, v: (str(round(v, 2)) + 'KWh')
      _a = lambda p, v: (str(round(v, 1)) + 'A')
      _w = lambda p, v: (str(round(v, 1)) + 'W')
      _v = lambda p, v: (str(round(v, 1)) + 'V')

      #start our main-service
      pvac_output = DbusGrowattShineXService(
        servicename='com.victronenergy.pvinverter',
        paths={
            '/ErrorCode': {'initial': None, 'textformat': '' },
            '/Ac/Energy/Forward': {'initial': None, 'textformat': _kwh},
            '/Ac/Power': {'initial': None, 'textformat': _w},

            '/Ac/L1/Current': {'initial': None, 'textformat': _a},
            '/Ac/L1/Power': {'initial': None, 'textformat': _w},
            '/Ac/L1/Voltage': {'initial': None, 'textformat': _v},
            '/Ac/L1/Energy/Forward': {'initial': None, 'textformat': _kwh},

            '/Ac/L2/Current': {'initial': None, 'textformat': _a},
            '/Ac/L2/Power': {'initial': None, 'textformat': _w},
            '/Ac/L2/Voltage': {'initial': None, 'textformat': _v},
            '/Ac/L2/Energy/Forward': {'initial': None, 'textformat': _kwh},

            '/Ac/L3/Current': {'initial': None, 'textformat': _a},
            '/Ac/L3/Power': {'initial': None, 'textformat': _w},
            '/Ac/L3/Voltage': {'initial': None, 'textformat': _v},
            '/Ac/L3/Energy/Forward': {'initial': None, 'textformat': _kwh},
        })

      logging.info('Connected to dbus, and switching over to gobject.MainLoop() (= event based)')
      mainloop = gobject.MainLoop()
      mainloop.run()
  except Exception as e:
    logging.critical('Error at %s', 'main', exc_info=e)


if __name__ == "__main__":
  main()
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab:
