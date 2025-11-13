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
EAT_THRESHOLD = 1.1
FOOD_MASS = 2
SPEED_MULTIPLIER = 5.0

# Food settings
MAX_FOOD = 1000
FOOD_SPAWN_RATE = 0.3

# Visuals
FOOD_COLOR = (200, 200, 200)
BACKGROUND_COLOR = (25, 25, 25)
SCOREBOARD_BG_COLOR = (35, 35, 35)
DIVIDER_COLOR = (100, 100, 100)
TEXT_COLOR_LIGHT = (220, 220, 220)
TEXT_COLOR_MUTED = (180, 180, 180)
BAR_BG_COLOR = (50, 50, 50)
VICTORY_OVERLAY_COLOR = (25, 25, 25, 200) # Dark, semi-transparent

# --- Helper Function ---
def get_distance(x1, y1, x2, y2):
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
        
        self.move_timer = 0
        self.dx = 0
        self.dy = 0

    def update_properties(self):
        self.radius = int(math.sqrt(self.mass) * 4)
        self.speed = SPEED_MULTIPLIER * max(0.5, 8 - self.radius * 0.1)

    def move(self):
        self.move_timer -= 1
        
        if self.move_timer <= 0:
            self.move_timer = random.randint(30, 90)
            angle = random.uniform(0, 2 * math.pi)
            self.dx = math.cos(angle)
            self.dy = math.sin(angle)
            
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        
        self.x = max(0, min(self.x, SCREEN_WIDTH))
        self.y = max(0, min(self.y, SCREEN_HEIGHT))

    def draw(self, screen):
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
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)

def generate_distinct_colors(num_teams):
    colors_rgb_list = []
    
    for i in range(num_teams):
        hue = i * (360.0 / num_teams)
        lightness = 70.0 if i % 2 == 0 else 55.0
        chroma = 60.0
        lch_color = LCHabColor(lightness, chroma, hue)
        rgb_color = convert_color(lch_color, sRGBColor)
        
        r_int = int(rgb_color.clamped_rgb_r * 255)
        g_int = int(rgb_color.clamped_rgb_g * 255)
        b_int = int(rgb_color.clamped_rgb_b * 255)
        
        colors_rgb_list.append((r_int, g_int, b_int))
    
    return np.array(colors_rgb_list, dtype=np.uint8)

# --- Main Game Function ---
def main():
    pygame.init()
    pygame.font.init()
    
    screen = pygame.display.set_mode((TOTAL_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Agar.io AI Simulation")
    clock = pygame.time.Clock()

    # Fonts
    font_title = pygame.font.SysFont(None, 28, bold=True)
    font_main = pygame.font.SysFont(None, 20, bold=True)
    font_small = pygame.font.SysFont(None, 18)
    font_large = pygame.font.SysFont(None, 100, bold=True)
    font_medium = pygame.font.SysFont(None, 50)

    players = []
    food_pellets = []
    colors = generate_distinct_colors(NUM_TEAMS)

    # Initialize Players
    for team_id in range(NUM_TEAMS):
        color = colors[team_id]
        for _ in range(PLAYERS_PER_TEAM):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            players.append(Player(x, y, team_id, color, START_MASS))

    # Game State
    game_state = "playing" # Can be "playing", "paused", "victory"
    winning_team_data = None
    
    team_data = {}
    sorted_teams = []
    max_mass = 1
    
    # --- Time and FPS variables ---
    total_play_time = 0  # Milliseconds
    last_frame_ticks = pygame.time.get_ticks()
    fps = 0
    
    running = True
    try:
        while running:
            # --- Delta time calculation ---
            current_ticks = pygame.time.get_ticks()
            dt_ms = current_ticks - last_frame_ticks
            last_frame_ticks = current_ticks

            # --- Event Handling (Runs in all states) ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # Global key presses (work in any game state)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    if event.key == pygame.K_r:
                        main()  # Restart
                        return
                    if event.key == pygame.K_p:
                        # Toggle pause state
                        if game_state == "playing":
                            game_state = "paused"
                        elif game_state == "paused":
                            game_state = "playing"


            # --- Game State Logic (Only if playing) ---
            if game_state == "playing":
                # --- Increment active play time ---
                total_play_time += dt_ms

                # 1. Spawn new food
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
                            continue
                        if player_a == player_b: # allow friendly fire by not considering the player's team
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
                    team_data[i] = {'mass': 0, 'player_count': 0, 'color': tuple(colors[i])}

                for player in players:
                    team_data[player.team_id]['mass'] += player.mass
                    team_data[player.team_id]['player_count'] += 1
                
                max_mass = max(1, *[data['mass'] for data in team_data.values()])
                sorted_teams = sorted(team_data.items(), key=lambda item: item[1]['mass'], reverse=True)

                # --- Win Condition Check ---
                active_team_count = 0
                last_active_team_id = -1
                for team_id, data in team_data.items():
                    if data['player_count'] > 0:
                        active_team_count += 1
                        last_active_team_id = team_id
                
                if active_team_count == 1:
                    game_state = "victory"
                    winning_team_data = team_data[last_active_team_id]
                    winning_team_data['id'] = last_active_team_id
                elif active_team_count == 0:
                    game_state = "victory"
                    winning_team_data = {'id': 'No one', 'color': (200, 200, 200), 'mass': 0}


            # --- Drawing (Runs in ALL states) ---
            # Draws the "frozen" game board when paused or victory
            
            screen.fill(BACKGROUND_COLOR)
            
            for pellet in food_pellets:
                pellet.draw(screen)
                
            for player in sorted(players, key=lambda p: p.mass):
                player.draw(screen)
                
            # --- Draw Scoreboard ---
            scoreboard_rect = pygame.Rect(SCREEN_WIDTH, 0, SCOREBOARD_WIDTH, SCREEN_HEIGHT)
            pygame.draw.rect(screen, SCOREBOARD_BG_COLOR, scoreboard_rect)
            pygame.draw.line(screen, DIVIDER_COLOR, (SCREEN_WIDTH, 0), (SCREEN_WIDTH, SCREEN_HEIGHT), 2)
            
            title_surface = font_title.render("Leaderboard", True, TEXT_COLOR_LIGHT)
            # --- UPDATED: Moved title down to make room for FPS/Timer ---
            screen.blit(title_surface, (SCREEN_WIDTH + (SCOREBOARD_WIDTH - title_surface.get_width()) // 2, 50))
            
            # --- UPDATED: Pushed team list down to follow title ---
            y_offset = 80 
            bar_max_width = SCOREBOARD_WIDTH - 20
            bar_height = 10
            entry_height = 55
            
            for i, (team_id, data) in enumerate(sorted_teams):
                if data['player_count'] == 0 and data['mass'] == 0:
                    continue
                    
                current_y = y_offset + i * entry_height
                color = data['color']
                
                team_text = f"Team {team_id} ({data['player_count']} players)"
                team_surface = font_main.render(team_text, True, color)
                screen.blit(team_surface, (SCREEN_WIDTH + 10, current_y))
                
                mass_text = f"Mass: {data['mass']:,.0f}"
                mass_surface = font_small.render(mass_text, True, TEXT_COLOR_MUTED)
                screen.blit(mass_surface, (SCREEN_WIDTH + 10, current_y + 20))
                
                bar_width_proportional = (data['mass'] / max_mass) * bar_max_width
                
                pygame.draw.rect(screen, BAR_BG_COLOR, (SCREEN_WIDTH + 10, current_y + 40, bar_max_width, bar_height))
                pygame.draw.rect(screen, color, (SCREEN_WIDTH + 10, current_y + 40, bar_width_proportional, bar_height))
            
            
            # --- Overlays (Pause or Victory) ---
            
            if game_state == "victory":
                # Create a semi-transparent overlay
                overlay = pygame.Surface((TOTAL_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill(VICTORY_OVERLAY_COLOR)
                screen.blit(overlay, (0, 0))
                
                # Draw Victory Text
                win_color = winning_team_data['color']
                win_id = winning_team_data['id']
                win_mass = winning_team_data['mass']
                
                title_text = "VICTORY!" if win_id != 'No one' else "DRAW!"
                title_surf = font_large.render(title_text, True, win_color)
                title_rect = title_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 - 80))
                screen.blit(title_surf, title_rect)

                if win_id != 'No one':
                    team_surf = font_medium.render(f"Team {win_id} Wins!", True, TEXT_COLOR_LIGHT)
                    team_rect = team_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2))
                    screen.blit(team_surf, team_rect)
                
                    mass_surf = font_medium.render(f"Final Mass: {win_mass:,.0f}", True, TEXT_COLOR_MUTED)
                    mass_rect = mass_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 50))
                    screen.blit(mass_surf, mass_rect)

                    # --- Display final time ---
                    total_seconds_win = total_play_time // 1000
                    minutes_win = total_seconds_win // 60
                    seconds_win = total_seconds_win % 60
                    time_win_str = f"Final Time: {minutes_win:02}:{seconds_win:02}"
                    
                    time_surf = font_medium.render(time_win_str, True, TEXT_COLOR_MUTED)
                    time_rect = time_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 100))
                    screen.blit(time_surf, time_rect)
                
                # --- Adjusted y-position ---
                prompt_surf = font_main.render("Press 'R' to Restart or 'Q' to Quit", True, TEXT_COLOR_LIGHT)
                prompt_rect = prompt_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 150))
                screen.blit(prompt_surf, prompt_rect)

            elif game_state == "paused":
                # Create a semi-transparent overlay
                overlay = pygame.Surface((TOTAL_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill(VICTORY_OVERLAY_COLOR) # Re-using the same overlay color
                screen.blit(overlay, (0, 0))
                
                # Draw "PAUSED" text
                pause_surf = font_large.render("PAUSED", True, TEXT_COLOR_LIGHT)
                pause_rect = pause_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 - 40))
                screen.blit(pause_surf, pause_rect)
                
                prompt_surf = font_main.render("Press 'P' to Resume", True, TEXT_COLOR_LIGHT)
                prompt_rect = prompt_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 40))
                screen.blit(prompt_surf, prompt_rect)

            # --- Draw FPS and Timer on top of everything ---
            # (This location is now clear)
            
            # Draw FPS
            fps_text = f"FPS: {fps:.0f}"
            fps_surf = font_small.render(fps_text, True, TEXT_COLOR_MUTED)
            fps_rect = fps_surf.get_rect(topright=(TOTAL_WIDTH - 10, 10))
            screen.blit(fps_surf, fps_rect)
            
            # Draw Timer
            total_seconds = total_play_time // 1000
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            time_str = f"Time: {minutes:02}:{seconds:02}"
            
            time_surf = font_small.render(time_str, True, TEXT_COLOR_MUTED)
            time_rect = time_surf.get_rect(topright=(TOTAL_WIDTH - 10, 30))
            screen.blit(time_surf, time_rect)


            # Update the display
            pygame.display.flip()

            # Cap the framerate
            clock.tick(60)
            
            # --- Get FPS for next frame's draw ---
            fps = clock.get_fps()
            
    finally:
        pygame.quit()

# --- Run the Game ---
if __name__ == "__main__":
    main()