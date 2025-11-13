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
CURSOR_BLINK_RATE = 500 # Milliseconds

# --- Helper Functions ---
def get_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

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

def parse_speed_input(input_str):
    """Tries to parse float from string, validates, and returns new speed and formatted text."""
    try:
        if not input_str: # Handle empty string
            return 1.0, "1"
        
        speed = float(input_str)
        
        if speed < 0:
            # Don't accept negative, reset to default
            return 1.0, "1"
        
        if speed.is_integer():
            return speed, f"{int(speed)}" # e.g., 2.0 -> "2"
        else:
            return speed, f"{speed}" # e.g., 1.5 -> "1.5"
            
    except ValueError:
        # Invalid input (e.g., "1.a.2" or "1.2.3" or ".")
        # Reset to default
        return 1.0, "1"

def get_cursor_pos_from_click(font, text, click_x, box_inner_x):
    """Finds the text index for a mouse click."""
    relative_click_x = click_x - box_inner_x
    
    # Find the width of each substring
    widths = [font.size(text[:i])[0] for i in range(len(text) + 1)]
    
    # Find where the click lands
    for i in range(len(widths)):
        if i == len(widths) - 1:
            # Click is past the end of the text
            return len(text)
            
        # Find the midpoint between this char's end and the next char's end
        midpoint = (widths[i] + widths[i+1]) / 2
        
        if relative_click_x < midpoint:
            return i
            
    return len(text) # Fallback


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

    def move(self, game_speed):
        # Apply game_speed to AI decision timer
        self.move_timer -= 1 * game_speed
        
        if self.move_timer <= 0:
            self.move_timer = random.randint(30, 90)
            angle = random.uniform(0, 2 * math.pi)
            self.dx = math.cos(angle)
            self.dy = math.sin(angle)
            
        # Apply game_speed to movement
        self.x += self.dx * self.speed * game_speed
        self.y += self.dy * self.speed * game_speed
        
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
    
    # --- Game speed and input box variables ---
    game_speed = 1.0
    input_text = "1" 
    input_active = False
    input_box_rect = pygame.Rect(SCREEN_WIDTH + 10, SCREEN_HEIGHT - 40, SCOREBOARD_WIDTH - 20, 30)
    # --- Cursor variables ---
    cursor_pos = len(input_text)
    cursor_timer = 0
    cursor_visible = True
    
    running = True
    try:
        while running:
            # --- Delta time calculation ---
            current_ticks = pygame.time.get_ticks()
            dt_ms = current_ticks - last_frame_ticks
            last_frame_ticks = current_ticks

            # --- Update cursor blink timer ---
            if input_active:
                cursor_timer += dt_ms
                if cursor_timer >= CURSOR_BLINK_RATE:
                    cursor_timer = 0
                    cursor_visible = not cursor_visible

            # --- Event Handling (Runs in all states) ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                # --- Handle clicking on/off the input box ---
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if input_box_rect.collidepoint(event.pos):
                        input_active = True
                        # --- Set cursor position based on click ---
                        cursor_pos = get_cursor_pos_from_click(font_small, input_text, event.pos[0], input_box_rect.x + 5)
                        cursor_timer = 0
                        cursor_visible = True
                    else:
                        if input_active:
                            # User clicked away, parse the input
                            game_speed, input_text = parse_speed_input(input_text)
                            cursor_pos = len(input_text) # Move cursor to end
                        input_active = False

                if event.type == pygame.KEYDOWN:
                    # Global key presses (work in any game state)
                    if event.key == pygame.K_q:
                        running = False
                    if event.key == pygame.K_r:
                        main()  # Restart
                        return
                    
                    # --- Handle input box typing ---
                    if input_active:
                        # Reset cursor blink on any keypress
                        cursor_timer = 0
                        cursor_visible = True

                        if event.key == pygame.K_RETURN:
                            game_speed, input_text = parse_speed_input(input_text)
                            input_active = False
                            cursor_pos = len(input_text)
                        elif event.key == pygame.K_BACKSPACE:
                            if cursor_pos > 0:
                                input_text = input_text[:cursor_pos-1] + input_text[cursor_pos:]
                                cursor_pos -= 1
                        elif event.key == pygame.K_DELETE:
                            input_text = input_text[:cursor_pos] + input_text[cursor_pos+1:]
                        elif event.key == pygame.K_LEFT:
                            cursor_pos = max(0, cursor_pos - 1)
                        elif event.key == pygame.K_RIGHT:
                            cursor_pos = min(len(input_text), cursor_pos + 1)
                        else:
                            # Add typed character if it's valid
                            char = event.unicode
                            if char.isdigit() or (char == '.' and '.' not in input_text):
                                input_text = input_text[:cursor_pos] + char + input_text[cursor_pos:]
                                cursor_pos += 1
                    else:
                        # Only handle pause key if NOT typing
                        if event.key == pygame.K_p:
                            # Toggle pause state
                            if game_state == "playing":
                                game_state = "paused"
                            elif game_state == "paused":
                                game_state = "playing"


            # --- Game State Logic (Only if playing) ---
            if game_state == "playing":
                # Apply game_speed to active play time
                total_play_time += dt_ms * game_speed

                # Apply game_speed to food spawn rate
                if random.random() < (FOOD_SPAWN_RATE * game_speed) and len(food_pellets) < MAX_FOOD:
                    fx = random.randint(0, SCREEN_WIDTH)
                    fy = random.randint(0, SCREEN_HEIGHT)
                    food_pellets.append(Food(fx, fy))

                # Pass game_speed to player move
                for player in players:
                    player.move(game_speed)

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
                        if player_a == player_b: 
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
            screen.blit(title_surface, (SCREEN_WIDTH + (SCOREBOARD_WIDTH - title_surface.get_width()) // 2, 50))
            
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
            

            # --- Draw Game Speed Input Box ---
            label_surf = font_small.render("Game Speed (x):", True, TEXT_COLOR_MUTED)
            screen.blit(label_surf, (input_box_rect.x, input_box_rect.y - 18))
            
            box_color = TEXT_COLOR_LIGHT if input_active else TEXT_COLOR_MUTED
            pygame.draw.rect(screen, box_color, input_box_rect, 2)
            
            text_surface = font_small.render(input_text, True, TEXT_COLOR_LIGHT)
            screen.blit(text_surface, (input_box_rect.x + 5, input_box_rect.y + 7))

            # --- Draw the cursor ---
            if input_active and cursor_visible:
                # Calculate cursor x position
                cursor_x_offset = font_small.size(input_text[:cursor_pos])[0]
                cursor_x = input_box_rect.x + 5 + cursor_x_offset
                cursor_y_start = input_box_rect.y + 5
                cursor_y_end = input_box_rect.y + input_box_rect.height - 5
                pygame.draw.line(screen, TEXT_COLOR_LIGHT, (cursor_x, cursor_y_start), (cursor_x, cursor_y_end), 2)

            
            # --- Overlays (Pause or Victory) ---
            if game_state == "victory":
                overlay = pygame.Surface((TOTAL_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill(VICTORY_OVERLAY_COLOR)
                screen.blit(overlay, (0, 0))
                
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

                    # --- Victory time formatting to show MM:SS.s ---
                    total_play_seconds_float_win = total_play_time / 1000.0
                    minutes_win = int(total_play_seconds_float_win) // 60
                    seconds_with_decimal_win = total_play_seconds_float_win % 60
                    # Use :04.1f for seconds to get format like 07.1
                    time_win_str = f"Final Time: {minutes_win:02}:{seconds_with_decimal_win:04.1f}"
                    
                    time_surf = font_medium.render(time_win_str, True, TEXT_COLOR_MUTED)
                    time_rect = time_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 100))
                    screen.blit(time_surf, time_rect)
                
                prompt_surf = font_main.render("Press 'R' to Restart or 'Q' to Quit", True, TEXT_COLOR_LIGHT)
                prompt_rect = prompt_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 150))
                screen.blit(prompt_surf, prompt_rect)

            elif game_state == "paused":
                overlay = pygame.Surface((TOTAL_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill(VICTORY_OVERLAY_COLOR) 
                screen.blit(overlay, (0, 0))
                
                pause_surf = font_large.render("PAUSED", True, TEXT_COLOR_LIGHT)
                pause_rect = pause_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 - 40))
                screen.blit(pause_surf, pause_rect)
                
                prompt_surf = font_main.render("Press 'P' to Resume", True, TEXT_COLOR_LIGHT)
                prompt_rect = prompt_surf.get_rect(center=(TOTAL_WIDTH / 2, SCREEN_HEIGHT / 2 + 40))
                screen.blit(prompt_surf, prompt_rect)

            # --- Draw FPS and Timer on top of everything ---
            
            # FPS formatting to 1 decimal place
            fps_text = f"FPS: {fps:.1f}"
            fps_surf = font_small.render(fps_text, True, TEXT_COLOR_MUTED)
            fps_rect = fps_surf.get_rect(topright=(TOTAL_WIDTH - 10, 10))
            screen.blit(fps_surf, fps_rect)
            
            # --- Timer formatting to show MM:SS.s ---
            total_play_seconds_float = total_play_time / 1000.0
            minutes = int(total_play_seconds_float) // 60
            seconds_with_decimal = total_play_seconds_float % 60
            
            # Use :04.1f for seconds to get format like 07.1 or 12.3
            time_str = f"Time: {int(minutes):02}:{seconds_with_decimal:04.1f}"
            
            time_surf = font_small.render(time_str, True, TEXT_COLOR_MUTED)
            time_rect = time_surf.get_rect(topright=(TOTAL_WIDTH - 10, 30))
            screen.blit(time_surf, time_rect)


            # Update the display
            pygame.display.flip()

            # Cap the framerate
            clock.tick(60)
            
            # Get FPS for next frame's draw
            fps = clock.get_fps()
            
    finally:
        pygame.quit()

# --- Run the Game ---
if __name__ == "__main__":
    main()