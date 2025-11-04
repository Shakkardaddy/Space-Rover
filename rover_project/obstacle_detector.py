import cv2
import numpy as np
import time
from enum import Enum

class Direction(Enum):
    FRONT = 0
    BACK = 1
    LEFT = 2
    RIGHT = 3

class RoverMultiCameraDetector:
    def __init__(self, camera_indices={'front': 0, 'back': 1, 'left': 2, 'right': 3}):
        """
        Initialize multi-camera obstacle detection for autonomous rover
        
        Args:
            camera_indices: Dict mapping direction to camera index
        """
        self.cameras = {}
        self.camera_indices = camera_indices
        
        # Initialize cameras
        for direction, index in camera_indices.items():
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Lower res for faster processing
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                self.cameras[direction] = cap
                print(f"✓ {direction.capitalize()} camera initialized")
            else:
                print(f"✗ Failed to open {direction} camera at index {index}")
        
        # Detection parameters
        self.min_obstacle_area = 1500  # Minimum area to consider as obstacle
        self.safe_zone_width = 0.4  # Center 40% is the "path"
        self.edge_threshold = (50, 150)  # Canny edge detection thresholds
        
        print(f"\nRover Multi-Camera System Ready ({len(self.cameras)} cameras active)")
    
    def preprocess_frame(self, frame):
        """Preprocess frame for obstacle detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (15, 15), 0)
        return blurred
    
    def detect_obstacles(self, frame):
        """
        Detect obstacles using edge detection and contour analysis
        
        Returns:
            obstacles: List of obstacle dictionaries
            processed_frame: Debug visualization frame
        """
        height, width = frame.shape[:2]
        processed = self.preprocess_frame(frame)
        
        # Edge detection
        edges = cv2.Canny(processed, *self.edge_threshold)
        
        # Morphological operations to connect edges
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=2)
        edges = cv2.erode(edges, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        obstacles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_obstacle_area:
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Calculate relative position
                rel_x = (center_x - width // 2) / (width // 2)  # -1 to 1
                rel_y = (center_y - height // 2) / (height // 2)
                
                obstacles.append({
                    'bbox': (x, y, w, h),
                    'center': (center_x, center_y),
                    'area': area,
                    'rel_position': (rel_x, rel_y),
                    'in_path': abs(rel_x) < self.safe_zone_width / 2
                })
        
        return obstacles, edges
    
    def analyze_direction(self, direction_name):
        """
        Analyze obstacles in a specific direction
        
        Returns:
            result: Dictionary with obstacle info and clearance
        """
        if direction_name not in self.cameras:
            return {'available': False, 'clear': False, 'obstacle_count': 0}
        
        cap = self.cameras[direction_name]
        ret, frame = cap.read()
        
        if not ret:
            return {'available': False, 'clear': False, 'obstacle_count': 0}
        
        obstacles, edges = self.detect_obstacles(frame)
        
        # Check if path is clear (no obstacles in center zone)
        path_obstacles = [obs for obs in obstacles if obs['in_path']]
        is_clear = len(path_obstacles) == 0
        
        return {
            'available': True,
            'clear': is_clear,
            'obstacle_count': len(obstacles),
            'path_obstacles': len(path_obstacles),
            'obstacles': obstacles,
            'frame': frame,
            'edges': edges
        }
    
    def get_best_direction(self):
        """
        Analyze all cameras and determine best direction to move
        
        Returns:
            decision: Dictionary with recommended direction and reasoning
        """
        results = {}
        
        # Analyze all directions
        for direction in self.cameras.keys():
            results[direction] = self.analyze_direction(direction)
        
        # Priority order for exploration: front > left > right > back
        priority = ['front', 'left', 'right', 'back']
        
        # Find first clear direction
        for direction in priority:
            if direction in results and results[direction]['clear']:
                return {
                    'recommended_direction': direction,
                    'reason': f'{direction.capitalize()} path is clear',
                    'should_move': True,
                    'all_results': results
                }
        
        # If no clear path, find direction with fewest obstacles
        available_results = {k: v for k, v in results.items() if v['available']}
        if available_results:
            best_direction = min(available_results.items(), 
                                key=lambda x: x[1]['path_obstacles'])[0]
            return {
                'recommended_direction': best_direction,
                'reason': f'{best_direction.capitalize()} has fewest obstacles',
                'should_move': True,
                'caution': True,
                'all_results': results
            }
        
        # All paths blocked or cameras unavailable
        return {
            'recommended_direction': 'stop',
            'reason': 'All paths blocked or cameras unavailable',
            'should_move': False,
            'all_results': results
        }
    
    def visualize_all_cameras(self):
        """
        Display all camera feeds with obstacle detection
        """
        print("\nStarting multi-camera visualization... Press 'q' to quit\n")
        
        while True:
            frames_to_show = {}
            
            for direction, cap in self.cameras.items():
                ret, frame = cap.read()
                if ret:
                    obstacles, edges = self.detect_obstacles(frame)
                    display = frame.copy()
                    
                    # Draw obstacles
                    for obs in obstacles:
                        x, y, w, h = obs['bbox']
                        color = (0, 0, 255) if obs['in_path'] else (0, 255, 0)
                        cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
                        cv2.circle(display, obs['center'], 5, color, -1)
                    
                    # Draw safe zone
                    height, width = frame.shape[:2]
                    zone_start = int(width * (0.5 - self.safe_zone_width / 2))
                    zone_end = int(width * (0.5 + self.safe_zone_width / 2))
                    cv2.rectangle(display, (zone_start, 0), (zone_end, height), 
                                (255, 255, 0), 1)
                    
                    # Add direction label
                    cv2.putText(display, direction.upper(), (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    
                    # Add obstacle count
                    path_obs = len([o for o in obstacles if o['in_path']])
                    status = "CLEAR" if path_obs == 0 else f"BLOCKED ({path_obs})"
                    color = (0, 255, 0) if path_obs == 0 else (0, 0, 255)
                    cv2.putText(display, status, (10, 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
                    frames_to_show[direction] = display
            
            if frames_to_show:
                # Arrange in grid (2x2)
                rows = []
                if 'front' in frames_to_show:
                    top_row = frames_to_show['front']
                    if 'back' in frames_to_show:
                        top_row = np.hstack([frames_to_show['front'], 
                                           frames_to_show['back']])
                    rows.append(top_row)
                
                if 'left' in frames_to_show:
                    bottom_row = frames_to_show['left']
                    if 'right' in frames_to_show:
                        bottom_row = np.hstack([frames_to_show['left'], 
                                              frames_to_show['right']])
                    rows.append(bottom_row)
                
                if rows:
                    grid = np.vstack(rows) if len(rows) > 1 else rows[0]
                    cv2.imshow('Rover Multi-Camera View', grid)
            
            # Get and display decision
            decision = self.get_best_direction()
            print(f"\r{'='*60}", end='')
            print(f"\rRECOMMENDED: {decision['recommended_direction'].upper()} - "
                  f"{decision['reason']}", end='')
            
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
        
        self.cleanup()
    
    def cleanup(self):
        """Release all camera resources"""
        for cap in self.cameras.values():
            cap.release()
        cv2.destroyAllWindows()
        print("\n\nCameras released successfully")


# Example usage
if __name__ == "__main__":
    # Initialize with available cameras (adjust indices as needed)
    detector = RoverMultiCameraDetector(camera_indices={
        'front': 0,  # Adjust these indices based on your setup
        # 'back': 1,
        # 'left': 2,
        # 'right': 3
    })
    
    # Option 1: Visualize all cameras
    detector.visualize_all_cameras()
    
    # Option 2: Get single decision (for integration with main rover control)
    # decision = detector.get_best_direction()
    # print(f"Move: {decision['recommended_direction']}")
    # print(f"Reason: {decision['reason']}")