import time
import json
import board
from datetime import datetime
from typing import Dict, Optional

# Import custom modules (assuming they're in the same directory)
# from sensor_manager import SensorManager
# from motor_controller import MotorController
# from obstacle_detector import RoverMultiCameraDetector

class RoverMainControl:
    """
    Main control system that integrates:
    - Multi-camera obstacle detection
    - IR sensors
    - Motor control
    - Environmental sensors (DHT11, pH)
    - Data logging
    """
    
    def __init__(self):
        """Initialize all rover systems"""
        print("\n" + "="*70)
        print(" "*20 + "SPACE ROVER INITIALIZATION")
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
            },
            'adc_channel': 0
        }
        # self.sensors = SensorManager(sensor_config)
        print("  [Uncomment SensorManager import to enable]")
        
        # Initialize motors
        print("\n→ Initializing motors...")
        motor_config = {
            'left': {'in1': 5, 'in2': 6, 'en': 13},
            'right': {'in1': 19, 'in2': 26, 'en': 12}
        }
        # self.motors = MotorController(motor_config)
        print("  [Uncomment MotorController import to enable]")
        
        # Initialize cameras
        print("\n→ Initializing cameras...")
        camera_config = {
            'front': 0,
            # 'back': 1,
            # 'left': 2,
            # 'right': 3
        }
        # self.camera_detector = RoverMultiCameraDetector(camera_config)
        print("  [Uncomment RoverMultiCameraDetector import to enable]")
        
        # Operational parameters
        self.ir_priority_distance = 20  # cm, IR sensor trigger distance
        self.study_interval = 30  # seconds between soil studies
        self.last_study_time = 0
        self.movement_speed = 50  # Default speed (0-100)
        
        # Position tracking
        self.position = {'x': 0.0, 'y': 0.0, 'heading': 0.0}  # Starting at origin
        self.distance_per_second = 0.15  # meters (calibrate this!)
        
        # Data storage
        self.data_log = []
        self.log_file = 'rover_data_log.json'
        
        print("\n" + "="*70)
        print(" "*25 + "✓ ROVER READY")
        print("="*70 + "\n")
    
    def load_config(self) -> Dict:
        """Load configuration from file or use defaults"""
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
        """
        Update rover position based on movement
        Simple dead reckoning (will drift over time)
        
        Args:
            direction: 'forward', 'backward', 'left', 'right'
            duration: Time spent moving in seconds
        """
        import math
        
        distance = self.distance_per_second * duration
        
        if direction == 'forward':
            self.position['x'] += distance * math.cos(math.radians(self.position['heading']))
            self.position['y'] += distance * math.sin(math.radians(self.position['heading']))
        
        elif direction == 'backward':
            self.position['x'] -= distance * math.cos(math.radians(self.position['heading']))
            self.position['y'] -= distance * math.sin(math.radians(self.position['heading']))
        
        elif direction == 'left':
            self.position['heading'] = (self.position['heading'] + 45) % 360  # Approximate turn
        
        elif direction == 'right':
            self.position['heading'] = (self.position['heading'] - 45) % 360
        
        elif direction == 'spin_left':
            self.position['heading'] = (self.position['heading'] + 90) % 360
        
        elif direction == 'spin_right':
            self.position['heading'] = (self.position['heading'] - 90) % 360
    
    def get_position(self) -> Dict:
        """Get current position"""
        return {
            'x': round(self.position['x'], 2),
            'y': round(self.position['y'], 2),
            'heading': round(self.position['heading'], 1)
        }
    
    # ==================== Data Logging ====================
    
    def log_data(self, sensor_data: Dict, action: str, position: Dict):
        """
        Log sensor data with position and timestamp
        
        Args:
            sensor_data: All sensor readings
            action: Action taken by rover
            position: Current position
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'position': position,
            'temperature': sensor_data.get('temperature'),
            'humidity': sensor_data.get('humidity'),
            'soil_ph': sensor_data.get('soil_ph'),
            'soil_voltage': sensor_data.get('soil_voltage'),
            'obstacles': sensor_data.get('obstacles', {}),
            'action': action
        }
        
        self.data_log.append(log_entry)
        
        # Save to file periodically
        if len(self.data_log) % 10 == 0:  # Save every 10 entries
            self.save_log_to_file()
    
    def save_log_to_file(self):
        """Save data log to JSON file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.data_log, f, indent=2)
            print(f"✓ Data saved ({len(self.data_log)} entries)")
        except Exception as e:
            print(f"✗ Failed to save data: {e}")
    
    def export_to_csv(self, filename='rover_data.csv'):
        """Export log data to CSV for dashboard"""
        import csv
        
        try:
            with open(filename, 'w', newline='') as f:
                if not self.data_log:
                    return
                
                fieldnames = ['timestamp', 'x', 'y', 'heading', 'temperature', 
                            'humidity', 'soil_ph', 'action']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for entry in self.data_log:
                    row = {
                        'timestamp': entry['timestamp'],
                        'x': entry['position']['x'],
                        'y': entry['position']['y'],
                        'heading': entry['position']['heading'],
                        'temperature': entry.get('temperature'),
                        'humidity': entry.get('humidity'),
                        'soil_ph': entry.get('soil_ph'),
                        'action': entry['action']
                    }
                    writer.writerow(row)
            
            print(f"✓ Data exported to {filename}")
        except Exception as e:
            print(f"✗ Failed to export CSV: {e}")
    
    # ==================== Study Mode ====================
    
    def should_study_location(self) -> bool:
        """Determine if rover should stop and study current location"""
        current_time = time.time()
        
        if self.config['auto_study_enabled']:
            if current_time - self.last_study_time >= self.study_interval:
                return True
        
        return False
    
    def study_location(self):
        """
        Stop and study current location
        Take environmental and soil readings
        """
        print("\n" + "🔬"*35)
        print(" "*20 + "STUDYING LOCATION")
        print("🔬"*35)
        
        # Stop motors
        # self.motors.stop()
        
        # Get current position
        position = self.get_position()
        print(f"\n📍 Position: ({position['x']}, {position['y']}) | Heading: {position['heading']}°")
        
        # Take multiple readings for accuracy
        print("\n📊 Taking readings...")
        readings = []
        
        for i in range(3):
            # sensor_data = self.sensors.get_dashboard_data()
            sensor_data = {  # Simulated data
                'temperature': 25.0 + i * 0.1,
                'humidity': 45.0 + i * 0.5,
                'soil_ph': 6.8 + i * 0.05,
                'soil_voltage': 2.1
            }
            readings.append(sensor_data)
            time.sleep(1)
        
        # Average the readings
        avg_data = {
            'temperature': round(sum(r['temperature'] for r in readings) / 3, 2),
            'humidity': round(sum(r['humidity'] for r in readings) / 3, 2),
            'soil_ph': round(sum(r['soil_ph'] for r in readings) / 3, 2),
            'soil_voltage': round(sum(r['soil_voltage'] for r in readings) / 3, 3)
        }
        
        # Display results
        print(f"\n🌡️  Temperature: {avg_data['temperature']}°C")
        print(f"💧 Humidity: {avg_data['humidity']}%")
        print(f"🌱 Soil pH: {avg_data['soil_ph']}")
        print(f"⚡ Soil Voltage: {avg_data['soil_voltage']}V")
        
        # Log the data
        self.log_data(avg_data, "STUDY_LOCATION", position)
        
        self.last_study_time = time.time()
        
        print("\n✓ Study complete!")
        print("🔬"*35 + "\n")
        
        time.sleep(2)  # Brief pause before continuing
    
    # ==================== Main Control Loop ====================
    
    def make_navigation_decision(self) -> Dict:
        """
        Make navigation decision based on all available data
        Priority: IR sensors > Camera vision
        
        Returns:
            Decision dictionary with action and reasoning
        """
        # Get IR sensor data
        # ir_status = self.sensors.read_all_ir_sensors()
        ir_status = {'front': False, 'back': False, 'left': False, 'right': False}  # Simulated
        
        # Get camera decision
        # camera_decision = self.camera_detector.get_best_direction()
        camera_decision = {'recommended_direction': 'front', 'should_move': True}  # Simulated
        
        # Immediate IR check (highest priority)
        if ir_status.get('front', False):
            return {
                'action': 'stop',
                'reason': 'Front IR sensor triggered - obstacle too close!',
                'direction': None,
                'duration': 0
            }
        
        # If IR is clear, follow camera guidance
        recommended_dir = camera_decision.get('recommended_direction', 'stop')
        
        if recommended_dir == 'front' and not ir_status.get('front', False):
            return {
                'action': 'forward',
                'reason': 'Path clear ahead',
                'direction': 'forward',
                'duration': 2.0
            }
        
        elif recommended_dir == 'left' and not ir_status.get('left', False):
            return {
                'action': 'turn_left',
                'reason': 'Camera suggests left turn',
                'direction': 'left',
                'duration': 0.5
            }
        
        elif recommended_dir == 'right' and not ir_status.get('right', False):
            return {
                'action': 'turn_right',
                'reason': 'Camera suggests right turn',
                'direction': 'right',
                'duration': 0.5
            }
        
        elif recommended_dir == 'back' and not ir_status.get('back', False):
            return {
                'action': 'backward',
                'reason': 'Reversing to find alternate path',
                'direction': 'backward',
                'duration': 1.0
            }
        
        else:
            return {
                'action': 'spin_right',
                'reason': 'No clear path - rotating to scan area',
                'direction': 'spin_right',
                'duration': 0.8
            }
    
    def execute_action(self, decision: Dict):
        """
        Execute the navigation action
        
        Args:
            decision: Decision dictionary from make_navigation_decision()
        """
        action = decision['action']
        duration = decision.get('duration', 0)
        
        print(f"🚀 {action.upper()}: {decision['reason']}")
        
        # Execute motor command
        # Uncomment when motors are connected:
        """
        if action == 'forward':
            self.motors.move_forward(speed=self.movement_speed, duration=duration)
        elif action == 'backward':
            self.motors.move_backward(speed=self.movement_speed, duration=duration)
        elif action == 'turn_left':
            self.motors.turn_left(duration=duration)
        elif action == 'turn_right':
            self.motors.turn_right(duration=duration)
        elif action == 'spin_left':
            self.motors.spin_left(duration=duration)
        elif action == 'spin_right':
            self.motors.spin_right(duration=duration)
        elif action == 'stop':
            self.motors.stop()
        """
        
        # Update position tracking
        if decision['direction']:
            self.update_position(decision['direction'], duration)
        
        # Log the action
        position = self.get_position()
        sensor_data = {}  # self.sensors.get_dashboard_data()
        self.log_data(sensor_data, action, position)
    
    def run(self):
        """
        Main rover control loop
        """
        print("\n" + "▶"*35)
        print(" "*15 + "STARTING ROVER OPERATION")
        print("▶"*35 + "\n")
        print("Press Ctrl+C to stop\n")
        
        loop_count = 0
        
        try:
            while True:
                loop_count += 1
                print(f"\n{'─'*70}")
                print(f"Loop #{loop_count} | Time: {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'─'*70}")
                
                # Check if should study location
                if self.should_study_location():
                    self.study_location()
                
                # Make navigation decision
                decision = self.make_navigation_decision()
                
                # Execute the decision
                self.execute_action(decision)
                
                # Display current position
                pos = self.get_position()
                print(f"📍 Position: ({pos['x']}, {pos['y']}) @ {pos['heading']}°")
                
                # Brief pause between loops
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n" + "⏹"*35)
            print(" "*15 + "STOPPING ROVER")
            print("⏹"*35 + "\n")
            self.stop()
    
    def stop(self):
        """Shutdown rover safely"""
        print("→ Stopping motors...")
        # self.motors.stop()
        
        print("→ Saving final data...")
        self.save_log_to_file()
        self.export_to_csv()
        
        print("→ Cleaning up resources...")
        # self.motors.cleanup()
        # self.sensors.cleanup()
        # self.camera_detector.cleanup()
        
        print("\n✓ Rover shutdown complete")
        print(f"Total data points collected: {len(self.data_log)}")
        print(f"Final position: {self.get_position()}")


# ==================== Standalone Execution ====================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║                                                                    ║
    ║                   🛸 SPACE ROVER CONTROL SYSTEM 🛸                  ║
    ║                                                                    ║
    ║  Features:                                                         ║
    ║    ✓ Multi-camera obstacle detection                               ║
    ║    ✓ IR sensor integration                                         ║
    ║    ✓ Autonomous navigation                                         ║
    ║    ✓ Environmental sensing (temp, humidity)                        ║
    ║    ✓ Soil analysis (pH)                                            ║
    ║    ✓ Position tracking                                             ║
    ║    ✓ Data logging                                                  ║
    ║                                                                    ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)
    
    rover = RoverMainControl()
    rover.run()