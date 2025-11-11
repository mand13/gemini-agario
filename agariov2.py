import pygame
import random
import math
import numpy as np
from colormath.color_objects import sRGBColor, LCHabColor
from colormath.color_conversions import convert_color

# --- Game Settings ---
SCREEN_WIDTH = 1000  # Game area width
SCREEN_HEIGHT = 800
SCOREBOARD_WIDTH = 200
TOTAL_WIDTH = SCREEN_WIDTH + SCOREBOARD_WIDTH

NUM_TEAMS = 8
PLAYERS_PER_TEAM = 5

# Player settings
START_MASS = 20
EAT_THRESHOLD = 1.1  # Must be 10% bigger to eat
FOOD_MASS = 2
SPEED_MULTIPLIER = 5.0 # This wasn't used in your original, I'm re-adding it

# Food settings
MAX_FOOD = 1000
FOOD_SPAWN_RATE = 0.3  # Chance to spawn one food pellet per frame

# Visuals
FOOD_COLOR = (200, 200, 200) # White
BACKGROUND_COLOR = (25, 25, 25) # Dark gray
SCOREBOARD_BG_COLOR = (35, 35, 35) # Slightly lighter dark gray
DIVIDER_COLOR = (100, 100, 100)
TEXT_COLOR_LIGHT = (220, 220, 220)
TEXT_COLOR_MUTED = (180, 180, 180)
BAR_BG_COLOR = (50, 50, 50)

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
        self.radius = int(math.sqrt(self.mass) * 4)
        # Use the SPEED_MULTIPLIER from settings
        self.speed = SPEED_MULTIPLIER * max(0.5, 8 - self.radius * 0.1)

    def move(self):
        """Updates the player's position with random movement."""
        self.move_timer -= 1
        
        if self.move_timer <= 0:
            self.move_timer = random.randint(30, 90) # Change direction every 0.5-1.5s
            angle = random.uniform(0, 2 * math.pi)
            self.dx = math.cos(angle)
            self.dy = math.sin(angle)
            
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        
        # Keep player within *game* screen bounds
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
        )

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
    pygame.font.init() # Initialize font module
    
    # Set up the display with the new total width
    screen = pygame.display.set_mode((TOTAL_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Agar.io AI Simulation")
    clock = pygame.time.Clock()

    # --- Initialize Fonts ---
    font_title = pygame.font.SysFont(None, 28, bold=True)
    font_main = pygame.font.SysFont(None, 20, bold=True)
    font_small = pygame.font.SysFont(None, 18)

    players = []
    food_pellets = []
    colors = generate_distinct_colors(NUM_TEAMS)

    # --- Initialize Players ---
    for team_id in range(NUM_TEAMS):
        color = colors[team_id]
        for _ in range(PLAYERS_PER_TEAM):
            # Spawn players only in the game area
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

            # 1. Spawn new food (only in game area)
            if random.random() < FOOD_SPAWN_RATE and len(food_pellets) < MAX_FOOD:
                fx = random.randint(0, SCREEN_WIDTH)
                fy = random.randint(0, SCREEN_HEIGHT)
                food_pellets.append(Food(fx, fy))

            # 2. Move players
            for player in players:
                player.move()

            # 3. Handle food collisions
            for player in players:
                for pellet in food_pellets.copy():
                    dist = get_distance(player.x, player.y, pellet.x, pellet.y)
                    if dist < player.radius + pellet.radius:
                        player.mass += FOOD_MASS
                        player.update_properties()
                        food_pellets.remove(pellet)

            # 4. Handle player collisions
            for player_a in players.copy():
                for player_b in players.copy():
                    if player_a not in players or player_b not in players:
                        continue # One of them was already eaten this frame
                    if player_a == player_b or player_a.team_id == player_b.team_id:
                        continue
                        
                    dist = get_distance(player_a.x, player_a.y, player_b.x, player_b.y)

                    if player_a.mass > player_b.mass * EAT_THRESHOLD:
                        if dist + player_b.radius < player_a.radius:
                            player_a.mass += player_b.mass
                            player_a.update_properties()
                            players.remove(player_b)
                    
                    elif player_b.mass > player_a.mass * EAT_THRESHOLD:
                        if dist + player_a.radius < player_b.radius:
                            player_b.mass += player_a.mass
                            player_b.update_properties()
                            players.remove(player_a)
                            
            # --- Scoreboard Data Calculation ---
            team_data = {}
            for i in range(NUM_TEAMS):
                # Store color as a tuple for pygame
                team_data[i] = {'mass': 0, 'player_count': 0, 'color': tuple(colors[i])}

            for player in players:
                team_data[player.team_id]['mass'] += player.mass
                team_data[player.team_id]['player_count'] += 1
            
            # Find max mass for proportional bar
            max_mass = 1 # Avoid division by zero
            for data in team_data.values():
                if data['mass'] > max_mass:
                    max_mass = data['mass']

            # Sort teams by mass, descending
            sorted_teams = sorted(team_data.items(), key=lambda item: item[1]['mass'], reverse=True)


            # --- Drawing ---
            
            # 1. Fill entire window
            screen.fill(BACKGROUND_COLOR)
            
            # 2. Draw food
            for pellet in food_pellets:
                pellet.draw(screen)
                
            # 3. Draw players
            for player in sorted(players, key=lambda p: p.mass):
                player.draw(screen)
                
            # 4. Draw Scoreboard
            
            # Draw scoreboard background
            scoreboard_rect = pygame.Rect(SCREEN_WIDTH, 0, SCOREBOARD_WIDTH, SCREEN_HEIGHT)
            pygame.draw.rect(screen, SCOREBOARD_BG_COLOR, scoreboard_rect)
            
            # Draw divider line
            pygame.draw.line(screen, DIVIDER_COLOR, (SCREEN_WIDTH, 0), (SCREEN_WIDTH, SCREEN_HEIGHT), 2)
            
            # Draw Title
            title_surface = font_title.render("Leaderboard", True, TEXT_COLOR_LIGHT)
            screen.blit(title_surface, (SCREEN_WIDTH + (SCOREBOARD_WIDTH - title_surface.get_width()) // 2, 10))
            
            # Draw Team Stats
            y_offset = 50
            bar_max_width = SCOREBOARD_WIDTH - 20 # 10px padding on each side
            bar_height = 10
            entry_height = 55 # Space for text + bar + padding
            
            for i, (team_id, data) in enumerate(sorted_teams):
                color = data['color']
                mass = data['mass']
                count = data['player_count']
                
                # Skip teams with 0 players (unless you want to show them as defeated)
                if count == 0 and mass == 0:
                    continue
                    
                current_y = y_offset + i * entry_height
                
                # --- Draw Text ---
                # "Team 0 (5 players)"
                team_text = f"Team {team_id} ({count} players)"
                team_surface = font_main.render(team_text, True, color)
                screen.blit(team_surface, (SCREEN_WIDTH + 10, current_y))
                
                # "Mass: 10,240"
                mass_text = f"Mass: {mass:,.0f}"
                mass_surface = font_small.render(mass_text, True, TEXT_COLOR_MUTED)
                screen.blit(mass_surface, (SCREEN_WIDTH + 10, current_y + 20))
                
                # --- Draw Bar ---
                bar_y = current_y + 40
                
                # Calculate proportional width
                bar_width_proportional = (mass / max_mass) * bar_max_width
                
                # Background of bar (the empty part)
                pygame.draw.rect(screen, BAR_BG_COLOR, (SCREEN_WIDTH + 10, bar_y, bar_max_width, bar_height))
                # Foreground of bar (the filled part)
                pygame.draw.rect(screen, color, (SCREEN_WIDTH + 10, bar_y, bar_width_proportional, bar_height))


            # Update the display
            pygame.display.flip()

            # Cap the framerate
            clock.tick(60)
            
    finally:
        pygame.quit()

# --- Run the Game ---
if __name__ == "__main__":
    main()