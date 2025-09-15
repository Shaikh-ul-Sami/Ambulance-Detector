import pygame

# --- Configuration ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)

# --- New, more realistic colors ---
HOUSING_COLOR = (30, 30, 30)       # Dark grey for the housing
BULB_OFF_COLOR = (20, 20, 20)      # Very dark color for off bulbs
RED_GLOW = (100, 0, 0)
YELLOW_GLOW = (100, 100, 0)
GREEN_GLOW = (0, 100, 0)

class TrafficLight:
    """
    A class to represent and draw a single traffic light.
    """
    def __init__(self, x, y, radius=40):
        self.x = x
        self.y = y # This will be the center of the middle (yellow) light
        self.radius = radius
        self.light_state = 'red' # Default state

    def set_light(self, state):
        """Sets the current light state ('red', 'yellow', or 'green')."""
        if state in ['red', 'yellow', 'green']:
            self.light_state = state

    def draw(self, surface):
        """Draws the traffic light onto a given Pygame surface."""
        # Draw the background housing
        housing_rect = pygame.Rect(0, 0, self.radius * 2.5, self.radius * 7)
        housing_rect.center = (self.x, self.y)
        pygame.draw.rect(surface, HOUSING_COLOR, housing_rect, border_radius=10)

        # Determine which light is on
        is_red = self.light_state == 'red'
        is_yellow = self.light_state == 'yellow'
        is_green = self.light_state == 'green'

        # --- Draw Glows (if active) ---
        glow_radius = int(self.radius * 1.5)
        if is_red: pygame.draw.circle(surface, RED_GLOW, (self.x, self.y - self.radius * 2.2), glow_radius)
        if is_yellow: pygame.draw.circle(surface, YELLOW_GLOW, (self.x, self.y), glow_radius)
        if is_green: pygame.draw.circle(surface, GREEN_GLOW, (self.x, self.y + self.radius * 2.2), glow_radius)

        # --- Draw the three bulbs ---
        red_color = RED if is_red else BULB_OFF_COLOR
        yellow_color = YELLOW if is_yellow else BULB_OFF_COLOR
        green_color = GREEN if is_green else BULB_OFF_COLOR

        pygame.draw.circle(surface, red_color, (self.x, self.y - self.radius * 2.2), self.radius)
        pygame.draw.circle(surface, yellow_color, (self.x, self.y), self.radius)
        pygame.draw.circle(surface, green_color, (self.x, self.y + self.radius * 2.2), self.radius)
