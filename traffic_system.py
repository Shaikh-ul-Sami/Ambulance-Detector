# d:\Smart Ambulance Traffic\core\traffic_system.py

import time
import collections
from Alerts.telegram_alert import send_alert
import constants

class TrafficSystem:
    """
    Encapsulates the entire state and logic for the smart traffic light system.
    """
    def __init__(self):
        # --- Core State ---
        # self.light_state = "RED" # OLD: Single state
        self.light_states = {
            'straight': 'RED',
            'left': 'RED',
            'right': 'RED'
        }
        self.siren_heard = False
        self.high_density_detected = False
        self.ambulance_visible = False
        self.last_vehicle_count = 0
        self.manual_override = False

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

    @property
    def light_state(self):
        """Provides backward compatibility for components expecting a single state."""
        return self.light_states['straight']

    def update_detection_results(self, vehicle_count, ambulance_detected):
        """Updates the system's state based on the latest video frame analysis."""
        self.last_vehicle_count = vehicle_count
        self.ambulance_visible = ambulance_detected
        self.high_density_detected = vehicle_count >= constants.HIGH_DENSITY_THRESHOLD
 
    def tick(self):
        """Executes one cycle of the state machine logic."""
        # --- Handle Manual Override Separately ---
        if self.manual_override:
            # In manual mode, no state changes happen automatically.
            return

        # --- Independent Lane Logic ---
        # The main state machine is driven by the 'straight' lane.
        current_main_state = self.light_states['straight']
        handler = self.state_handlers.get(current_main_state, self._handle_state_red)
        next_main_state = handler()

        # If the main state changes, update the straight and left lanes.
        if current_main_state != next_main_state:
            self.light_states['straight'] = next_main_state
            self.light_states['left'] = next_main_state

            # Special logic for the right lane when transitioning from GREEN
            if current_main_state == 'GREEN' and next_main_state == 'YELLOW':
                # The right lane also turns yellow with the main signal.
                self.light_states['right'] = 'YELLOW'
            else:
                # For all other transitions (e.g., RED->GREEN, YELLOW->RED), the right lane follows.
                self.light_states['right'] = next_main_state

        # --- Logic for Right Turn Early Red ---
        # If the main light is GREEN and the grace period for low density has started...
        if self.light_states['straight'] == 'GREEN' and self.low_density_timer > 0:
            # And if the right turn hasn't started its early red timer yet...
            if self.right_turn_red_timer == 0:
                self.right_turn_red_timer = self._get_time_ms()

            # If the short delay for the right turn has passed, turn it yellow.
            if self.right_turn_red_timer > 0 and self._get_time_ms() - self.right_turn_red_timer > constants.RIGHT_TURN_YELLOW_DELAY:
                self.light_states['right'] = 'YELLOW'

    def _get_time_ms(self):
        """Returns the current time in milliseconds."""
        return time.time() * 1000

    # --- State Handler Methods ---

    def _handle_state_red(self):

        event_detected = self.siren_heard or self.high_density_detected
        if event_detected:
            self.green_light_timer = self._get_time_ms()
            if self.siren_heard and not self.alert_sent:
                msg = "🚨 SIREN DETECTED! Turning signal GREEN."
                self.event_messages.append(msg)
                send_alert(msg)
                self.alert_sent = True
            elif self.high_density_detected and not self.density_alert_sent:
                msg = f"🚗 High traffic ({self.last_vehicle_count} vehicles)! Turning signal GREEN."
                self.event_messages.append(msg)
                send_alert(msg)
                self.density_alert_sent = True
            return 'GREEN'
        return 'RED'

    def _handle_state_green(self):
        if self.siren_heard:
            self.ambulance_disappeared_frames = 0 if self.ambulance_visible else self.ambulance_disappeared_frames + 1
            if self.ambulance_disappeared_frames > 30:
                self.yellow_light_timer = self._get_time_ms()
                self.siren_heard = False
                self.alert_sent = False
                self.event_messages.append("↩️ Ambulance passed. Resuming normal cycle.")
                return 'YELLOW'
            return 'GREEN'

        # This part handles the high-density case with the new grace period logic.
        if self.density_alert_sent:
            # If density is still high, reset the grace period timer and stay green.
            if self.high_density_detected:
                self.low_density_timer = 0
                self.right_turn_red_timer = 0 # Also reset the right turn timer
                return 'GREEN'
            
            # If density has dropped, start the grace period timer if it hasn't been started.
            if self.low_density_timer == 0:
                self.low_density_timer = self._get_time_ms()
            
            # If the grace period has passed, switch to yellow.
            if self._get_time_ms() - self.low_density_timer > constants.GREEN_LIGHT_GRACE_PERIOD:
                self.yellow_light_timer = self._get_time_ms()
                self.event_messages.append("🚦 Traffic has cleared. Returning to RED.")
                self.low_density_timer = 0 # Reset timer for next time
                self.right_turn_red_timer = 0 # Reset right turn timer
                return 'YELLOW'
            
            return 'GREEN' # Stay green during the grace period.

        # Fallback: If the state is GREEN but no event (siren or density) is active,
        # transition to YELLOW to safely return to RED.
        self.yellow_light_timer = self._get_time_ms()
        return 'YELLOW'

    def _handle_state_yellow(self):
        if self._get_time_ms() - self.yellow_light_timer > constants.YELLOW_LIGHT_DURATION:
            self.density_alert_sent = False
            # When transitioning to RED, all lights turn red together.
            self.light_states['right'] = 'RED'
            self.light_states['left'] = 'RED'
            self.light_states['straight'] = 'RED'
            return 'RED' # Return RED to confirm the state change
        return 'YELLOW'