import pygame
import random
import math
import numpy as np
from colormath.color_objects import sRGBColor, LCHabColor
from colormath.color_conversions import convert_color

# --- Game Settings ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 800
NUM_TEAMS = 8
PLAYERS_PER_TEAM = 5

# Player settings
START_MASS = 20
EAT_THRESHOLD = 1.1  # Must be 10% bigger to eat
FOOD_MASS = 2
SPEED_MULTIPLIER = 5.0

# Food settings
MAX_FOOD = 1000
FOOD_SPAWN_RATE = 0.3  # Chance to spawn one food pellet per frame

# Visuals
FOOD_COLOR = (200, 200, 200) # White
BACKGROUND_COLOR = (25, 25, 25) # Dark gray

# --- Helper Function ---
def get_distance(x1, y1, x2, y2):
    """Calculates the distance between two points."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# --- Player Class ---
class Player:
    def __init__(self, x, y, team_id, color, start_mass):
        self.x = x
        self.y = y
        self.team_id = team_id
        self.color = color
        self.mass = start_mass
        self.radius = 0
        self.speed = 0
        self.update_properties()
        
        # Movement-related
        self.move_timer = 0
        self.dx = 0
        self.dy = 0

    def update_properties(self):
        """Updates radius and speed based on current mass."""
        # Area = pi * r^2, so r = sqrt(Area / pi)
        # We'll use mass as a proxy for area, and scale it for visibility
        self.radius = int(math.sqrt(self.mass) * 4)
        
        # Speed decreases as size increases
        self.speed = 5*max(0.5, 8 - self.radius * 0.1)

    def move(self):
        """Updates the player's position with random movement."""
        self.move_timer -= 1
        
        # Pick a new random direction every so often
        if self.move_timer <= 0:
            self.move_timer = random.randint(30, 90) # Change direction every 0.5-1.5s
            angle = random.uniform(0, 2 * math.pi)
            self.dx = math.cos(angle)
            self.dy = math.sin(angle)
            
        # Move the player
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        
        # Keep player within screen bounds
        # (Clamps the center, not the edge, for simplicity)
        self.x = max(0, min(self.x, SCREEN_WIDTH))
        self.y = max(0, min(self.y, SCREEN_HEIGHT))

    def draw(self, screen):
        """Draws the player cell on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

# --- Food Class ---
class Food:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 3
        self.color = (
            random.randint(200, 255),
            random.randint(200, 255),
            random.randint(200, 255)
        ) # Varied bright colors

    def draw(self, screen):
        """Draws the food pellet on the screen."""
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)

def generate_distinct_colors(num_teams):
    """
    Generates a list of perceptually distinct colors using the
    LCHab (Lightness, Chroma, Hue) color space.
    """
    colors_rgb_list = []
    
    for i in range(num_teams):
        hue = i * (360.0 / num_teams)
        lightness = 70.0 if i % 2 == 0 else 55.0
        chroma = 60.0
        lch_color = LCHabColor(lightness, chroma, hue)
        rgb_color = convert_color(lch_color, sRGBColor)
        
        r_clamped = rgb_color.clamped_rgb_r
        g_clamped = rgb_color.clamped_rgb_g
        b_clamped = rgb_color.clamped_rgb_b
        
        r_int = int(r_clamped * 255)
        g_int = int(g_clamped * 255)
        b_int = int(b_clamped * 255)
        
        colors_rgb_list.append((r_int, g_int, b_int))
    
    return np.array(colors_rgb_list, dtype=np.uint8)

# --- Main Game Function ---
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Agar.io AI Simulation")
    clock = pygame.time.Clock()

    players = []
    food_pellets = []
    colors = generate_distinct_colors(NUM_TEAMS)

    # --- Initialize Players ---
    for team_id in range(NUM_TEAMS):
        color = colors[team_id]
        for _ in range(PLAYERS_PER_TEAM):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            players.append(Player(x, y, team_id, color, START_MASS))

    running = True
    try:
        while running:
            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # --- Game State Updates ---

            # 1. Spawn new food
            if random.random() < FOOD_SPAWN_RATE and len(food_pellets) < MAX_FOOD:
                fx = random.randint(0, SCREEN_WIDTH)
                fy = random.randint(0, SCREEN_HEIGHT)
                food_pellets.append(Food(fx, fy))

            # 2. Move players
            for player in players:
                player.move()

            # 3. Handle food collisions (Player eats food)
            # We iterate over a copy of the list to safely remove items
            for player in players:
                for pellet in food_pellets.copy():
                    dist = get_distance(player.x, player.y, pellet.x, pellet.y)
                    if dist < player.radius + pellet.radius:
                        player.mass += FOOD_MASS
                        player.update_properties()
                        food_pellets.remove(pellet)

            # 4. Handle player collisions (Player eats player)
            # This is O(n^2), which is fine for a small number of players
            for player_a in players.copy():
                for player_b in players.copy():
                    if player_a == player_b or player_a.team_id == player_b.team_id:
                        continue # Don't eat yourself or teammates
                        
                    dist = get_distance(player_a.x, player_a.y, player_b.x, player_b.y)

                    # Check if A can eat B
                    if player_a.mass > player_b.mass * EAT_THRESHOLD:
                        # "Completely overlaps": smaller circle is entirely inside larger one
                        if dist + player_b.radius < player_a.radius:
                            player_a.mass += player_b.mass
                            player_a.update_properties()
                            if player_b in players:
                                players.remove(player_b)
                    
                    # Check if B can eat A
                    elif player_b.mass > player_a.mass * EAT_THRESHOLD:
                        if dist + player_a.radius < player_b.radius:
                            player_b.mass += player_a.mass
                            player_b.update_properties()
                            if player_a in players:
                                players.remove(player_a)

            # --- Drawing ---
            screen.fill(BACKGROUND_COLOR)
            
            # Draw food
            for pellet in food_pellets:
                pellet.draw(screen)
                
            # Draw players (sorted by mass so smaller ones are drawn "under" larger ones)
            for player in sorted(players, key=lambda p: p.mass):
                player.draw(screen)

            # Update the display
            pygame.display.flip()

            # Cap the framerate
            clock.tick(60)
            
    finally:
        pygame.quit()

# --- Run the Game ---
if __name__ == "__main__":
    main()