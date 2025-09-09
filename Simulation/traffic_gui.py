import pygame

# --- Configuration ---
WINDOW_WIDTH = 200
WINDOW_HEIGHT = 400
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
GRAY = (50, 50, 50) # Color for the "off" lights

def run_simulation(current_light='red'):
    """
    Initializes a Pygame window and displays a traffic light.
    The active light is determined by the 'current_light' parameter.
    """
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Traffic Simulation")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Fill the background
        screen.fill(BLACK)

        # Determine which light is on
        red_color = RED if current_light == 'red' else GRAY
        yellow_color = YELLOW if current_light == 'yellow' else GRAY
        green_color = GREEN if current_light == 'green' else GRAY

        # Draw the three lights
        pygame.draw.circle(screen, red_color, (WINDOW_WIDTH // 2, 80), 50)
        pygame.draw.circle(screen, yellow_color, (WINDOW_WIDTH // 2, 200), 50)
        pygame.draw.circle(screen, green_color, (WINDOW_WIDTH // 2, 320), 50)

        # Update the display
        pygame.display.flip()

    pygame.quit()

# This part allows us to test the simulation by itself
if __name__ == "__main__":
    # You can change 'red' to 'green' or 'yellow' to test
    run_simulation('red')