import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
from typing import Dict, Optional, List
import json

class SensorManager:
    """
    Manages sensors for the rover:
    - DHT11 (temperature & humidity)
    - IR sensors (4 directions)
    """
    
    def __init__(self, config: Dict):
        """
        Initialize all sensors
        
        Args:
            config: Dictionary with sensor configurations
                {
                    'dht_pin': board.D4,
                    'ir_pins': {'front': 17, 'back': 27, 'left': 22, 'right': 23}
                }
        """
        self.config = config

        # Initialize DHT11
        self.dht_device = None
        self.init_dht(config.get('dht_pin', board.D4))

        # Initialize IR sensors
        self.ir_pins = config.get('ir_pins', {})
        self.init_ir_sensors()
        print("✓ Sensor Manager Initialized")
    
    def init_dht(self, pin):
        """Initialize DHT11 sensor"""
        try:
            self.dht_device = adafruit_dht.DHT11(pin)
            print(f"✓ DHT11 initialized on pin {pin}")
        except Exception as e:
            print(f"✗ Failed to initialize DHT11: {e}")

    def init_ir_sensors(self):
        """Initialize IR obstacle sensors (digital output)"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for direction, pin in self.ir_pins.items():
            GPIO.setup(pin, GPIO.IN)
            print(f"✓ IR sensor ({direction}) initialized on GPIO {pin}")

    # ==================== DHT11 Functions ====================
    def read_temperature_humidity(self, retries=3) -> Optional[Dict]:
        """
        Read temperature and humidity from DHT11
        
        Args:
            retries: Number of retry attempts
            
        Returns:
            Dict with temperature (°C) and humidity (%) or None
        """
        if not self.dht_device:
            return None
        for attempt in range(retries):
            try:
                temperature = self.dht_device.temperature
                humidity = self.dht_device.humidity
                if temperature is not None and humidity is not None:
                    return {
                        'temperature_c': round(temperature, 2),
                        'temperature_f': round(temperature * 9/5 + 32, 2),
                        'humidity': round(humidity, 2),
                        'timestamp': time.time()
                    }
            except RuntimeError as e:
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    print(f"DHT11 read failed after {retries} attempts: {e}")
            except Exception as e:
                print(f"DHT11 error: {e}")
                break
        return None

    def get_temperature(self) -> Optional[float]:
        """Get only temperature in Celsius"""
        data = self.read_temperature_humidity()
        return data['temperature_c'] if data else None

    def get_humidity(self) -> Optional[float]:
        """Get only humidity percentage"""
        data = self.read_temperature_humidity()
        return data['humidity'] if data else None

    # ==================== IR Sensor Functions ====================
    def read_ir_sensor(self, direction: str) -> Optional[bool]:
        """
        Read single IR sensor
        Args:
            direction: 'front', 'back', 'left', or 'right'
        Returns:
            True if obstacle detected (LOW), False if clear (HIGH), None if error
        """
        if direction not in self.ir_pins:
            print(f"IR sensor '{direction}' not configured")
            return None
        try:
            sensor_value = GPIO.input(self.ir_pins[direction])
            return sensor_value == 0  # True = obstacle detected
        except Exception as e:
            print(f"IR sensor read error ({direction}): {e}")
            return None

    def read_all_ir_sensors(self) -> Dict[str, bool]:
        """
        Read all IR sensors
        Returns:
            Dict with obstacle status for each direction
        """
        ir_status = {}
        for direction in self.ir_pins.keys():
            obstacle = self.read_ir_sensor(direction)
            ir_status[direction] = obstacle if obstacle is not None else False
        return ir_status

    def get_clear_directions(self) -> List[str]:
        """
        Get list of directions without obstacles
        Returns:
            List of clear directions
        """
        ir_status = self.read_all_ir_sensors()
        return [direction for direction, has_obstacle in ir_status.items() if not has_obstacle]

    # ==================== Combined Reading ====================
    def get_all_sensor_data(self) -> Dict:
        """
        Get readings from all sensors at once
        Returns:
            Dictionary with all sensor data
        """
        return {
            'environment': self.read_temperature_humidity(),
            'obstacles': self.read_all_ir_sensors(),
            'timestamp': time.time()
        }

    def get_dashboard_data(self) -> Dict:
        """
        Get formatted data for dashboard display
        Returns:
            Formatted sensor data
        """
        env = self.read_temperature_humidity()
        ir = self.read_all_ir_sensors()
        return {
            'temperature': env['temperature_c'] if env else None,
            'humidity': env['humidity'] if env else None,
            'obstacles_front': ir.get('front', False),
            'obstacles_back': ir.get('back', False),
            'obstacles_left': ir.get('left', False),
            'obstacles_right': ir.get('right', False),
            'clear_directions': self.get_clear_directions(),
            'timestamp': time.time()
        }

    def save_to_file(self, filename='sensor_data.json'):
        """Save current sensor readings to JSON file"""
        data = self.get_all_sensor_data()
        try:
            with open(filename, 'a') as f:
                f.write(json.dumps(data) + '\n')
            return True
        except Exception as e:
            print(f"Failed to save data: {e}")
            return False

    def cleanup(self):
        """Clean up GPIO and sensor resources"""
        if self.dht_device:
            self.dht_device.exit()
        GPIO.cleanup()
        print("✓ Sensor resources cleaned up")


# ==================== Example Usage ====================
if __name__ == "__main__":
    # Configuration
    config = {
        'dht_pin': board.D4,  # GPIO4 for DHT11
        'ir_pins': {
            'front': 17,   # GPIO17
            'back': 27,    # GPIO27
            'left': 22,    # GPIO22
            'right': 23    # GPIO23
        }
    }
    sensors = SensorManager(config)
    try:
        print("\n" + "="*60)
        print("ROVER SENSOR TEST")
        print("="*60 + "\n")
        while True:
            # Read all sensors
            data = sensors.get_dashboard_data()
            print(f"\n{'─'*60}")
            print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'─'*60}")
            print(f"🌡️  Temperature: {data['temperature']}°C")
            print(f"💧 Humidity: {data['humidity']}%")
            print(f"\n🚧 Obstacles:")
            print(f"   Front:  {'⚠️  DETECTED' if data['obstacles_front'] else '✓ Clear'}")
            print(f"   Back:   {'⚠️  DETECTED' if data['obstacles_back'] else '✓ Clear'}")
            print(f"   Left:   {'⚠️  DETECTED' if data['obstacles_left'] else '✓ Clear'}")
            print(f"   Right:  {'⚠️  DETECTED' if data['obstacles_right'] else '✓ Clear'}")
            print(f"\n✅ Clear directions: {', '.join(data['clear_directions'])}")
            time.sleep(2)  # Read every 2 seconds
    except KeyboardInterrupt:
        print("\n\nStopping sensor readings...")
    finally:
        sensors.cleanup()
