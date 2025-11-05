import time
import json
import board
from datetime import datetime
from typing import Dict, Optional

# Import your real sensor, motor, and camera modules
from sensor_manager import SensorManager
# from motor_controller import MotorController
# from obstacle_detector import RoverMultiCameraDetector

class RoverMainControl:
    """
    Main control system that integrates:
    - IR sensors
    - Motor control
    - Environmental sensors (DHT11)
    - Data logging
    """
    def __init__(self):
        print("\n" + "="*70)
        print(" " * 20 + "SPACE ROVER INITIALIZATION")
        print("="*70 + "\n")
        
        # Configuration
        self.config = self.load_config()
        
        # Initialize sensors
        print("→ Initializing sensors...")
        sensor_config = {
            'dht_pin': board.D4,
            'ir_pins': {
                'front': 17,
                'back': 27,
                'left': 22,
                'right': 23
            }
        }
        self.sensors = SensorManager(sensor_config)
        
        # Uncomment/init other modules as needed
        # print("\n→ Initializing motors...")
        # motor_config = {...}
        # self.motors = MotorController(motor_config)
        
        # print("\n→ Initializing cameras...")
        # camera_config = {...}
        # self.camera_detector = RoverMultiCameraDetector(camera_config)
        
        self.ir_priority_distance = 20  # cm, IR sensor trigger distance
        self.study_interval = 30  # seconds between soil studies
        self.last_study_time = 0
        self.movement_speed = 50  # Default speed (0-100)
        
        self.position = {'x': 0.0, 'y': 0.0, 'heading': 0.0}
        self.distance_per_second = 0.15
        
        self.data_log = []
        self.log_file = 'rover_data_log.json'
        
        print("\n" + "="*70)
        print(" " * 25 + "✓ ROVER READY")
        print("="*70 + "\n")

    def load_config(self) -> Dict:
        default_config = {
            'auto_study_enabled': True,
            'study_interval': 30,
            'default_speed': 50,
            'ir_priority': True,
            'log_to_file': True
        }
        try:
            with open('rover_config.json', 'r') as f:
                config = json.load(f)
                return {**default_config, **config}
        except FileNotFoundError:
            return default_config

    # ==================== Position Tracking ====================
    def update_position(self, direction: str, duration: float):
        import math
        distance = self.distance_per_second * duration
        if direction == 'forward':
            self.position['x'] += distance * math.cos(math.radians(self.position['heading']))
            self.position['y'] += distance * math.sin(math.radians(self.position['heading']))
        elif direction == 'backward':
            self.position['x'] -= distance * math.cos(math.radians(self.position['heading']))
            self.position['y'] -= distance * math.sin(math.radians(self.position['heading']))
        elif direction == 'left':
            self.position['heading'] = (self.position['heading'] + 45) % 360
        elif direction == 'right':
            self.position['heading'] = (self.position['heading'] - 45) % 360
        elif direction == 'spin_left':
            self.position['heading'] = (self.position['heading'] + 90) % 360
        elif direction == 'spin_right':
            self.position['heading'] = (self.position['heading'] - 90) % 360

    def get_position(self) -> Dict:
        return {
            'x': round(self.position['x'], 2),
            'y': round(self.position['y'], 2),
            'heading': round(self.position['heading'], 1)
        }

    # ==================== Data Logging ====================
    def log_data(self, sensor_data: Dict, action: str, position: Dict):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'position': position,
            'temperature': sensor_data.get('temperature'),
            'humidity': sensor_data.get('humidity'),
            'obstacles': sensor_data.get('obstacles', {}),
            'action': action
        }
        self.data_log.append(log_entry)
        if len(self.data_log) % 10 == 0:
            self.save_log_to_file()

    def save_log_to_file(self):
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.data_log, f, indent=2)
            print(f"✓ Data saved ({len(self.data_log)} entries)")
        except Exception as e:
            print(f"✗ Failed to save data: {e}")

    # ==================== Study Mode ====================
    def should_study_location(self) -> bool:
        current_time = time.time()
        if self.config['auto_study_enabled']:
            if current_time - self.last_study_time >= self.study_interval:
                return True
        return False

    def study_location(self):
        print("\n" + "🔬"*35)
        print(" " * 20 + "STUDYING LOCATION")
        print("🔬"*35)
        
        position = self.get_position()
        print(f"\n📍 Position: ({position['x']}, {position['y']}) | Heading: {position['heading']}°")
        print("\n📊 Taking readings...")

        readings = []
        for i in range(3):
            sensor_data = self.sensors.get_dashboard_data()
            readings.append(sensor_data)
            time.sleep(1)

        avg_temp = sum(r['temperature'] for r in readings if r['temperature'] is not None) / 3
        avg_humidity = sum(r['humidity'] for r in readings if r['humidity'] is not None) / 3

        print(f"\n🌡️  Temperature: {round(avg_temp, 2)}°C")
        print(f"💧 Humidity: {round(avg_humidity, 2)}%")

        avg_data = {
            'temperature': round(avg_temp, 2),
            'humidity': round(avg_humidity, 2),
            'obstacles': self.sensors.read_all_ir_sensors()
        }

        self.log_data(avg_data, "STUDY_LOCATION", position)
        self.last_study_time = time.time()

        print("\n✓ Study complete!")
        print("🔬"*35 + "\n")
        time.sleep(2)

    # ==================== Main Control Loop ====================
    def make_navigation_decision(self) -> Dict:
        ir_status = self.sensors.read_all_ir_sensors()
        # camera_decision = self.camera_detector.get_best_direction()
        camera_decision = {'recommended_direction': 'front', 'should_move': True}

        if ir_status.get('front', False):
            return {'action': 'stop',
                    'reason': 'Front IR sensor triggered - obstacle too close!',
                    'direction': None,
                    'duration': 0}

        recommended_dir = camera_decision.get('recommended_direction', 'stop')

        if recommended_dir == 'front' and not ir_status.get('front', False):
            return {'action': 'forward', 'reason': 'Path clear ahead', 'direction': 'forward', 'duration': 2.0}
        elif recommended_dir == 'left' and not ir_status.get('left', False):
            return {'action': 'turn_left', 'reason': 'Camera suggests left turn', 'direction': 'left', 'duration': 0.5}
        elif recommended_dir == 'right' and not ir_status.get('right', False):
            return {'action': 'turn_right', 'reason': 'Camera suggests right turn', 'direction': 'right', 'duration': 0.5}
        elif recommended_dir == 'back' and not ir_status.get('back', False):
            return {'action': 'backward', 'reason': 'Reversing to find alternate path', 'direction': 'backward', 'duration': 1.0}
        else:
            return {'action': 'spin_right', 'reason': 'No clear path - rotating to scan area', 'direction': 'spin_right', 'duration': 0.8}

    def execute_action(self, decision: Dict):
        action = decision['action']
        duration = decision.get('duration', 0)
        print(f"🚀 {action.upper()}: {decision['reason']}")
        # Uncomment for motors
        # if action == 'forward':
        #     self.motors.move_forward(speed=self.movement_speed, duration=duration)
        # elif action == 'backward':
        #     self.motors.move_backward(speed=self.movement_speed, duration=duration)
        # elif action == 'turn_left':
        #     self.motors.turn_left(duration=duration)
        # elif action == 'turn_right':
        #     self.motors.turn_right(duration=duration)
        # elif action == 'spin_left':
        #     self.motors.spin_left(duration=duration)
        # elif action == 'spin_right':
        #     self.motors.spin_right(duration=duration)
        # elif action == 'stop':
        #     self.motors.stop()

        if decision['direction']:
            self.update_position(decision['direction'], duration)
        position = self.get_position()
        sensor_data = self.sensors.get_dashboard_data()
        self.log_data(sensor_data, action, position)

    def run(self):
        print("\n" + "▶"*35)
        print(" " * 15 + "STARTING ROVER OPERATION")
        print("▶"*35 + "\n")
        print("Press Ctrl+C to stop\n")
        loop_count = 0
        try:
            while True:
                loop_count += 1
                print(f"\n{'─'*70}")
                print(f"Loop #{loop_count} | Time: {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'─'*70}")
                if self.should_study_location():
                    self.study_location()
                decision = self.make_navigation_decision()
                self.execute_action(decision)
                pos = self.get_position()
                print(f"📍 Position: ({pos['x']}, {pos['y']}) @ {pos['heading']}°")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n" + "⏹"*35)
            print(" " * 15 + "STOPPING ROVER")
            print("⏹"*35 + "\n")
            self.stop()

    def stop(self):
        print("→ Saving final data...")
        self.save_log_to_file()
        print("\n✓ Rover shutdown complete")
        print(f"Total data points collected: {len(self.data_log)}")
        print(f"Final position: {self.get_position()}")


# ==================== Standalone Execution ====================
if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║         🛸 SPACE ROVER CONTROL SYSTEM 🛸                           ║
    ║   ✓ IR sensor integration                                        ║
    ║   ✓ Autonomous navigation                                        ║
    ║   ✓ Environmental sensing (temp, humidity)                       ║
    ║   ✓ Position tracking                                            ║
    ║   ✓ Data logging                                                 ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)
    rover = RoverMainControl()
    rover.run()
