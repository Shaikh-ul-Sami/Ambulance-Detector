# d:\Smart Ambulance Traffic\core\traffic_system.py

import time
import cv2 # Import OpenCV for drawing
import collections
from Alerts.telegram_alert import send_alert
import constants

class TrafficSystem:
    """
    Encapsulates the entire state and logic for the smart traffic light system.
    """
    def __init__(self):
        # --- Color Mapping for Drawing ---
        self.color_map = {
            'RED': (0, 0, 255),
            'YELLOW': (0, 255, 255),
            'GREEN': (0, 255, 0)
        }

        # --- Core State ---
        # self.light_state = "RED" # OLD: Single state
        self.light_states = {lane: 'RED' for lane in constants.LANES}
        self.siren_heard = False # Siren is global (heard everywhere)
        self.density_per_lane = {lane: 0 for lane in constants.LANES}
        self.high_density_in_lane = {lane: False for lane in constants.LANES}
        self.ambulance_in_lane = {lane: False for lane in constants.LANES}
        self.manual_override = False

        # --- NEW: State for 4-way intersection ---
        self.active_phase = 'NS' # Can be 'NS' (North-South) or 'EW' (East-West)
        self.phase_map = {'NS': ['north', 'south'], 'EW': ['east', 'west']}

        # --- Timers and Counters ---
        self.yellow_light_timer = 0
        self.green_light_timer = 0
        self.low_density_timer = 0 # NEW: Timer for the green light grace period
        self.right_turn_red_timer = 0 # NEW: Timer for the right turn early red
        self.ambulance_disappeared_frames = 0

        # --- Alerting ---
        self.alert_sent = False
        self.density_alert_sent = False
        self.event_messages = collections.deque(maxlen=10) # For web app notifications

        # --- State Machine Mapping ---
        self.state_handlers = {
            'RED': self._handle_state_red,    # Logic for when the main light is RED
            'GREEN': self._handle_state_green,  # Logic for when the main light is GREEN
            'YELLOW': self._handle_state_yellow, # Logic for when the main light is YELLOW
        }

    def update_detection_results(self, lane, vehicle_count, ambulance_detected):
        """Updates the system's state based on the latest video frame analysis."""
        self.density_per_lane[lane] = vehicle_count
        self.ambulance_in_lane[lane] = ambulance_detected
        self.high_density_in_lane[lane] = vehicle_count >= constants.HIGH_DENSITY_THRESHOLD
 
    def tick(self):
        """Executes one cycle of the state machine logic."""
        # --- THE DEFINITIVE FIX ---
        # If the system is in manual override, the state machine must not run at all.
        # All state changes are handled exclusively by the 'manual_override' endpoint.
        if self.manual_override:
            return

        # --- NEW 4-WAY LOGIC ---
        # The state of the active phase determines the overall state. We'll use the first lane of the phase.
        active_lane = self.phase_map[self.active_phase][0]
        main_light_current_state = self.light_states.get(active_lane, 'RED')
        main_light_next_state = self.state_handlers[main_light_current_state]()

        # If the state changes, update all lights in the current phase.
        if main_light_current_state == 'RED' and main_light_next_state == 'GREEN':
            self._start_green_light_cycle()
            for lane in self.phase_map[self.active_phase]:
                self.light_states[lane] = 'GREEN'

        elif main_light_current_state == 'GREEN' and main_light_next_state == 'YELLOW':
            self.yellow_light_timer = self._get_time_ms()
            self.low_density_timer = 0
            self.right_turn_red_timer = 0
            for lane in self.phase_map[self.active_phase]:
                self.light_states[lane] = 'YELLOW'

        elif main_light_current_state == 'YELLOW' and main_light_next_state == 'RED':
            # The phase is over, switch to the other phase and set all its lights to RED.
            for lane in self.phase_map[self.active_phase]:
                self.light_states[lane] = 'RED'
            self.active_phase = 'EW' if self.active_phase == 'NS' else 'NS'

    def _get_time_ms(self):
        """Returns the current time in milliseconds."""
        return time.time() * 1000

    def set_auto_mode(self):
        """Resets the system to automatic control, initiating a safe transition."""
        self.manual_override = False
        self.event_messages.append("🕹️ Manual Override Disabled. Resuming Auto.")
        # Force a transition to YELLOW to safely re-enter the automatic cycle
        for lane in self.light_states:
            self.light_states[lane] = 'YELLOW'
        self.yellow_light_timer = self._get_time_ms()
        # --- THE DEFINITIVE FIX ---
        # Reset all stateful flags to ensure a clean start for the auto-cycle.
        self.alert_sent = False
        self.density_alert_sent = False
        self.siren_heard = False

    # --- State Handler Methods ---

    def _start_green_light_cycle(self):
        """Helper to handle logic when turning a light green."""
        self.green_light_timer = self._get_time_ms()
        if self.siren_heard and not self.alert_sent:
            msg = "🚨 SIREN DETECTED! Turning signal GREEN."
            self.event_messages.append(msg)
            send_alert(msg)
            self.alert_sent = True
        elif any(self.high_density_in_lane[lane] for lane in self.phase_map[self.active_phase]) and not self.density_alert_sent:
            msg = f"🚗 High traffic in {self.active_phase} phase! Turning signal GREEN."
            self.event_messages.append(msg)
            send_alert(msg)
            self.density_alert_sent = True

    def _handle_state_red(self):
        """Determines the next state from RED. Returns 'GREEN' or 'RED'."""
        # Check for events in the *inactive* phase to decide if we should switch.
        inactive_phase = 'EW' if self.active_phase == 'NS' else 'NS'
        
        # An ambulance in an inactive red-light lane is the highest priority event.
        ambulance_waiting = any(self.ambulance_in_lane[lane] for lane in self.phase_map[inactive_phase])
        if ambulance_waiting:
            return 'GREEN' # This will trigger a phase change in tick()

        # Check for high density in the inactive phase.
        density_waiting = any(self.high_density_in_lane[lane] for lane in self.phase_map[inactive_phase])
        event_detected = self.siren_heard or density_waiting
        if event_detected:
            return 'GREEN'
        return 'RED'

    def _handle_state_green(self):
        """Determines the next state from GREEN. Returns 'YELLOW' or 'GREEN'."""
        # Priority 1: An ambulance in an opposing lane forces a switch.
        inactive_phase = 'EW' if self.active_phase == 'NS' else 'NS'
        ambulance_waiting = any(self.ambulance_in_lane[lane] for lane in self.phase_map[inactive_phase])
        if ambulance_waiting:
            self.event_messages.append(f"🚑 Ambulance detected in {inactive_phase} phase! Switching lights.")
            return 'YELLOW'

        # Priority 1.5: If the green light has been on for its max duration, switch.
        # This prevents a phase from staying green forever if density remains high.
        if self._get_time_ms() - self.green_light_timer > constants.GREEN_LIGHT_DURATION_DENSITY:
            self.event_messages.append(f"🚦 Max green time for {self.active_phase} reached. Switching.")
            return 'YELLOW'

        # Priority 2: High-Density Logic
        if self.density_alert_sent:
            # Stay green as long as there is density in the current phase.
            if any(self.high_density_in_lane[lane] for lane in self.phase_map[self.active_phase]):
                self.low_density_timer = 0 # Reset grace period while density is high
                self.right_turn_red_timer = 0 # Also reset the right turn timer
                return 'GREEN'
            
            # Density has dropped, start the grace period timer.
            if self.low_density_timer == 0:
                self.low_density_timer = self._get_time_ms()
            
            # If grace period has passed, it's time to turn yellow.
            if self._get_time_ms() - self.low_density_timer > constants.GREEN_LIGHT_GRACE_PERIOD:
                self.event_messages.append("🚦 Traffic has cleared. Returning to RED.")
                return 'YELLOW'
            
            return 'GREEN' # Stay green during the grace period

        # Fallback: If the state is GREEN but no event (siren or density) is active,
        # transition to YELLOW to safely return to RED.
        return 'YELLOW'

    def _handle_state_yellow(self):
        """Determines the next state from YELLOW. Returns 'RED' or 'YELLOW'."""
        if self._get_time_ms() - self.yellow_light_timer > constants.YELLOW_LIGHT_DURATION:
            return 'RED'
        return 'YELLOW'

    def draw_lights_on_frame(self, frame, lane_name):
        """
        Draws the current state of the traffic light for a specific lane onto its frame.
        """
        if frame is None:
            return None

        # Position for the light indicator on the top-right of the frame
        # (frame_width - margin, margin_from_top)
        pos = (constants.RESIZE_WIDTH - 30, 30)
        
        # Get the color for the specified lane
        if lane_name in self.light_states:
            state = self.light_states[lane_name]
            color = self.color_map.get(state, (255, 255, 255)) # Default to white
            cv2.circle(frame, pos, 15, color, -1) # Draw a filled circle

        return frame