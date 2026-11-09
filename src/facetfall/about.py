"""Екран «Про гру» і відкриття посилання в браузері (зокрема з ізольованого snap)."""

import os
import shutil
import subprocess
import webbrowser

from . import AUTHOR, HOMEPAGE, __version__
from .i18n import _


def open_url(url):
    """Відкриває адресу в браузері. Повертає True, якщо запит вдалося передати системі.

    У snap-пакеті прямого доступу до браузера немає, тому спершу просимо систему
    через стандартний портал робочого столу (xdg-desktop-portal), далі — через
    обгортку xdg-open від snapd, і лише потім — звичайний модуль webbrowser.
    """
    attempts = []
    if shutil.which("gdbus"):
        attempts.append(["gdbus", "call", "--session",
                         "--dest", "org.freedesktop.portal.Desktop",
                         "--object-path", "/org/freedesktop/portal/desktop",
                         "--method", "org.freedesktop.portal.OpenURI.OpenURI",
                         "", url, "{}"])
    if shutil.which("xdg-open"):
        attempts.append(["xdg-open", url])
    for cmd in attempts:
        try:
            if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=10).returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            continue
    if os.environ.get("SNAP"):
        return False  # у snap webbrowser не має куди звернутися
    try:
        return webbrowser.open(url)
    except webbrowser.Error:
        return False


class About:
    """Стан екрана: повідомлення про результат відкриття посилання."""

    def __init__(self):
        self.status = None

    def activate(self, fullscreen):
        import pygame
        ok = open_url(HOMEPAGE)
        self.status = "ok" if ok else "fail"
        if ok and fullscreen:
            pygame.display.iconify()  # згортаємо гру, щоб було видно браузер

    def draw(self, game, w, h, colors):
        white, grey, yellow, red = colors
        game.text(_("About"), 56, yellow, center=(w // 2, 120))
        game.text(_("Version {v}").format(v=__version__), 28, grey, center=(w // 2, 180))
        game.text(_("Author: {name}").format(name=AUTHOR), 30, white, center=(w // 2, 240))
        game.text(_("License: MIT"), 26, grey, center=(w // 2, 280))
        game.text(_("Source code, bug reports and updates:"), 28, white, center=(w // 2, 360))
        game.text(HOMEPAGE, 30, yellow, center=(w // 2, 400))
        if self.status == "ok":
            game.text(_("Opened in your browser."), 26, (110, 255, 160), center=(w // 2, 460))
        elif self.status == "fail":
            game.text(_("Could not open the browser. Type the address manually."), 24, red,
                      center=(w // 2, 460))
        game.text(_("ENTER — open in browser    ESC — back"), 24, grey, center=(w // 2, h - 40))
