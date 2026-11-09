"""Точка входу: `facetfall` або `python -m facetfall`."""

import argparse
import os
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="facetfall", description="Facetfall — geometric brick breaker")
    parser.add_argument("--lang", help="interface language: en, uk, pl, de, fr, es")
    parser.add_argument("--windowed", action="store_true", help="start in a window")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)

    from . import __version__
    if args.version:
        print(__version__)
        return 0

    # Ім'я вікна для доків GNOME/KDE (відповідає StartupWMClass у .desktop-файлі).
    os.environ.setdefault("SDL_VIDEO_X11_WMCLASS", "facetfall")
    os.environ.setdefault("SDL_VIDEO_WAYLAND_WMCLASS", "facetfall")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    import pygame

    from . import i18n
    from .game import H, W, run
    from .settings import Settings
    from .sound import Audio

    settings = Settings()
    lang = args.lang or settings["language"] or i18n.detect_system_language()
    i18n.set_language(lang)

    audio = Audio(enabled=settings["sound"])  # міксер ініціалізуємо до pygame.init()
    pygame.init()
    pygame.display.set_caption("Facetfall")
    icon = pygame.image.load(str(Path(__file__).with_name("icon.png")))
    pygame.display.set_icon(icon)

    flags = pygame.SCALED | pygame.RESIZABLE
    if settings["fullscreen"] and not args.windowed:
        flags |= pygame.FULLSCREEN
    screen = pygame.display.set_mode((W, H), flags, vsync=1)
    pygame.mouse.set_visible(False)

    try:
        run(screen, settings, audio)
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
