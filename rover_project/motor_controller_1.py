import RPi.GPIO as GPIO
import time
from typing import Dict, Optional

class MotorController:
    """
    Motor controller for rover using ONE L298N motor driver
    Supports 4-wheel drive with motors wired in pairs:
    - Left side: Front-Left + Back-Left (Channel A)
    - Right side: Front-Right + Back-Right (Channel B)
    """
    
    def __init__(self, motor_pins: Dict, pwm_frequency: int = 1000):
        """
        Initialize motor controller
        
        Args:
            motor_pins: Dictionary with motor pin configurations
                Single L298N configuration:
                {
                    'left': {'in1': 5, 'in2': 6, 'en': 13},    # Channel A (left pair)
                    'right': {'in1': 19, 'in2': 26, 'en': 12}  # Channel B (right pair)
                }
                
        Wiring:
            Channel A (Motor A):
                OUT1 & OUT2 → Front-Left Motor (parallel)
                OUT1 & OUT2 → Back-Left Motor (parallel)
            
            Channel B (Motor B):
                OUT3 & OUT4 → Front-Right Motor (parallel)
                OUT3 & OUT4 → Back-Right Motor (parallel)
                
        pwm_frequency: PWM frequency in Hz (default 1000)
        """
        self.motor_pins = motor_pins
        self.pwm_frequency = pwm_frequency
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Initialize motors
        self.pwm = {}
        self.init_motors()
        
        # Speed settings (0-100)
        self.default_speed = 50
        self.current_speed = self.default_speed
        self.turn_speed_reduction = 0.6  # Reduce speed when turning
        
        print("✓ Motor Controller Initialized")
    
    def init_motors(self):
        """Initialize all motor pins and PWM"""
        for side, pins in self.motor_pins.items():
            # Setup direction pins
            GPIO.setup(pins['in1'], GPIO.OUT)
            GPIO.setup(pins['in2'], GPIO.OUT)
            
            # Setup enable pin with PWM
            GPIO.setup(pins['en'], GPIO.OUT)
            self.pwm[side] = GPIO.PWM(pins['en'], self.pwm_frequency)
            self.pwm[side].start(0)
            
            print(f"✓ {side.capitalize()} motor initialized (EN: GPIO{pins['en']})")
    
    # ==================== Basic Motor Control ====================
    
    def set_motor_speed(self, side: str, speed: int):
        """
        Set motor speed using PWM
        
        Args:
            side: 'left' or 'right'
            speed: Speed value 0-100
        """
        if side in self.pwm:
            speed = max(0, min(100, speed))  # Clamp to 0-100
            self.pwm[side].ChangeDutyCycle(speed)
    
    def motor_forward(self, side: str):
        """Set motor to move forward"""
        pins = self.motor_pins[side]
        GPIO.output(pins['in1'], GPIO.HIGH)
        GPIO.output(pins['in2'], GPIO.LOW)
    
    def motor_backward(self, side: str):
        """Set motor to move backward"""
        pins = self.motor_pins[side]
        GPIO.output(pins['in1'], GPIO.LOW)
        GPIO.output(pins['in2'], GPIO.HIGH)
    
    def motor_stop(self, side: str):
        """Stop motor"""
        pins = self.motor_pins[side]
        GPIO.output(pins['in1'], GPIO.LOW)
        GPIO.output(pins['in2'], GPIO.LOW)
        self.set_motor_speed(side, 0)
    
    # ==================== Movement Commands ====================
    
    def move_forward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Move rover forward
        
        Args:
            speed: Speed (0-100), uses default if None
            duration: Time in seconds, continuous if None
        """
        speed = speed or self.current_speed
        
        self.motor_forward('left')
        self.motor_forward('right')
        self.set_motor_speed('left', speed)
        self.set_motor_speed('right', speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def move_backward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Move rover backward"""
        speed = speed or self.current_speed
        
        self.motor_backward('left')
        self.motor_backward('right')
        self.set_motor_speed('left', speed)
        self.set_motor_speed('right', speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def turn_left(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Turn left by reducing left motor speed or reversing
        
        Args:
            speed: Speed (0-100)
            duration: Time in seconds
        """
        speed = speed or int(self.current_speed * self.turn_speed_reduction)
        
        # Method 1: Slow down left side (gradual turn)
        self.motor_forward('left')
        self.motor_forward('right')
        self.set_motor_speed('left', int(speed * 0.3))  # Left slower
        self.set_motor_speed('right', speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def turn_right(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """Turn right by reducing right motor speed"""
        speed = speed or int(self.current_speed * self.turn_speed_reduction)
        
        self.motor_forward('left')
        self.motor_forward('right')
        self.set_motor_speed('left', speed)
        self.set_motor_speed('right', int(speed * 0.3))  # Right slower
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def spin_left(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Spin left in place (left backward, right forward)
        """
        speed = speed or int(self.current_speed * 0.7)
        
        self.motor_backward('left')
        self.motor_forward('right')
        self.set_motor_speed('left', speed)
        self.set_motor_speed('right', speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def spin_right(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Spin right in place (left forward, right backward)
        """
        speed = speed or int(self.current_speed * 0.7)
        
        self.motor_forward('left')
        self.motor_backward('right')
        self.set_motor_speed('left', speed)
        self.set_motor_speed('right', speed)
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def stop(self):
        """Stop all motors"""
        self.motor_stop('left')
        self.motor_stop('right')
    
    # ==================== Advanced Control with Sensors ====================
    
    def navigate_with_ir(self, ir_status: Dict[str, bool], speed: Optional[int] = None):
        """
        Navigate based on IR sensor readings
        
        Args:
            ir_status: Dict with obstacle status {'front': bool, 'back': bool, ...}
            speed: Movement speed
            
        Returns:
            action: String describing action taken
        """
        speed = speed or self.current_speed
        
        front_blocked = ir_status.get('front', False)
        left_blocked = ir_status.get('left', False)
        right_blocked = ir_status.get('right', False)
        back_blocked = ir_status.get('back', False)
        
        # Decision logic
        if not front_blocked:
            self.move_forward(speed)
            return "Moving forward - path clear"
        
        elif not right_blocked:
            self.turn_right(speed, duration=0.5)
            return "Turning right - front blocked"
        
        elif not left_blocked:
            self.turn_left(speed, duration=0.5)
            return "Turning left - front blocked"
        
        elif not back_blocked:
            self.move_backward(speed, duration=1.0)
            return "Reversing - front/sides blocked"
        
        else:
            self.stop()
            return "STOPPED - All directions blocked!"
    
    def navigate_with_camera_and_ir(self, camera_decision: Dict, ir_status: Dict[str, bool], 
                                    speed: Optional[int] = None):
        """
        Navigate using both camera vision and IR sensors
        IR sensors have priority for immediate obstacle avoidance
        
        Args:
            camera_decision: Decision from camera system
            ir_status: IR sensor readings
            speed: Movement speed
            
        Returns:
            action: String describing action taken
        """
        speed = speed or self.current_speed
        
        # IR has priority - immediate danger
        front_ir_blocked = ir_status.get('front', False)
        
        if front_ir_blocked:
            # Emergency stop if front IR detects obstacle
            self.stop()
            return "EMERGENCY STOP - Front IR triggered"
        
        # If IR is clear, follow camera decision
        recommended_dir = camera_decision.get('recommended_direction', 'stop')
        
        if recommended_dir == 'front':
            # Check front IR one more time
            if not ir_status.get('front', False):
                self.move_forward(speed)
                return "Moving forward (camera + IR clear)"
            else:
                self.stop()
                return "Stopped - IR overrides camera"
        
        elif recommended_dir == 'left':
            if not ir_status.get('left', False):
                self.turn_left(speed, duration=0.5)
                return "Turning left (camera guidance)"
            else:
                # Try right instead
                if not ir_status.get('right', False):
                    self.turn_right(speed, duration=0.5)
                    return "Turning right (left blocked by IR)"
                else:
                    self.stop()
                    return "Stopped - sides blocked"
        
        elif recommended_dir == 'right':
            if not ir_status.get('right', False):
                self.turn_right(speed, duration=0.5)
                return "Turning right (camera guidance)"
            else:
                if not ir_status.get('left', False):
                    self.turn_left(speed, duration=0.5)
                    return "Turning left (right blocked by IR)"
                else:
                    self.stop()
                    return "Stopped - sides blocked"
        
        elif recommended_dir == 'back':
            if not ir_status.get('back', False):
                self.move_backward(speed, duration=0.8)
                return "Reversing (camera suggests)"
            else:
                self.stop()
                return "Stopped - back blocked"
        
        else:  # 'stop'
            self.stop()
            return "Stopped - no clear path"
    
    # ==================== Speed Control ====================
    
    def set_speed(self, speed: int):
        """Set default movement speed"""
        self.current_speed = max(0, min(100, speed))
        print(f"Speed set to {self.current_speed}%")
    
    def increase_speed(self, increment: int = 10):
        """Increase speed"""
        self.set_speed(self.current_speed + increment)
    
    def decrease_speed(self, decrement: int = 10):
        """Decrease speed"""
        self.set_speed(self.current_speed - decrement)
    
    # ==================== Cleanup ====================
    
    def cleanup(self):
        """Stop motors and cleanup GPIO"""
        self.stop()
        for pwm in self.pwm.values():
            pwm.stop()
        GPIO.cleanup()
        print("✓ Motor controller cleaned up")


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Motor pin configuration for L298N
    motor_config = {
        'left': {
            'in1': 5,   # GPIO5
            'in2': 6,   # GPIO6
            'en': 13    # GPIO13 (PWM)
        },
        'right': {
            'in1': 19,  # GPIO19
            'in2': 26,  # GPIO26
            'en': 12    # GPIO12 (PWM)
        }
    }
    
    # Initialize controller
    motors = MotorController(motor_config)
    motors.set_speed(50)  # Set to 50% speed
    
    try:
        print("\n" + "="*60)
        print("MOTOR TEST SEQUENCE")
        print("="*60 + "\n")
        
        # Test 1: Forward
        print("1. Moving forward...")
        motors.move_forward(duration=2)
        time.sleep(1)
        
        # Test 2: Backward
        print("2. Moving backward...")
        motors.move_backward(duration=2)
        time.sleep(1)
        
        # Test 3: Turn left
        print("3. Turning left...")
        motors.turn_left(duration=1)
        time.sleep(1)
        
        # Test 4: Turn right
        print("4. Turning right...")
        motors.turn_right(duration=1)
        time.sleep(1)
        
        # Test 5: Spin left
        print("5. Spinning left...")
        motors.spin_left(duration=1)
        time.sleep(1)
        
        # Test 6: Spin right
        print("6. Spinning right...")
        motors.spin_right(duration=1)
        time.sleep(1)
        
        # Test 7: IR-based navigation simulation
        print("\n7. Testing IR-based navigation...")
        
        # Simulate different IR scenarios
        scenarios = [
            {'front': False, 'left': False, 'right': False, 'back': False},  # All clear
            {'front': True, 'left': False, 'right': False, 'back': False},   # Front blocked
            {'front': True, 'left': True, 'right': False, 'back': False},    # Front & left blocked
            {'front': True, 'left': True, 'right': True, 'back': False},     # Only back clear
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n  Scenario {i}: {scenario}")
            action = motors.navigate_with_ir(scenario, speed=40)
            print(f"  Action: {action}")
            time.sleep(1.5)
            motors.stop()
            time.sleep(0.5)
        
        print("\n✓ Motor test complete!")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    finally:
        motors.cleanup()