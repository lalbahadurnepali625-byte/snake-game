import base64
import io
import json
import os
import random
import socket
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout


# ============================================================
# CONFIGURATION
# ============================================================

GAME_WIDTH = 500
GAME_HEIGHT = 500
BLOCK_SIZE = 20

BACKGROUND_COLOR = "#000000"
PLAYER1_COLOR = "#008000"
PLAYER2_COLOR = "#0000FF"

INITIAL_SNAKE_LENGTH = 3
INITIAL_SPEED = 200

SPEED_INCREASE_SCORE = 10
SPEED_INCREASE_PERCENT = 10

PORT = 5000

BGM_DEFAULT_VOLUME = 0.50

MAX_NAME_LENGTH = 20

ROOT_BG = "#151515"
PANEL_BG = "#252525"
BUTTON_BG = "#303030"
TEXT_COLOR = "#FFFFFF"
MUTED_COLOR = "#AAAAAA"
RED = "#FF4D4D"
GREEN = "#63D297"


# ============================================================
# HELPERS
# ============================================================

def hex_to_rgba(value, alpha=1):
    value = value.lstrip("#")

    if len(value) == 3:
        value = "".join(c * 2 for c in value)

    try:
        return (
            int(value[0:2], 16) / 255.0,
            int(value[2:4], 16) / 255.0,
            int(value[4:6], 16) / 255.0,
            alpha,
        )
    except Exception:
        return (0, 0, 0, alpha)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


# ============================================================
# BACKGROUND / SNAKE DRAWING
# ============================================================

class GameBoard(Widget):
    """
    Kivy replacement for the old Tkinter Canvas.

    Coordinates inside the board are kept identical to the original
    game: 0..500 in both directions.
    """

    snakes = {}
    foods = []
    gap_food = None

    background_color_value = BACKGROUND_COLOR
    background_texture = None

    snake_colors = {
        "1": PLAYER1_COLOR,
        "2": PLAYER2_COLOR,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (GAME_WIDTH, GAME_HEIGHT)

        self.bind(pos=self.redraw, size=self.redraw)
        Clock.schedule_once(lambda *_: self.redraw(), 0)

    def board_to_screen(self, x, y):
        sx = self.x + x
        sy = self.y + (GAME_HEIGHT - y - BLOCK_SIZE)
        return sx, sy

    def redraw(self, *_):
        self.canvas.before.clear()

        with self.canvas.before:

            # ------------------------------------------------
            # Background
            # ------------------------------------------------
            if self.background_texture is not None:
                Color(1, 1, 1, 1)
                Rectangle(
                    texture=self.background_texture,
                    pos=self.pos,
                    size=self.size,
                )
            else:
                Color(*hex_to_rgba(self.background_color_value))
                Rectangle(
                    pos=self.pos,
                    size=self.size,
                )

            # ------------------------------------------------
            # Food
            # ------------------------------------------------
            for food in self.foods:
                if not isinstance(food, (list, tuple)) or len(food) < 2:
                    continue

                x, y = food[:2]
                sx, sy = self.board_to_screen(x, y)

                Color(1, 0, 0, 1)
                Ellipse(
                    pos=(sx + 2, sy + 2),
                    size=(BLOCK_SIZE - 4, BLOCK_SIZE - 4),
                )

            # ------------------------------------------------
            # Gap food
            # ------------------------------------------------
            if self.gap_food:
                try:
                    x, y = self.gap_food[:2]
                    sx, sy = self.board_to_screen(x, y)

                    Color(1, 0.65, 0, 1)
                    Ellipse(
                        pos=(sx + 1, sy + 1),
                        size=(BLOCK_SIZE - 2, BLOCK_SIZE - 2),
                    )

                    Color(1, 1, 0, 1)
                    Line(
                        circle=(
                            sx + BLOCK_SIZE / 2,
                            sy + BLOCK_SIZE / 2,
                            BLOCK_SIZE / 2 - 2,
                        ),
                        width=2,
                    )
                except Exception:
                    pass

            # ------------------------------------------------
            # Snakes
            # ------------------------------------------------
            for player_id in ("1", "2"):
                snake = self.snakes.get(player_id, [])

                if not snake:
                    continue

                color = self.snake_colors.get(
                    player_id,
                    PLAYER1_COLOR if player_id == "1" else PLAYER2_COLOR,
                )

                self.draw_snake(snake, color)

        self.canvas.after.clear()

    def draw_snake(self, snake, color):
        rgba = hex_to_rgba(color)

        # Body
        for i in range(len(snake) - 1, 0, -1):
            try:
                x1, y1 = snake[i]
                x2, y2 = snake[i - 1]
            except Exception:
                continue

            sx1, sy1 = self.board_to_screen(x1, y1)
            sx2, sy2 = self.board_to_screen(x2, y2)

            cx1 = sx1 + BLOCK_SIZE / 2
            cy1 = sy1 + BLOCK_SIZE / 2
            cx2 = sx2 + BLOCK_SIZE / 2
            cy2 = sy2 + BLOCK_SIZE / 2

            width = 16

            if len(snake) >= 3:
                if i == len(snake) - 1:
                    width = 5
                elif i == len(snake) - 2:
                    width = 10
            elif i == len(snake) - 1:
                width = 7

            Color(*rgba)

            Line(
                points=(cx1, cy1, cx2, cy2),
                width=width,
                cap="round",
            )

            Ellipse(
                pos=(
                    cx1 - width / 2,
                    cy1 - width / 2,
                ),
                size=(width, width),
            )

        # Head
        hx, hy = snake[0]
        hsx, hsy = self.board_to_screen(hx, hy)

        head_cx = hsx + BLOCK_SIZE / 2
        head_cy = hsy + BLOCK_SIZE / 2

        Color(*rgba)
        Ellipse(
            pos=(head_cx - 13, head_cy - 13),
            size=(26, 26),
        )

        # Determine head direction
        if len(snake) >= 2:
            sx, sy = snake[1]
            dx = hx - sx
            dy = hy - sy
        else:
            dx = BLOCK_SIZE
            dy = 0

        # Eyes
        Color(1, 1, 1, 1)

        if dx > 0:
            eyes = [
                (head_cx + 5, head_cy + 5),
                (head_cx + 5, head_cy - 5),
            ]
        elif dx < 0:
            eyes = [
                (head_cx - 5, head_cy + 5),
                (head_cx - 5, head_cy - 5),
            ]
        elif dy < 0:
            eyes = [
                (head_cx - 5, head_cy - 5),
                (head_cx + 5, head_cy - 5),
            ]
        else:
            eyes = [
                (head_cx - 5, head_cy + 5),
                (head_cx + 5, head_cy + 5),
            ]

        for ex, ey in eyes:
            Ellipse(
                pos=(ex - 3.5, ey - 3.5),
                size=(7, 7),
            )

            Color(0, 0, 0, 1)
            Ellipse(
                pos=(ex - 1.7, ey - 1.7),
                size=(3.4, 3.4),
            )


# ============================================================
# MOBILE CONTROL BUTTON
# ============================================================

class ControlButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_normal = ""
        self.background_down = ""
        self.background_color = hex_to_rgba("#303030", 0.90)

        self.color = (1, 1, 1, 1)
        self.font_size = "25sp"
        self.bold = True

        self.size_hint = (None, None)
        self.size = (82, 70)


# ============================================================
# GAME SCREEN
# ============================================================

class GameScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.board = None

        # ----------------------------------------------------
        # Root
        # ----------------------------------------------------
        root = BoxLayout(
            orientation="vertical",
            spacing=3,
            padding=3,
        )

        # ----------------------------------------------------
        # HUD
        # ----------------------------------------------------
        self.hud = GridLayout(
            cols=3,
            size_hint_y=None,
            height=55,
            spacing=3,
        )

        self.p1_label = Label(
            text="P1: Player 1\nScore: 0 | 200ms",
            font_size="12sp",
            color=(1, 1, 1, 1),
        )

        self.center_label = Label(
            text="SNAKE",
            font_size="16sp",
            bold=True,
            color=(1, 1, 1, 1),
        )

        self.p2_label = Label(
            text="P2: Player 2\nScore: 0 | 200ms",
            font_size="12sp",
            color=(1, 1, 1, 1),
        )

        self.hud.add_widget(self.p1_label)
        self.hud.add_widget(self.center_label)
        self.hud.add_widget(self.p2_label)

        root.add_widget(self.hud)

        # ----------------------------------------------------
        # Game area
        # ----------------------------------------------------
        game_area = FloatLayout()

        self.board = GameBoard(
            size=(GAME_WIDTH, GAME_HEIGHT),
        )

        # Center board
        self.board.pos_hint = {
            "center_x": 0.5,
            "center_y": 0.5,
        }

        game_area.add_widget(self.board)

        # ----------------------------------------------------
        # Pause button - top left
        # ----------------------------------------------------
        self.pause_button = ControlButton(
            text="Ⅱ",
            size=(62, 55),
            size_hint=(None, None),
            pos_hint={
                "x": 0.01,
                "top": 0.98,
            },
        )

        self.pause_button.bind(on_release=self.on_pause_button)
        game_area.add_widget(self.pause_button)

        # ----------------------------------------------------
        # LEFT MOBILE CONTROLS
        # W / S
        # ----------------------------------------------------
        self.up_button = ControlButton(
            text="▲",
            size=(82, 70),
            size_hint=(None, None),
            pos_hint={
                "x": 0.015,
                "center_y": 0.58,
            },
        )

        self.down_button = ControlButton(
            text="▼",
            size=(82, 70),
            size_hint=(None, None),
            pos_hint={
                "x": 0.015,
                "center_y": 0.36,
            },
        )

        self.up_button.bind(on_release=lambda *_: self.change_direction("Up"))
        self.down_button.bind(on_release=lambda *_: self.change_direction("Down"))

        game_area.add_widget(self.up_button)
        game_area.add_widget(self.down_button)

        # ----------------------------------------------------
        # RIGHT MOBILE CONTROLS
        # A / D
        # ----------------------------------------------------
        self.left_button = ControlButton(
            text="◀",
            size=(82, 70),
            size_hint=(None, None),
            pos_hint={
                "right": 0.905,
                "center_y": 0.47,
            },
        )

        self.right_button = ControlButton(
            text="▶",
            size=(82, 70),
            size_hint=(None, None),
            pos_hint={
                "right": 0.995,
                "center_y": 0.47,
            },
        )

        self.left_button.bind(
            on_release=lambda *_: self.change_direction("Left")
        )

        self.right_button.bind(
            on_release=lambda *_: self.change_direction("Right")
        )

        game_area.add_widget(self.left_button)
        game_area.add_widget(self.right_button)

        # ----------------------------------------------------
        # Bottom status / hearts
        # ----------------------------------------------------
        self.bottom_label = Label(
            text="❤ ❤ ❤",
            size_hint=(1, None),
            height=35,
            font_size="18sp",
            color=(1, 0.2, 0.2, 1),
        )

        game_area.add_widget(
            self.bottom_label
        )

        root.add_widget(game_area)

        self.add_widget(root)

        Clock.schedule_interval(self.refresh_screen, 1 / 30)

    # ========================================================
    # DIRECTION
    # ========================================================

    def change_direction(self, direction):
        app = App.get_running_app()

        app.play_sound("click")

        if app.multiplayer_running:
            if app.paused.get(str(app.my_player), False):
                return

            app.send_message(
                {
                    "type": "direction",
                    "direction": direction,
                }
            )
        else:
            app.single_set_direction(direction)

    # ========================================================
    # PAUSE
    # ========================================================

    def on_pause_button(self, *_):
        app = App.get_running_app()
        app.play_sound("click")

        if app.multiplayer_running:
            app.toggle_multiplayer_pause()
        else:
            app.toggle_single_pause()

    # ========================================================
    # REFRESH
    # ========================================================

    def refresh_screen(self, *_):
        app = App.get_running_app()

        if not app.multiplayer_running and not app.single_running:
            return

        # ------------------------------
        # Single player
        # ------------------------------
        if app.single_running:
            self.board.snakes = {
                "1": list(app.single_snake),
                "2": [],
            }

            self.board.foods = (
                [app.single_food]
                if app.single_food is not None
                else []
            )

            self.board.gap_food = app.single_gap_food

            self.board.snake_colors = {
                "1": app.custom_snake_color,
                "2": PLAYER2_COLOR,
            }

            self.p1_label.text = (
                f"{app.player_name}\n"
                f"Score: {app.single_score} | "
                f"{app.single_speed}ms"
            )

            self.p2_label.text = ""

            lives = "❤ ❤ ❤"

            self.bottom_label.text = lives

            self.board.redraw()

            if app.single_game_over:
                self.center_label.text = "GAME OVER"
            elif app.single_paused:
                self.center_label.text = "PAUSED"
            else:
                self.center_label.text = "SNAKE"

            return

        # ------------------------------
        # Multiplayer
        # ------------------------------
        with app.state_lock:
            current_snakes = {
                key: list(value)
                for key, value in app.snakes.items()
            }

            current_food = list(app.food)
            current_gap = app.gap_food

            current_scores = dict(app.scores)
            current_speeds = dict(app.speeds)
            current_pings = dict(app.pings)
            current_names = dict(app.names)
            current_lives = dict(app.lives)
            current_alive = dict(app.alive)
            current_paused = dict(app.paused)
            current_started = app.game_started
            current_colors = dict(app.player_snake_colors)

        self.board.snakes = current_snakes
        self.board.foods = current_food
        self.board.gap_food = current_gap
        self.board.snake_colors = current_colors

        self.p1_label.text = (
            f"{current_names.get('1', 'Player 1')}\n"
            f"Score: {current_scores.get('1', 0)} | "
            f"{current_speeds.get('1', INITIAL_SPEED)}ms | "
            f"{current_pings.get('1', 0)}ms"
        )

        self.p2_label.text = (
            f"{current_names.get('2', 'Player 2')}\n"
            f"Score: {current_scores.get('2', 0)} | "
            f"{current_speeds.get('2', INITIAL_SPEED)}ms | "
            f"{current_pings.get('2', 0)}ms"
        )

        my_lives = current_lives.get(
            str(app.my_player),
            3,
        )

        self.bottom_label.text = (
            "❤ " * max(0, min(3, my_lives))
        ).strip()

        if not current_started:
            self.center_label.text = "WAITING"

        elif current_paused.get(str(app.my_player), False):
            self.center_label.text = "PAUSED"

        elif not current_alive.get(str(app.my_player), False):
            self.center_label.text = "YOU DIED"

        else:
            self.center_label.text = "SNAKE"

        self.board.redraw()


# ============================================================
# MAIN MENU
# ============================================================

class MenuScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            spacing=15,
            padding=35,
        )

        title = Label(
            text="SNAKE",
            font_size="42sp",
            bold=True,
            size_hint_y=None,
            height=70,
        )

        subtitle = Label(
            text="Snake Game",
            font_size="18sp",
            color=hex_to_rgba(MUTED_COLOR),
            size_hint_y=None,
            height=40,
        )

        self.name_input = TextInput(
            text="Player",
            hint_text="Player Name",
            multiline=False,
            font_size="18sp",
            size_hint_y=None,
            height=55,
            padding=(15, 15),
        )

        single = self.make_button(
            "SINGLE PLAYER",
            self.start_single,
        )

        multiplayer = self.make_button(
            "MULTIPLAYER",
            self.open_multiplayer,
        )

        settings = self.make_button(
            "SETTINGS",
            self.open_settings,
        )

        layout.add_widget(title)
        layout.add_widget(subtitle)
        layout.add_widget(self.name_input)
        layout.add_widget(single)
        layout.add_widget(multiplayer)
        layout.add_widget(settings)

        self.add_widget(layout)

    def make_button(self, text, callback):
        button = Button(
            text=text,
            font_size="18sp",
            size_hint_y=None,
            height=58,
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        button.bind(on_release=callback)

        return button

    def get_name(self):
        name = self.name_input.text.strip()

        if not name:
            name = "Player"

        return name[:MAX_NAME_LENGTH]

    def start_single(self, *_):
        app = App.get_running_app()
        app.player_name = self.get_name()
        app.start_single_player()

    def open_multiplayer(self, *_):
        app = App.get_running_app()
        app.player_name = self.get_name()

        self.manager.current = "multiplayer"

    def open_settings(self, *_):
        app = App.get_running_app()
        app.open_settings("menu")


# ============================================================
# MULTIPLAYER JOIN SCREEN
# ============================================================

class MultiplayerScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            spacing=12,
            padding=35,
        )

        title = Label(
            text="MULTIPLAYER",
            font_size="32sp",
            bold=True,
            size_hint_y=None,
            height=60,
        )

        ip_label = Label(
            text="Server IP Address",
            size_hint_y=None,
            height=35,
            font_size="16sp",
        )

        self.ip_input = TextInput(
            text="127.0.0.1",
            multiline=False,
            font_size="18sp",
            size_hint_y=None,
            height=55,
            padding=(15, 15),
        )

        name_label = Label(
            text="Player Name",
            size_hint_y=None,
            height=35,
            font_size="16sp",
        )

        self.name_input = TextInput(
            text="Player",
            multiline=False,
            font_size="18sp",
            size_hint_y=None,
            height=55,
            padding=(15, 15),
        )

        self.status = Label(
            text="",
            color=hex_to_rgba(MUTED_COLOR),
            size_hint_y=None,
            height=40,
            font_size="14sp",
        )

        join = Button(
            text="JOIN GAME",
            font_size="18sp",
            size_hint_y=None,
            height=60,
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        join.bind(on_release=self.join)

        back = Button(
            text="BACK",
            font_size="18sp",
            size_hint_y=None,
            height=55,
            background_normal="",
            background_color=hex_to_rgba("#252525"),
        )

        back.bind(
            on_release=lambda *_: setattr(
                self.manager,
                "current",
                "menu",
            )
        )

        layout.add_widget(title)
        layout.add_widget(ip_label)
        layout.add_widget(self.ip_input)
        layout.add_widget(name_label)
        layout.add_widget(self.name_input)
        layout.add_widget(self.status)
        layout.add_widget(join)
        layout.add_widget(back)

        self.add_widget(layout)

    def join(self, *_):
        app = App.get_running_app()

        ip = self.ip_input.text.strip()
        name = self.name_input.text.strip()

        if not ip:
            self.status.text = "Enter the server IP."
            self.status.color = hex_to_rgba(RED)
            return

        if not name:
            self.status.text = "Enter your player name."
            self.status.color = hex_to_rgba(RED)
            return

        app.player_name = name[:MAX_NAME_LENGTH]

        self.status.text = "Connecting..."
        self.status.color = hex_to_rgba(MUTED_COLOR)

        app.connect_multiplayer(ip, self.status)


# ============================================================
# SETTINGS SCREEN
# ============================================================

class SettingsScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.return_target = "menu"

        layout = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=25,
        )

        title = Label(
            text="SETTINGS",
            font_size="32sp",
            bold=True,
            size_hint_y=None,
            height=55,
        )

        layout.add_widget(title)

        # --------------------------------------------
        # Background colour
        # --------------------------------------------

        layout.add_widget(
            Label(
                text="Background Colour",
                size_hint_y=None,
                height=35,
            )
        )

        self.color_input = TextInput(
            text=BACKGROUND_COLOR,
            multiline=False,
            size_hint_y=None,
            height=50,
            font_size="16sp",
        )

        layout.add_widget(self.color_input)

        apply_background = Button(
            text="APPLY BACKGROUND COLOUR",
            size_hint_y=None,
            height=52,
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        apply_background.bind(
            on_release=self.apply_background
        )

        layout.add_widget(apply_background)

        # --------------------------------------------
        # Snake colour
        # --------------------------------------------

        layout.add_widget(
            Label(
                text="Your Snake Colour",
                size_hint_y=None,
                height=35,
            )
        )

        self.snake_color_input = TextInput(
            text=PLAYER1_COLOR,
            multiline=False,
            size_hint_y=None,
            height=50,
            font_size="16sp",
        )

        layout.add_widget(self.snake_color_input)

        apply_snake = Button(
            text="APPLY SNAKE COLOUR",
            size_hint_y=None,
            height=52,
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        apply_snake.bind(
            on_release=self.apply_snake
        )

        layout.add_widget(apply_snake)

        # --------------------------------------------
        # BGM
        # --------------------------------------------

        layout.add_widget(
            Label(
                text="BGM Volume",
                size_hint_y=None,
                height=35,
            )
        )

        self.volume = Slider(
            min=0,
            max=1,
            value=BGM_DEFAULT_VOLUME,
            size_hint_y=None,
            height=45,
        )

        self.volume.bind(
            value=self.change_volume
        )

        layout.add_widget(self.volume)

        self.mute_button = Button(
            text="MUTE BGM",
            size_hint_y=None,
            height=52,
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        self.mute_button.bind(
            on_release=self.toggle_mute
        )

        layout.add_widget(self.mute_button)

        # --------------------------------------------
        # Back
        # --------------------------------------------

        back = Button(
            text="BACK",
            size_hint_y=None,
            height=55,
            background_normal="",
            background_color=hex_to_rgba("#252525"),
        )

        back.bind(on_release=self.go_back)

        layout.add_widget(back)

        self.add_widget(layout)

    def apply_background(self, *_):
        app = App.get_running_app()

        value = self.color_input.text.strip()

        if not value.startswith("#"):
            value = "#" + value

        if len(value) not in (4, 7):
            return

        app.background_color = value

        if app.multiplayer_running:
            app.send_settings(
                background_mode="color",
                background_color_value=value,
            )

        if app.game_screen and app.game_screen.board:
            app.game_screen.board.background_color_value = value
            app.game_screen.board.redraw()

    def apply_snake(self, *_):
        app = App.get_running_app()

        value = self.snake_color_input.text.strip()

        if not value.startswith("#"):
            value = "#" + value

        if len(value) not in (4, 7):
            return

        app.custom_snake_color = value

        if app.multiplayer_running:
            player_key = str(app.my_player)

            if player_key in ("1", "2"):
                app.player_snake_colors[player_key] = value

                app.send_settings(
                    snake_color=value,
                )

        if app.game_screen and app.game_screen.board:
            app.game_screen.board.snake_colors[
                "1"
            ] = app.custom_snake_color

            app.game_screen.board.redraw()

    def change_volume(self, _, value):
        app = App.get_running_app()
        app.set_bgm_volume(value)

    def toggle_mute(self, *_):
        app = App.get_running_app()
        app.toggle_bgm_mute()

        self.mute_button.text = (
            "UNMUTE BGM"
            if app.bgm_muted
            else "MUTE BGM"
        )

    def go_back(self, *_):
        self.manager.current = self.return_target


# ============================================================
# PAUSE SCREEN
# ============================================================

class PauseScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            spacing=15,
            padding=40,
        )

        title = Label(
            text="PAUSED",
            font_size="38sp",
            bold=True,
            size_hint_y=None,
            height=70,
        )

        resume = Button(
            text="RESUME",
            size_hint_y=None,
            height=60,
            font_size="18sp",
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        settings = Button(
            text="SETTINGS",
            size_hint_y=None,
            height=60,
            font_size="18sp",
            background_normal="",
            background_color=hex_to_rgba(BUTTON_BG),
        )

        menu = Button(
            text="MAIN MENU",
            size_hint_y=None,
            height=60,
            font_size="18sp",
            background_normal="",
            background_color=hex_to_rgba("#252525"),
        )

        resume.bind(
            on_release=lambda *_: App.get_running_app().resume_game()
        )

        settings.bind(
            on_release=lambda *_: App.get_running_app().open_settings("pause")
        )

        menu.bind(
            on_release=lambda *_: App.get_running_app().leave_to_menu()
        )

        layout.add_widget(title)
        layout.add_widget(resume)
        layout.add_widget(settings)
        layout.add_widget(menu)

        self.add_widget(layout)


# ============================================================
# KIVY APPLICATION
# ============================================================

class SnakeApp(App):

    title = "Snake Game"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ----------------------------------------------------
        # Player
        # ----------------------------------------------------
        self.player_name = "Player"

        # ----------------------------------------------------
        # Multiplayer connection
        # ----------------------------------------------------
        self.client = None
        self.receive_thread = None
        self.multiplayer_running = False
        self.my_player = 0

        self.state_lock = threading.Lock()

        # ----------------------------------------------------
        # Multiplayer state
        # ----------------------------------------------------
        self.snakes = {
            "1": [],
            "2": [],
        }

        self.food = []
        self.gap_food = None

        self.lives = {
            "1": 3,
            "2": 3,
        }

        self.scores = {
            "1": 0,
            "2": 0,
        }

        self.speeds = {
            "1": INITIAL_SPEED,
            "2": INITIAL_SPEED,
        }

        self.pings = {
            "1": 0,
            "2": 0,
        }

        self.names = {
            "1": "Player 1",
            "2": "Player 2",
        }

        self.alive = {
            "1": False,
            "2": False,
        }

        self.ready = {
            "1": False,
            "2": False,
        }

        self.paused = {
            "1": False,
            "2": False,
        }

        self.game_started = False

        self.ping_id = 0
        self.ping_start_times = {}

        # ----------------------------------------------------
        # Single player
        # ----------------------------------------------------
        self.single_snake = []
        self.single_food = None
        self.single_gap_food = None

        self.single_normal_food_count = 0
        self.single_growth = 0

        self.single_direction = "Right"
        self.single_next_direction = "Right"

        self.single_score = 0
        self.single_speed = INITIAL_SPEED

        self.single_running = False
        self.single_paused = False
        self.single_game_over = False

        self.single_loop_event = None

        # ----------------------------------------------------
        # Appearance
        # ----------------------------------------------------
        self.background_color = BACKGROUND_COLOR

        self.player_snake_colors = {
            "1": PLAYER1_COLOR,
            "2": PLAYER2_COLOR,
        }

        self.custom_snake_color = PLAYER1_COLOR

        # ----------------------------------------------------
        # Audio
        # ----------------------------------------------------
        self.bgm_volume = BGM_DEFAULT_VOLUME
        self.bgm_muted = False

        self.sounds = {}
        self.bgm = None

        # ----------------------------------------------------
        # UI references
        # ----------------------------------------------------
        self.game_screen = None
        self.connection_status_label = None

    # ========================================================
    # BUILD
    # ========================================================

    def build(self):

        # Android landscape
        try:
            Window.rotation = 0
        except Exception:
            pass

        sm = ScreenManager()

        menu = MenuScreen(name="menu")
        multiplayer = MultiplayerScreen(name="multiplayer")
        settings = SettingsScreen(name="settings")
        pause = PauseScreen(name="pause")

        self.game_screen = GameScreen(name="game")

        sm.add_widget(menu)
        sm.add_widget(multiplayer)
        sm.add_widget(settings)
        sm.add_widget(pause)
        sm.add_widget(self.game_screen)

        self.load_audio()

        # Keyboard support for desktop testing
        Window.bind(
            on_key_down=self.on_keyboard_down
        )

        Clock.schedule_interval(
            self.multiplayer_ping_loop,
            1.0,
        )

        return sm

    # ========================================================
    # RESOURCE PATH
    # ========================================================

    def resource_path(self, filename):
        base = os.path.dirname(
            os.path.abspath(__file__)
        )

        return os.path.join(
            base,
            filename,
        )

    # ========================================================
    # AUDIO
    # ========================================================

    def load_audio(self):

        audio_names = [
            "click",
            "death",
            "eat",
            "eat_gap",
        ]

        for name in audio_names:
            path = self.resource_path(
                f"{name}.mp3"
            )

            if os.path.exists(path):
                try:
                    self.sounds[name] = SoundLoader.load(
                        path
                    )
                except Exception:
                    pass

        bgm_path = self.resource_path(
            "bgm.mp3"
        )

        if os.path.exists(bgm_path):
            try:
                self.bgm = SoundLoader.load(
                    bgm_path
                )

                if self.bgm:
                    self.bgm.loop = True
                    self.bgm.volume = self.bgm_volume

            except Exception:
                self.bgm = None

    def play_sound(self, name):

        sound = self.sounds.get(name)

        if sound:
            try:
                sound.stop()
                sound.play()
            except Exception:
                pass

    def start_bgm(self):

        if not self.bgm:
            return

        try:
            self.bgm.volume = (
                0
                if self.bgm_muted
                else self.bgm_volume
            )

            self.bgm.play()

        except Exception:
            pass

    def stop_bgm(self):

        if self.bgm:
            try:
                self.bgm.stop()
            except Exception:
                pass

    def set_bgm_volume(self, value):

        self.bgm_volume = clamp(
            float(value),
            0,
            1,
        )

        if self.bgm:

            try:
                self.bgm.volume = (
                    0
                    if self.bgm_muted
                    else self.bgm_volume
                )
            except Exception:
                pass

    def toggle_bgm_mute(self):

        self.bgm_muted = not self.bgm_muted

        if self.bgm:

            try:
                self.bgm.volume = (
                    0
                    if self.bgm_muted
                    else self.bgm_volume
                )
            except Exception:
                pass

    # ========================================================
    # KEYBOARD
    # ========================================================

    def on_keyboard_down(
        self,
        window,
        key,
        scancode,
        codepoint,
        modifiers,
    ):

        # Escape
        if key == 27:

            if self.multiplayer_running:
                self.toggle_multiplayer_pause()

            elif self.single_running:
                self.toggle_single_pause()

            return True

        # R = respawn
        if key in (ord("r"), ord("R")):

            if self.multiplayer_running:
                self.send_message(
                    {"type": "respawn"}
                )

            return True

        directions = {
            273: "Up",
            274: "Down",
            275: "Right",
            276: "Left",
        }

        if key in directions:

            direction = directions[key]

            if self.multiplayer_running:
                self.send_message(
                    {
                        "type": "direction",
                        "direction": direction,
                    }
                )

            elif self.single_running:
                self.single_set_direction(
                    direction
                )

            return True

        try:
            char = codepoint.lower()

            if char in ("w", "a", "s", "d"):

                direction = {
                    "w": "Up",
                    "s": "Down",
                    "a": "Left",
                    "d": "Right",
                }[char]

                if self.multiplayer_running:

                    self.send_message(
                        {
                            "type": "direction",
                            "direction": direction,
                        }
                    )

                elif self.single_running:

                    self.single_set_direction(
                        direction
                    )

                return True

        except Exception:
            pass

        return False

    # ========================================================
    # SINGLE PLAYER
    # ========================================================

    def calculate_single_speed(self):

        speed = INITIAL_SPEED

        steps = (
            self.single_score
            // SPEED_INCREASE_SCORE
        )

        for _ in range(steps):

            speed = int(
                speed
                * (
                    1
                    - SPEED_INCREASE_PERCENT
                    / 100
                )
            )

            if speed < 20:
                speed = 20
                break

        return speed

    def create_single_food(self):

        blocked = list(
            self.single_snake
        )

        if self.single_gap_food is not None:
            blocked.append(
                self.single_gap_food
            )

        possible = []

        for x in range(
            0,
            GAME_WIDTH,
            BLOCK_SIZE,
        ):

            for y in range(
                0,
                GAME_HEIGHT,
                BLOCK_SIZE,
            ):

                position = (
                    x,
                    y,
                )

                if position not in blocked:
                    possible.append(
                        position
                    )

        if possible:
            self.single_food = random.choice(
                possible
            )

    def create_single_gap_food(self):

        blocked = list(
            self.single_snake
        )

        if self.single_food is not None:
            blocked.append(
                self.single_food
            )

        possible = []

        for x in range(
            0,
            GAME_WIDTH,
            BLOCK_SIZE,
        ):

            for y in range(
                0,
                GAME_HEIGHT,
                BLOCK_SIZE,
            ):

                position = (
                    x,
                    y,
                )

                if position not in blocked:
                    possible.append(
                        position
                    )

        if possible:
            self.single_gap_food = random.choice(
                possible
            )

    def start_single_player(self):

        self.leave_multiplayer_silent()

        self.single_snake = [
            (100, 240),
            (80, 240),
            (60, 240),
        ]

        self.single_direction = "Right"
        self.single_next_direction = "Right"

        self.single_score = 0
        self.single_speed = INITIAL_SPEED

        self.single_food = None
        self.single_gap_food = None

        self.single_normal_food_count = 0
        self.single_growth = 0

        self.single_running = True
        self.single_paused = False
        self.single_game_over = False

        self.custom_snake_color = (
            self.player_snake_colors["1"]
        )

        self.create_single_food()

        self.start_bgm()

        self.root.current = "game"

        self.schedule_single_loop()

    def schedule_single_loop(self):

        if self.single_loop_event:
            try:
                self.single_loop_event.cancel()
            except Exception:
                pass

        self.single_loop_event = Clock.schedule_once(
            self.single_game_loop,
            self.single_speed / 1000.0,
        )

    def single_game_loop(self, *_):

        if not self.single_running:
            return

        if not self.single_paused:
            self.move_single_player()

        if (
            self.single_running
            and not self.single_game_over
        ):
            self.schedule_single_loop()

    def single_set_direction(self, direction):

        if not self.single_running:
            return

        if self.single_paused:
            return

        opposite = {
            "Up": "Down",
            "Down": "Up",
            "Left": "Right",
            "Right": "Left",
        }

        if (
            direction
            != opposite[
                self.single_direction
            ]
        ):

            self.single_next_direction = (
                direction
            )

    def move_single_player(self):

        self.single_direction = (
            self.single_next_direction
        )

        head_x, head_y = (
            self.single_snake[0]
        )

        if self.single_direction == "Up":
            head_y -= BLOCK_SIZE

        elif self.single_direction == "Down":
            head_y += BLOCK_SIZE

        elif self.single_direction == "Left":
            head_x -= BLOCK_SIZE

        elif self.single_direction == "Right":
            head_x += BLOCK_SIZE

        new_head = (
            head_x,
            head_y,
        )

        # Wall
        if (
            head_x < 0
            or head_x >= GAME_WIDTH
            or head_y < 0
            or head_y >= GAME_HEIGHT
        ):

            self.single_game_over = True
            self.play_sound("death")
            return

        # Self collision
        if new_head in self.single_snake:

            self.single_game_over = True
            self.play_sound("death")
            return

        self.single_snake.insert(
            0,
            new_head,
        )

        # Normal food
        if new_head == self.single_food:

            self.single_score += 1
            self.single_normal_food_count += 1
            self.single_growth += 1

            self.single_speed = (
                self.calculate_single_speed()
            )

            self.play_sound("eat")

            self.single_food = None
            self.create_single_food()

            if (
                self.single_normal_food_count >= 6
                and self.single_gap_food is None
            ):

                self.create_single_gap_food()
                self.single_normal_food_count = 0

        # Gap food
        elif new_head == self.single_gap_food:

            self.single_score += 2
            self.single_growth += 2

            self.single_speed = (
                self.calculate_single_speed()
            )

            self.play_sound("eat_gap")

            self.single_gap_food = None
            self.single_food = None

            self.create_single_food()

        # Growth
        elif self.single_growth > 0:

            self.single_growth -= 1

        else:

            self.single_snake.pop()

    def toggle_single_pause(self):

        if not self.single_running:
            return

        self.single_paused = not self.single_paused

        if self.single_paused:
            self.root.current = "pause"
        else:
            self.root.current = "game"
            self.schedule_single_loop()

    # ========================================================
    # MULTIPLAYER CONNECTION
    # ========================================================

    def connect_multiplayer(
        self,
        server_ip,
        status_label,
    ):

        def worker():

            try:

                new_client = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                )

                new_client.settimeout(8)

                new_client.connect(
                    (
                        server_ip,
                        PORT,
                    )
                )

                new_client.settimeout(None)

                new_client.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_NODELAY,
                    1,
                )

                self.client = new_client
                self.multiplayer_running = True

                Clock.schedule_once(
                    lambda *_: self.finish_multiplayer_connection(
                        status_label
                    )
                )

            except Exception as exc:

                Clock.schedule_once(
                    lambda *_: self.set_connection_error(
                        status_label,
                        str(exc),
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def finish_multiplayer_connection(
        self,
        status_label,
    ):

        status_label.text = (
            "Connected. Waiting for server..."
        )

        self.root.current = "game"

        self.receive_thread = threading.Thread(
            target=self.receive_data,
            daemon=True,
        )

        self.receive_thread.start()

        self.send_message(
            {
                "type": "name",
                "name": self.player_name,
            }
        )

        self.send_ping()

    def set_connection_error(
        self,
        status_label,
        error,
    ):

        status_label.text = (
            f"Connection failed:\n{error}"
        )

        status_label.color = hex_to_rgba(
            RED
        )

        self.multiplayer_running = False

        try:
            if self.client:
                self.client.close()
        except Exception:
            pass

        self.client = None

    # ========================================================
    # NETWORK SEND
    # ========================================================

    def send_message(self, data):

        if self.client is None:
            return

        try:

            message = (
                json.dumps(data)
                + "\n"
            )

            self.client.sendall(
                message.encode("utf-8")
            )

        except Exception:
            pass

    # ========================================================
    # NETWORK RECEIVE
    # ========================================================

    def receive_data(self):

        buffer = ""

        while self.multiplayer_running:

            try:

                data = self.client.recv(
                    4096
                )

                if not data:
                    break

                buffer += data.decode(
                    "utf-8",
                    errors="ignore",
                )

                while "\n" in buffer:

                    message, buffer = (
                        buffer.split(
                            "\n",
                            1,
                        )
                    )

                    if not message.strip():
                        continue

                    try:
                        packet = json.loads(
                            message
                        )
                    except json.JSONDecodeError:
                        continue

                    self.process_server_message(
                        packet
                    )

            except Exception:
                break

        if self.multiplayer_running:

            Clock.schedule_once(
                lambda *_:
                self.handle_multiplayer_disconnect()
            )

    # ========================================================
    # PROCESS SERVER MESSAGE
    # ========================================================

    def process_server_message(self, data):

        message_type = data.get(
            "type"
        )

        if message_type == "welcome":

            self.my_player = int(
                data.get(
                    "player",
                    data.get(
                        "id",
                        0,
                    ),
                )
            )

            return

        if message_type == "settings":

            new_background_mode = data.get(
                "background_mode",
                "color",
            )

            new_background_color = data.get(
                "background_color",
                BACKGROUND_COLOR,
            )

            new_background_image = data.get(
                "background_image"
            )

            new_snake_colors = data.get(
                "snake_colors"
            )

            self.background_color = (
                new_background_color
            )

            if isinstance(
                new_snake_colors,
                dict,
            ):

                with self.state_lock:

                    self.player_snake_colors[
                        "1"
                    ] = new_snake_colors.get(
                        "1",
                        PLAYER1_COLOR,
                    )

                    self.player_snake_colors[
                        "2"
                    ] = new_snake_colors.get(
                        "2",
                        PLAYER2_COLOR,
                    )

                    self.custom_snake_color = (
                        self.player_snake_colors.get(
                            str(self.my_player),
                            PLAYER1_COLOR,
                        )
                    )

            if (
                new_background_mode == "image"
                and new_background_image
            ):

                self.load_background_base64(
                    new_background_image
                )

            else:

                self.game_screen.board.background_texture = None

            return

        if message_type == "pong":

            ping_id_received = data.get(
                "id"
            )

            if (
                ping_id_received
                in self.ping_start_times
            ):

                elapsed = (
                    time.perf_counter()
                    - self.ping_start_times.pop(
                        ping_id_received
                    )
                )

                ping = int(
                    elapsed * 1000
                )

                self.send_message(
                    {
                        "type": "ping_result",
                        "ping": ping,
                    }
                )

            return

        if message_type == "sound":

            self.play_sound(
                data.get(
                    "sound",
                    "",
                )
            )

            return

        if message_type == "state":

            with self.state_lock:

                self.snakes = data.get(
                    "snakes",
                    self.snakes,
                )

                self.food = data.get(
                    "food",
                    self.food,
                )

                self.gap_food = data.get(
                    "gap_food",
                    self.gap_food,
                )

                self.lives = data.get(
                    "lives",
                    self.lives,
                )

                self.scores = data.get(
                    "scores",
                    self.scores,
                )

                self.speeds = data.get(
                    "speeds",
                    self.speeds,
                )

                self.pings = data.get(
                    "pings",
                    self.pings,
                )

                self.names = data.get(
                    "names",
                    self.names,
                )

                self.alive = data.get(
                    "alive",
                    self.alive,
                )

                self.ready = data.get(
                    "ready",
                    self.ready,
                )

                self.paused = data.get(
                    "paused",
                    self.paused,
                )

                self.game_started = data.get(
                    "started",
                    self.game_started,
                )

    # ========================================================
    # PING
    # ========================================================

    def send_ping(self):

        if not self.multiplayer_running:
            return

        self.ping_id += 1

        current_id = self.ping_id

        self.ping_start_times[
            current_id
        ] = time.perf_counter()

        self.send_message(
            {
                "type": "ping",
                "id": current_id,
            }
        )

    def multiplayer_ping_loop(self, *_):

        if self.multiplayer_running:
            self.send_ping()

    # ========================================================
    # MULTIPLAYER PAUSE
    # ========================================================

    def toggle_multiplayer_pause(self):

        if not self.multiplayer_running:
            return

        self.send_message(
            {
                "type": "pause"
            }
        )

    def resume_game(self):

        if self.multiplayer_running:

            if self.paused.get(
                str(self.my_player),
                False,
            ):

                self.send_message(
                    {
                        "type": "pause"
                    }
                )

            self.root.current = "game"

        elif self.single_running:

            self.single_paused = False
            self.root.current = "game"
            self.schedule_single_loop()

    # ========================================================
    # SETTINGS
    # ========================================================

    def send_settings(
        self,
        background_mode=None,
        background_color_value=None,
        background_image_value=None,
        snake_color=None,
    ):

        if not self.multiplayer_running:
            return

        data = {
            "type": "settings"
        }

        if background_mode is not None:
            data[
                "background_mode"
            ] = background_mode

        if background_color_value is not None:
            data[
                "background_color"
            ] = background_color_value

        if background_image_value is not None:
            data[
                "background_image"
            ] = background_image_value

        if snake_color is not None:
            data[
                "snake_color"
            ] = snake_color

        self.send_message(data)

    def load_background_base64(
        self,
        image_data,
    ):

        try:

            raw = base64.b64decode(
                image_data
            )

            data = io.BytesIO(raw)

            texture = CoreImage(
                data,
                ext="png",
            ).texture

            self.game_screen.board.background_texture = (
                texture
            )

            self.game_screen.board.redraw()

        except Exception as exc:

            print(
                "Background error:",
                exc,
            )

    def open_settings(
        self,
        return_target="menu",
    ):

        settings = self.root.get_screen(
            "settings"
        )

        settings.return_target = (
            return_target
        )

        self.root.current = "settings"

    # ========================================================
    # LEAVE / DISCONNECT
    # ========================================================

    def leave_multiplayer_silent(self):

        self.multiplayer_running = False

        try:
            if self.client:
                self.client.close()
        except Exception:
            pass

        self.client = None

    def handle_multiplayer_disconnect(self):

        if not self.multiplayer_running:
            return

        self.multiplayer_running = False

        try:
            if self.client:
                self.client.close()
        except Exception:
            pass

        self.client = None

        self.show_message(
            "Disconnected",
            "Disconnected from the multiplayer server.",
        )

        self.root.current = "menu"

    def leave_to_menu(self):

        if self.multiplayer_running:
            self.leave_multiplayer_silent()

        self.single_running = False
        self.single_paused = False

        self.stop_bgm()

        self.root.current = "menu"

    # ========================================================
    # MESSAGE POPUP
    # ========================================================

    def show_message(
        self,
        title,
        message,
    ):

        content = BoxLayout(
            orientation="vertical",
            spacing=10,
            padding=15,
        )

        label = Label(
            text=message,
        )

        button = Button(
            text="OK",
            size_hint_y=None,
            height=50,
        )

        content.add_widget(label)
        content.add_widget(button)

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.45),
        )

        button.bind(
            on_release=popup.dismiss
        )

        popup.open()

    # ========================================================
    # ANDROID BACK BUTTON
    # ========================================================

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    # ========================================================
    # STOP
    # ========================================================

    def on_stop(self):

        self.multiplayer_running = False
        self.single_running = False

        try:
            if self.client:
                self.client.close()
        except Exception:
            pass

        self.stop_bgm()


if __name__ == "__main__":
    SnakeApp().run()