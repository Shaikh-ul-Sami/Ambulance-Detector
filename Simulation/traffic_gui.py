import pygame

# --- Configuration ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
GRAY = (50, 50, 50) # Color for the "off" lights

class TrafficLight:
    """
    A class to represent and draw a single traffic light.
    """
    def __init__(self, x, y, radius=40):
        self.x = x
        self.y = y
        self.radius = radius
        self.light_state = 'red' # Default state

    def set_light(self, state):
        """Sets the current light state ('red', 'yellow', or 'green')."""
        if state in ['red', 'yellow', 'green']:
            self.light_state = state

    def draw(self, surface):
        """Draws the traffic light onto a given Pygame surface."""
        # Draw the background housing
        housing_rect = pygame.Rect(0, 0, self.radius * 2.5, self.radius * 7.5)
        housing_rect.center = (self.x, self.y)
        pygame.draw.rect(surface, BLACK, housing_rect, border_radius=15)

        # Determine which light is on
        red_color = RED if self.light_state == 'red' else GRAY
        yellow_color = YELLOW if self.light_state == 'yellow' else GRAY
        green_color = GREEN if self.light_state == 'green' else GRAY

        # Draw the three lights vertically
        pygame.draw.circle(surface, red_color, (self.x, self.y - self.radius * 2.2), self.radius)
        pygame.draw.circle(surface, yellow_color, (self.x, self.y), self.radius)
        pygame.draw.circle(surface, green_color, (self.x, self.y + self.radius * 2.2), self.radius)
