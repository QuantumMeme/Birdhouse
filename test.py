import unittest
from unittest import mock
import sys

from unittest.mock import MagicMock, patch

# MockRPi = MagicMock()
# modules = {
#     "RPi": MockRPi,
#     "RPi.GPIO": MockRPi.GPIO,
# }
# patcher = patch.dict("sys.modules", modules)
# patcher.start()

# mock imports
sys.modules['board'] = MagicMock()
sys.modules['adafruit_veml7700'] = MagicMock()
sys.modules['serial'] = MagicMock()
sys.modules['serial.SerialException'] = MagicMock()
sys.modules['influxdb_client'] = MagicMock()
sys.modules['influxdb_client.InfluxDBClient'] = MagicMock()
sys.modules['influxdb_client.Point'] = MagicMock()
sys.modules['influxdb_client.WritePrecision'] = MagicMock()
sys.modules['influxdb_client.client'] = MagicMock()
sys.modules['influxdb_client.client.write_api'] = MagicMock()
sys.modules['influxdb_client.client.write_api.SYNCHRONOUS'] = MagicMock()

sys.modules['RPi'] = MagicMock()
sys.modules['RPi.GPIO'] = MagicMock()

# import file to test after mocks
import call_refactor


class Testing(unittest.TestCase):

    def test_lux_setup(self):
        lux_sensor_bool_test = False
        # this should work with the mock
        lux_sensor, lux_sensor_bool = call_refactor.load_lux_sensor(lux_sensor_bool_test)
        self.assertTrue(lux_sensor, msg="lux_sensor false")
        self.assertTrue(lux_sensor_bool, msg="lux_sensor_bool false")

    def test_temp_setup(self):
        temp_sensor_bool_test = False
        # this should work with the mock
        temp_sensor_serial, temp_sensor_bool = call_refactor.load_temp_sensor(temp_sensor_bool_test, 'test')
        self.assertTrue(temp_sensor_serial, msg="temp_sensor_serial false")
        self.assertTrue(temp_sensor_bool, msg="temp_sensor_bool false")

    def test_connect_influxdb(self):
        write_api, connection_bool = call_refactor.connect_influxdb()
        self.assertTrue(connection_bool)

    @patch.object(load_sensor, 'load_lux_sensor')
    def test_collect_lux_data_sensor_false(self):
        # test when sensor needs to be reset
        write_api, lux_sensor_bool = 'test', False
        lux_sensor = Sensor()
        lux_sent_bool = call_refactor.collect_lux_data(lux_sensor, write_api, lux_sensor_bool)
        self.assertTrue(lux_sent_bool)

# Then for the actual test

# with patch("RPi.GPIO.output") as mock_gpio:

# Invoke the code to test GPIO
# mock_gpio.assert_called_with(....)
