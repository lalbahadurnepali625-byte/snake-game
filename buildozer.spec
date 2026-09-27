[app]

# ------------------------------------------------------------
# BASIC INFORMATION
# ------------------------------------------------------------

title = Snake Game

package.name = snakegame

package.domain = org.snakegame

source.dir = .

source.include_exts = py,kv,png,jpg,jpeg,mp3,wav

version = 1.0

# ------------------------------------------------------------
# REQUIREMENTS
# ------------------------------------------------------------

requirements = python3,kivy,pillow

# ------------------------------------------------------------
# ANDROID
# ------------------------------------------------------------

orientation = landscape

fullscreen = 1

android.permissions = INTERNET

android.api = 34

android.minapi = 23

android.ndk = 27c

# ------------------------------------------------------------
# ANDROID APP SETTINGS
# ------------------------------------------------------------

android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = True

android.enable_androidx = True

# ------------------------------------------------------------
# SCREEN / DISPLAY
# ------------------------------------------------------------

# Landscape is required for the mobile control layout.

# ------------------------------------------------------------
# FILES
# ------------------------------------------------------------

# These files will be packaged if they exist:
#
# main.py
# snake_game.kv
# apple.png
# gap.png
# heart.png
# bgm.mp3
# click.mp3
# death.mp3
# eat.mp3
# eat_gap.mp3

# ------------------------------------------------------------
# BUILD
# ------------------------------------------------------------

[buildozer]

log_level = 2

warn_on_root = 1
