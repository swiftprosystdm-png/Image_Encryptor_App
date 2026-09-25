"""
theme_config.py - Clean, Modern & Elegant Theme Manager for Image Encryptor.

Provides a minimalist, polished Fluent/macOS-inspired aesthetic for both Dark and Light themes.
Includes crisp native icons for combobox drop-downs, spinbox arrows, and checkbox checkmarks.
"""

import os
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QPalette, QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import QApplication


def _resolve_resource(filename: str) -> str:
    """Resolve file path whether running in Python or PyInstaller frozen bundle."""
    if hasattr(sys, "_MEIPASS"):
        meipass_path = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(meipass_path):
            return meipass_path
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(exe_dir, filename)
        if os.path.exists(exe_path):
            return exe_path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, filename)
    if os.path.exists(script_path):
        return script_path
    return filename


ICO_PATH = _resolve_resource("Swift_Prosys.ico")
LOGO_PATH = _resolve_resource("Swift-ProSys-Logo.png")
LOGO_PREVIEW_PATH = _resolve_resource("Swift-ProSys-Logo-2026-1-removebg-preview.png")

DARK = "Dark"
LIGHT = "Light"

_ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_icons")
_ICON_VERSION = "realistic_v4"


def _ensure_icons() -> dict:
    """Generate crisp mathematical vector UI icons if not present or outdated."""
    os.makedirs(_ICONS_DIR, exist_ok=True)
    paths = {
        "arrow_down_dark": os.path.join(_ICONS_DIR, "arrow_down_dark.png"),
        "arrow_down_light": os.path.join(_ICONS_DIR, "arrow_down_light.png"),
        "arrow_up_dark": os.path.join(_ICONS_DIR, "arrow_up_dark.png"),
        "arrow_up_light": os.path.join(_ICONS_DIR, "arrow_up_light.png"),
        "check_white": os.path.join(_ICONS_DIR, "check_white.png"),
        "add_file_white": os.path.join(_ICONS_DIR, "add_file_white.png"),
        "add_folder": os.path.join(_ICONS_DIR, "add_folder.png"),
        "clear_trash": os.path.join(_ICONS_DIR, "clear_trash.png"),
        "folder_browse": os.path.join(_ICONS_DIR, "folder_browse.png"),
        "lock_white": os.path.join(_ICONS_DIR, "lock_white.png"),
        "lightning": os.path.join(_ICONS_DIR, "lightning.png"),
        "pause": os.path.join(_ICONS_DIR, "pause.png"),
        "play": os.path.join(_ICONS_DIR, "play.png"),
        "cancel_x": os.path.join(_ICONS_DIR, "cancel_x.png"),
        "moon": os.path.join(_ICONS_DIR, "moon.png"),
        "sun": os.path.join(_ICONS_DIR, "sun.png"),
    }

    ver_file = os.path.join(_ICONS_DIR, ".version")
    current_ver = ""
    if os.path.exists(ver_file):
        try:
            with open(ver_file, "r") as f:
                current_ver = f.read().strip()
        except Exception:
            current_ver = ""

    needs_generation = (current_ver != _ICON_VERSION) or not all(os.path.exists(p) for p in paths.values())

    if needs_generation:
        from PyQt6.QtCore import QRectF, QPointF
        from PyQt6.QtGui import QBrush, QFont, QPainter, QImage, QPen, QColor, QPainterPath, QLinearGradient, QRadialGradient

        # 1. add_file_white (Realistic 3D Document with Folded Corner and Blue Badge)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        doc_grad = QLinearGradient(16, 10, 48, 54)
        doc_grad.setColorAt(0.0, QColor("#ffffff"))
        doc_grad.setColorAt(0.8, QColor("#f1f5f9"))
        doc_grad.setColorAt(1.0, QColor("#e2e8f0"))
        p.setPen(QPen(QColor("#94a3b8"), 1.2))
        p.setBrush(QBrush(doc_grad))
        doc_path = QPainterPath()
        doc_path.moveTo(16, 10)
        doc_path.lineTo(38, 10)
        doc_path.lineTo(48, 20)
        doc_path.lineTo(48, 54)
        doc_path.lineTo(16, 54)
        doc_path.closeSubpath()
        p.drawPath(doc_path)

        flap_grad = QLinearGradient(38, 10, 48, 20)
        flap_grad.setColorAt(0.0, QColor("#e2e8f0"))
        flap_grad.setColorAt(1.0, QColor("#cbd5e1"))
        p.setBrush(QBrush(flap_grad))
        p.setPen(QPen(QColor("#94a3b8"), 1.0))
        flap_path = QPainterPath()
        flap_path.moveTo(38, 10)
        flap_path.lineTo(38, 20)
        flap_path.lineTo(48, 20)
        flap_path.closeSubpath()
        p.drawPath(flap_path)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#3b82f6")))
        p.drawRoundedRect(QRectF(21, 16, 14, 4), 1.5, 1.5)

        p.setPen(QPen(QColor("#94a3b8"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(21, 26, 43, 26)
        p.drawLine(21, 32, 43, 32)
        p.drawLine(21, 38, 35, 38)

        badge_grad = QLinearGradient(34, 34, 52, 52)
        badge_grad.setColorAt(0.0, QColor("#2563eb"))
        badge_grad.setColorAt(1.0, QColor("#1d4ed8"))
        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.setBrush(QBrush(badge_grad))
        p.drawEllipse(QRectF(34, 34, 18, 18))
        p.setPen(QPen(QColor("#ffffff"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(43, 38, 43, 48)
        p.drawLine(38, 43, 48, 43)
        p.end()
        img.save(paths["add_file_white"])

        # 2. add_folder (Realistic 3D Golden Manila Folder)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        back_grad = QLinearGradient(12, 16, 12, 52)
        back_grad.setColorAt(0.0, QColor("#d97706"))
        back_grad.setColorAt(1.0, QColor("#b45309"))
        p.setPen(QPen(QColor("#92400e"), 1.2))
        p.setBrush(QBrush(back_grad))
        back_path = QPainterPath()
        back_path.moveTo(12, 22)
        back_path.lineTo(24, 22)
        back_path.lineTo(29, 16)
        back_path.lineTo(52, 16)
        back_path.lineTo(52, 50)
        back_path.lineTo(12, 50)
        back_path.closeSubpath()
        p.drawPath(back_path)

        paper_grad = QLinearGradient(18, 18, 18, 38)
        paper_grad.setColorAt(0.0, QColor("#ffffff"))
        paper_grad.setColorAt(1.0, QColor("#e2e8f0"))
        p.setPen(QPen(QColor("#cbd5e1"), 1.0))
        p.setBrush(QBrush(paper_grad))
        p.drawRoundedRect(QRectF(17, 18, 30, 24), 2, 2)
        p.setPen(QPen(QColor("#94a3b8"), 1.2))
        p.drawLine(22, 24, 40, 24)
        p.drawLine(22, 28, 36, 28)

        front_grad = QLinearGradient(10, 26, 10, 52)
        front_grad.setColorAt(0.0, QColor("#fde047"))
        front_grad.setColorAt(0.15, QColor("#facc15"))
        front_grad.setColorAt(0.8, QColor("#eab308"))
        front_grad.setColorAt(1.0, QColor("#ca8a04"))
        p.setPen(QPen(QColor("#a16207"), 1.2))
        p.setBrush(QBrush(front_grad))
        front_path = QPainterPath()
        front_path.moveTo(10, 26)
        front_path.lineTo(54, 26)
        front_path.lineTo(48, 52)
        front_path.lineTo(10, 52)
        front_path.closeSubpath()
        p.drawPath(front_path)

        p.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
        p.drawLine(12, 27, 52, 27)

        badge_grad = QLinearGradient(34, 34, 52, 52)
        badge_grad.setColorAt(0.0, QColor("#2563eb"))
        badge_grad.setColorAt(1.0, QColor("#1d4ed8"))
        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.setBrush(QBrush(badge_grad))
        p.drawEllipse(QRectF(34, 34, 18, 18))
        p.setPen(QPen(QColor("#ffffff"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(43, 38, 43, 48)
        p.drawLine(38, 43, 48, 43)
        p.end()
        img.save(paths["add_folder"])

        # 3. clear_trash (Realistic 3D Crimson/Metallic Trash Bin)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(QPen(QColor("#94a3b8"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(27, 14, 37, 14)

        lid_grad = QLinearGradient(14, 18, 50, 22)
        lid_grad.setColorAt(0.0, QColor("#f87171"))
        lid_grad.setColorAt(0.5, QColor("#ef4444"))
        lid_grad.setColorAt(1.0, QColor("#b91c1c"))
        p.setPen(QPen(QColor("#991b1b"), 1.2))
        p.setBrush(QBrush(lid_grad))
        p.drawRoundedRect(QRectF(15, 18, 34, 6), 3, 3)

        body_grad = QLinearGradient(18, 24, 46, 52)
        body_grad.setColorAt(0.0, QColor("#ef4444"))
        body_grad.setColorAt(0.3, QColor("#f87171"))
        body_grad.setColorAt(0.7, QColor("#dc2626"))
        body_grad.setColorAt(1.0, QColor("#991b1b"))
        p.setPen(QPen(QColor("#7f1d1d"), 1.2))
        p.setBrush(QBrush(body_grad))
        body_path = QPainterPath()
        body_path.moveTo(19, 24)
        body_path.lineTo(45, 24)
        body_path.lineTo(41, 52)
        body_path.lineTo(23, 52)
        body_path.closeSubpath()
        p.drawPath(body_path)

        p.setPen(QPen(QColor(255, 255, 255, 120), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(27, 28, 28, 48)
        p.setPen(QPen(QColor(0, 0, 0, 60), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(32, 28, 32, 48)
        p.setPen(QPen(QColor(255, 255, 255, 120), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(37, 28, 36, 48)
        p.end()
        img.save(paths["clear_trash"])

        # 4. folder_browse (Realistic 3D Open Folder with Multi-Docs)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        back_grad = QLinearGradient(12, 16, 12, 50)
        back_grad.setColorAt(0.0, QColor("#0284c7"))
        back_grad.setColorAt(1.0, QColor("#0369a1"))
        p.setPen(QPen(QColor("#075985"), 1.2))
        p.setBrush(QBrush(back_grad))
        back_path = QPainterPath()
        back_path.moveTo(12, 22)
        back_path.lineTo(24, 22)
        back_path.lineTo(29, 16)
        back_path.lineTo(52, 16)
        back_path.lineTo(52, 48)
        back_path.lineTo(12, 48)
        back_path.closeSubpath()
        p.drawPath(back_path)

        p.setPen(QPen(QColor("#cbd5e1"), 1.0))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawRoundedRect(QRectF(18, 18, 28, 22), 2, 2)
        p.setBrush(QBrush(QColor("#f8fafc")))
        p.drawRoundedRect(QRectF(22, 22, 26, 20), 2, 2)

        front_grad = QLinearGradient(10, 30, 10, 52)
        front_grad.setColorAt(0.0, QColor("#38bdf8"))
        front_grad.setColorAt(0.5, QColor("#0ea5e9"))
        front_grad.setColorAt(1.0, QColor("#0284c7"))
        p.setPen(QPen(QColor("#0369a1"), 1.2))
        p.setBrush(QBrush(front_grad))
        front_path = QPainterPath()
        front_path.moveTo(10, 48)
        front_path.lineTo(19, 30)
        front_path.lineTo(54, 30)
        front_path.lineTo(46, 48)
        front_path.closeSubpath()
        p.drawPath(front_path)

        p.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
        p.drawLine(19, 31, 53, 31)
        p.end()
        img.save(paths["folder_browse"])

        # 5. lock_white (Realistic 3D Gold & Chrome Padlock)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        shackle_grad = QLinearGradient(20, 12, 44, 30)
        shackle_grad.setColorAt(0.0, QColor("#f8fafc"))
        shackle_grad.setColorAt(0.3, QColor("#cbd5e1"))
        shackle_grad.setColorAt(0.7, QColor("#64748b"))
        shackle_grad.setColorAt(1.0, QColor("#f1f5f9"))
        p.setPen(QPen(QBrush(shackle_grad), 5.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        shackle_path = QPainterPath()
        shackle_path.moveTo(23, 28)
        shackle_path.lineTo(23, 20)
        shackle_path.arcTo(23, 11, 18, 18, 180, -180)
        shackle_path.lineTo(41, 28)
        p.drawPath(shackle_path)

        body_grad = QLinearGradient(16, 26, 48, 52)
        body_grad.setColorAt(0.0, QColor("#fef08a"))
        body_grad.setColorAt(0.2, QColor("#facc15"))
        body_grad.setColorAt(0.8, QColor("#d97706"))
        body_grad.setColorAt(1.0, QColor("#92400e"))
        p.setPen(QPen(QColor("#78350f"), 1.2))
        p.setBrush(QBrush(body_grad))
        p.drawRoundedRect(QRectF(16, 26, 32, 26), 6, 6)

        p.setPen(QPen(QColor(255, 255, 255, 220), 1.2))
        p.drawLine(19, 27, 45, 27)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#451a03")))
        p.drawEllipse(QRectF(29.5, 34, 5, 5))
        keyhole_path = QPainterPath()
        keyhole_path.moveTo(30, 37)
        keyhole_path.lineTo(34, 37)
        keyhole_path.lineTo(33, 44)
        keyhole_path.lineTo(31, 44)
        keyhole_path.closeSubpath()
        p.drawPath(keyhole_path)
        p.end()
        img.save(paths["lock_white"])

        # 6. lightning (Realistic 3D Emerald Energy Bolt)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bolt_grad = QLinearGradient(20, 10, 44, 54)
        bolt_grad.setColorAt(0.0, QColor("#6ee7b7"))
        bolt_grad.setColorAt(0.4, QColor("#10b981"))
        bolt_grad.setColorAt(1.0, QColor("#047857"))
        p.setPen(QPen(QColor("#064e3b"), 1.2))
        p.setBrush(QBrush(bolt_grad))
        bolt = QPainterPath()
        bolt.moveTo(36, 10)
        bolt.lineTo(20, 32)
        bolt.lineTo(33, 32)
        bolt.lineTo(27, 54)
        bolt.lineTo(45, 28)
        bolt.lineTo(33, 28)
        bolt.closeSubpath()
        p.drawPath(bolt)

        p.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        p.drawLine(33, 14, 25, 30)
        p.end()
        img.save(paths["lightning"])

        # 7. pause (Realistic 3D Amber Bars)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_grad = QLinearGradient(0, 16, 0, 48)
        bar_grad.setColorAt(0.0, QColor("#fde68a"))
        bar_grad.setColorAt(0.3, QColor("#f59e0b"))
        bar_grad.setColorAt(1.0, QColor("#b45309"))
        p.setPen(QPen(QColor("#92400e"), 1.2))
        p.setBrush(QBrush(bar_grad))
        p.drawRoundedRect(QRectF(20, 16, 8, 32), 4, 4)
        p.drawRoundedRect(QRectF(36, 16, 8, 32), 4, 4)

        p.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
        p.drawLine(22, 18, 26, 18)
        p.drawLine(38, 18, 42, 18)
        p.end()
        img.save(paths["pause"])

        # 8. play (Realistic 3D Emerald Play Button)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        play_grad = QLinearGradient(22, 16, 48, 48)
        play_grad.setColorAt(0.0, QColor("#34d399"))
        play_grad.setColorAt(0.5, QColor("#10b981"))
        play_grad.setColorAt(1.0, QColor("#059669"))
        p.setPen(QPen(QColor("#065f46"), 1.2))
        p.setBrush(QBrush(play_grad))
        play_path = QPainterPath()
        play_path.moveTo(22, 16)
        play_path.lineTo(47, 32)
        play_path.lineTo(22, 48)
        play_path.closeSubpath()
        p.drawPath(play_path)

        p.setPen(QPen(QColor(255, 255, 255, 180), 1.2))
        p.drawLine(24, 19, 44, 32)
        p.end()
        img.save(paths["play"])

        # 9. cancel_x (Realistic 3D Stop Circle with White Cross)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        circle_grad = QRadialGradient(32, 28, 24)
        circle_grad.setColorAt(0.0, QColor("#f87171"))
        circle_grad.setColorAt(0.7, QColor("#dc2626"))
        circle_grad.setColorAt(1.0, QColor("#991b1b"))
        p.setPen(QPen(QColor("#7f1d1d"), 1.2))
        p.setBrush(QBrush(circle_grad))
        p.drawEllipse(QRectF(14, 14, 36, 36))

        p.setPen(QPen(QColor(255, 255, 255, 160), 1.5))
        p.drawArc(QRectF(16, 16, 32, 32), 45 * 16, 90 * 16)

        p.setPen(QPen(QColor("#ffffff"), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(24, 24, 40, 40)
        p.drawLine(40, 24, 24, 40)
        p.end()
        img.save(paths["cancel_x"])

        # 10. moon (Realistic 3D Luminous Crescent Moon)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        moon_grad = QLinearGradient(16, 14, 48, 50)
        moon_grad.setColorAt(0.0, QColor("#e0f2fe"))
        moon_grad.setColorAt(0.5, QColor("#7dd3fc"))
        moon_grad.setColorAt(1.0, QColor("#0284c7"))
        p.setPen(QPen(QColor("#0369a1"), 1.2))
        p.setBrush(QBrush(moon_grad))
        moon = QPainterPath()
        moon.moveTo(38, 14)
        moon.arcTo(16, 14, 34, 34, 90, -180)
        moon.arcTo(24, 18, 26, 26, 270, 160)
        moon.closeSubpath()
        p.drawPath(moon)
        p.end()
        img.save(paths["moon"])

        # 11. sun (Realistic 3D Radiant Golden Sun)
        img = QImage(64, 64, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        sun_grad = QRadialGradient(32, 32, 12)
        sun_grad.setColorAt(0.0, QColor("#fef08a"))
        sun_grad.setColorAt(0.7, QColor("#f59e0b"))
        sun_grad.setColorAt(1.0, QColor("#d97706"))
        p.setPen(QPen(QColor("#b45309"), 1.2))
        p.setBrush(QBrush(sun_grad))
        p.drawEllipse(QRectF(22, 22, 20, 20))

        p.setPen(QPen(QColor("#f59e0b"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(32, 12, 32, 6); p.drawLine(32, 52, 32, 58)
        p.drawLine(12, 32, 6, 32); p.drawLine(52, 32, 58, 32)
        p.drawLine(18, 18, 13, 13); p.drawLine(46, 18, 51, 13)
        p.drawLine(18, 46, 13, 51); p.drawLine(46, 46, 51, 51)
        p.end()
        img.save(paths["sun"])

        # 12. Chevrons & Check
        def _render_arrow(direction="down", color="#334155"):
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(color), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            if direction == "down":
                p.drawLine(9, 13, 16, 20)
                p.drawLine(16, 20, 23, 13)
            else:
                p.drawLine(9, 19, 16, 12)
                p.drawLine(16, 12, 23, 19)
            p.end()
            return img

        def _render_check(color="#ffffff"):
            img = QImage(32, 32, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(color), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawLine(6, 15, 12, 21)
            p.drawLine(12, 21, 24, 9)
            p.end()
            return img

        _render_arrow("down", "#94a3b8").save(paths["arrow_down_dark"])
        _render_arrow("down", "#334155").save(paths["arrow_down_light"])
        _render_arrow("up", "#94a3b8").save(paths["arrow_up_dark"])
        _render_arrow("up", "#334155").save(paths["arrow_up_light"])
        _render_check("#ffffff").save(paths["check_white"])

        try:
            with open(ver_file, "w") as f:
                f.write(_ICON_VERSION)
        except Exception:
            pass

    return {k: v.replace("\\", "/") for k, v in paths.items()}


def get_ui_icon(name: str) -> QIcon:
    """Return a QIcon for a generated UI icon name."""
    paths = _ensure_icons()
    p = paths.get(name)
    if p and os.path.exists(p):
        return QIcon(p)
    return QIcon()


def setup_high_dpi():
    """Configure PyQt6 high-DPI auto-scaling settings."""
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass


def get_app_icon() -> QIcon:
    """Return QIcon loaded from Swift_Prosys.ico."""
    path = _resolve_resource("Swift_Prosys.ico")
    if os.path.exists(path):
        return QIcon(path)
    return QIcon()


def get_brand_logo_pixmap(height: int = 32) -> QPixmap:
    """Return scaled QPixmap of transparent Swift-ProSys logo."""
    target_path = _resolve_resource("Swift-ProSys-Logo-2026-1-removebg-preview.png")
    if not os.path.exists(target_path):
        target_path = _resolve_resource("Swift-ProSys-Logo.png")
    if os.path.exists(target_path):
        pm = QPixmap(target_path)
        if not pm.isNull():
            return pm.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
    return QPixmap()


def _set_palette(app: QApplication, colors: dict):
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor(colors["window"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(colors["text"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(colors["base"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["surface"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["surface"]))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(colors["text"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(colors["surface"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text"]))
    pal.setColor(QPalette.ColorRole.BrightText, QColor(colors["text"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(colors["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(pal)


def apply_theme(app: QApplication, theme_name: str = LIGHT):
    """Apply the given theme ('Light' or 'Dark') to the whole application."""
    if theme_name == DARK:
        _set_palette(app, {
            "window": "#0b0f17", "text": "#f8fafc", "base": "#0f172a",
            "surface": "#141c2e", "accent": "#3b82f6"
        })
        app.setStyleSheet(get_dark_stylesheet())
    else:
        _set_palette(app, {
            "window": "#f8fafc", "text": "#0f172a", "base": "#ffffff",
            "surface": "#ffffff", "accent": "#2563eb"
        })
        app.setStyleSheet(get_light_stylesheet())


def apply_dark_theme(app: QApplication):
    """Backwards-compatible alias."""
    apply_theme(app, DARK)


_BASE_TEMPLATE = """
    QMainWindow, QDialog, QMessageBox {{
        background-color: {window};
        color: {text};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Segoe UI Emoji', 'Inter', -apple-system, sans-serif;
    }}

    QWidget {{
        font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Segoe UI Emoji', 'Inter', -apple-system, sans-serif;
        font-size: 12px;
        color: {text};
    }}

    /* Scroll Area */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}

    /* Message Box */
    QMessageBox {{
        background-color: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 10px;
    }}
    QMessageBox QLabel,
    QLabel#qt_msgbox_label,
    QLabel#qt_msgbox_informativelabel,
    QLabel#qt_msgboxex_icon_label {{
        color: {text} !important;
        background-color: transparent;
        font-size: 13px;
    }}
    QMessageBox QPushButton {{
        background-color: {accent};
        color: #ffffff;
        border: 1px solid {accent_border};
        border-radius: 7px;
        padding: 6px 18px;
        min-width: 75px;
        font-weight: 600;
    }}
    QMessageBox QPushButton:hover {{
        background-color: {accent_hover};
    }}

    /* Elevated Card Panels & GroupBoxes (Modern Card Container) */
    QGroupBox {{
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 10px;
        margin-top: 14px;
        padding-top: 14px;
        padding-bottom: 12px;
        padding-left: 14px;
        padding-right: 14px;
        color: {text};
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        top: 2px;
        padding: 2px 10px;
        color: {section_title};
        background-color: {surface};
        border: 1px solid {border};
        border-radius: 5px;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.3px;
    }}

    /* Tool Separator */
    QFrame#ToolSeparator {{
        background-color: {border};
        width: 1px;
        margin: 3px 6px;
        border: none;
    }}

    /* Header Bar */
    QFrame#HeaderBar {{
        background-color: {header_bg};
        border-bottom: 1px solid {border};
        padding: 8px 18px;
    }}
    QLabel#BrandTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {header_title};
        background: transparent;
        letter-spacing: -0.2px;
    }}
    QLabel#BrandSubtitle {{
        font-size: 11px;
        font-weight: 500;
        color: {header_subtitle};
        background: transparent;
    }}
    QLabel#SecurityBadge {{
        background-color: {badge_bg};
        color: {badge_text};
        border: 1px solid {badge_border};
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }}
    QLabel#PillBadge {{
        background-color: {pill_bg};
        color: {pill_text};
        border: 1px solid {pill_border};
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }}

    /* Standard Button (Modern Elevated Neutral) */
    QPushButton {{
        background-color: {btn_bg};
        color: {text};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px 16px;
        font-weight: 600;
        font-size: 12px;
        min-height: 24px;
    }}
    QPushButton:hover {{
        background-color: {btn_bg_hover};
        border-color: {border_hover};
    }}
    QPushButton:pressed {{
        background-color: {btn_bg_pressed};
    }}
    QPushButton:disabled {{
        background-color: {btn_bg_disabled};
        color: {text_disabled};
        border-color: {border};
    }}

    /* Primary Action Button (Add Files) */
    QPushButton.btn-primary {{
        background-color: {accent};
        color: #ffffff;
        border: 1px solid {accent_border};
        border-radius: 8px;
        font-weight: 600;
    }}
    QPushButton.btn-primary:hover {{
        background-color: {accent_hover};
        border-color: {accent_border};
    }}
    QPushButton.btn-primary:pressed {{
        background-color: {accent_border};
    }}

    /* Hero Success Action (Start Encryption) */
    QPushButton.btn-success {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:0.5 #059669, stop:1 #047857);
        color: #ffffff;
        border: 1px solid #065f46;
        border-radius: 8px;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 0.3px;
        padding: 8px 22px;
        min-height: 26px;
    }}
    QPushButton.btn-success:hover {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:0.5 #10b981, stop:1 #059669);
        border-color: #047857;
    }}
    QPushButton.btn-success:pressed {{
        background-color: #047857;
    }}
    QPushButton.btn-success:disabled {{
        background-color: {btn_bg_disabled};
        color: {text_disabled};
        border-color: {border};
    }}

    /* Danger Action (Clear / Cancel) */
    QPushButton.btn-danger {{
        background-color: {danger_bg};
        color: {danger_text};
        border: 1px solid {danger_border};
        border-radius: 8px;
        font-weight: 600;
    }}
    QPushButton.btn-danger:hover {{
        background-color: {danger_hover};
        border-color: {danger_text};
    }}

    /* Warning Action (Pause) */
    QPushButton.btn-warning {{
        background-color: {warning_bg};
        color: {warning_text};
        border: 1px solid {warning_border};
        border-radius: 8px;
        font-weight: 600;
    }}
    QPushButton.btn-warning:hover {{
        background-color: {warning_hover};
        border-color: {warning_text};
    }}

    /* Ghost / Subtle Button (Theme Toggle) */
    QPushButton.btn-ghost {{
        background-color: transparent;
        border: 1px solid {border};
        border-radius: 8px;
        color: {text_muted};
        font-weight: 600;
        font-size: 11px;
        padding: 5px 14px;
    }}
    QPushButton.btn-ghost:hover {{
        background-color: {btn_bg_hover};
        color: {text};
        border-color: {border_hover};
    }}

    /* Inputs: ComboBox & SpinBox */
    QComboBox, QSpinBox {{
        background-color: {base};
        color: {text};
        border: 1px solid {border};
        border-radius: 7px;
        padding: 5px 10px;
        min-height: 20px;
        font-size: 12px;
        font-weight: 500;
    }}
    QComboBox:hover, QSpinBox:hover {{
        border-color: {border_hover};
    }}
    QComboBox:focus, QSpinBox:focus {{
        border: 1.5px solid {accent};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border-left: 1px solid {border};
    }}
    QComboBox::down-arrow {{
        image: url("{arrow_down_icon}");
        width: 11px;
        height: 11px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {surface};
        color: {text};
        selection-background-color: {accent};
        selection-color: #ffffff;
        border: 1px solid {border};
        border-radius: 7px;
        padding: 4px;
        outline: none;
    }}
    QSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {border};
        border-bottom: 1px solid {border};
    }}
    QSpinBox::up-arrow {{
        image: url("{arrow_up_icon}");
        width: 9px;
        height: 9px;
    }}
    QSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border-left: 1px solid {border};
    }}
    QSpinBox::down-arrow {{
        image: url("{arrow_down_icon}");
        width: 9px;
        height: 9px;
    }}

    /* LineEdit */
    QLineEdit {{
        background-color: {base};
        color: {text};
        border: 1px solid {border};
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 12px;
    }}
    QLineEdit:hover {{
        border-color: {border_hover};
    }}
    QLineEdit:focus {{
        border: 1.5px solid {accent};
    }}

    /* CheckBox */
    QCheckBox {{
        spacing: 8px;
        font-size: 12px;
        font-weight: 600;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1.5px solid {checkbox_border};
        background-color: {base};
    }}
    QCheckBox::indicator:hover {{
        border-color: {accent};
    }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent_border};
        image: url("{check_icon}");
    }}

    /* Modern Table Widget */
    QTableWidget {{
        background-color: {base};
        color: {text};
        gridline-color: {table_grid};
        border: 1px solid {border};
        border-radius: 10px;
        selection-background-color: {row_selection};
        selection-color: {text};
        alternate-background-color: {table_alt_row};
    }}
    QHeaderView::section {{
        background-color: {header_section};
        color: {text_muted};
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.4px;
        padding: 8px 12px;
        border: none;
        border-bottom: 1px solid {border};
        border-right: 1px solid {table_grid};
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border: none;
    }}

    /* Modern Progress Bar */
    QProgressBar {{
        border: 1px solid {border};
        border-radius: 8px;
        text-align: center;
        background-color: {progress_track};
        color: {text};
        font-weight: 700;
        font-size: 11px;
        min-height: 22px;
        max-height: 22px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #06b6d4);
        border-radius: 7px;
    }}

    /* Clean Thin Scrollbars */
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {scrollbar_handle};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {accent};
    }}
    QScrollBar:horizontal {{
        background-color: transparent;
        height: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {scrollbar_handle};
        min-width: 20px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {accent};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0px;
        height: 0px;
    }}

    /* Splitter (Modern subtle grip handle) */
    QSplitter::handle:vertical {{
        background-color: {border};
        height: 2px;
        margin: 4px 0px;
        border-radius: 1px;
    }}
    QSplitter::handle:vertical:hover {{
        background-color: {accent};
        height: 4px;
    }}
    QSplitter::handle:horizontal {{
        background-color: {border};
        width: 2px;
        margin: 0px 4px;
        border-radius: 1px;
    }}
    QSplitter::handle:horizontal:hover {{
        background-color: {accent};
        width: 4px;
    }}

    /* Log Console */
    QTextEdit#LogConsole {{
        background-color: {console_bg};
        color: {console_text};
        font-family: 'Cascadia Code', 'Consolas', 'JetBrains Mono', monospace;
        font-size: 11px;
        border: 1px solid {border};
        border-radius: 10px;
        padding: 10px 12px;
    }}
    /* Empty Dropzone Card */
    QFrame#EmptyDropzone {{
        background-color: {empty_dropzone_bg};
        border: 2px dashed {accent};
        border-radius: 12px;
        margin: 6px 4px;
        padding: 14px 16px;
    }}
    QLabel#DropzoneIcon {{
        font-size: 38px;
        background: transparent;
        font-family: 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif;
    }}
    QLabel#DropzoneTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {text};
        background: transparent;
        letter-spacing: -0.2px;
    }}
    QLabel#DropzoneSubtitle {{
        font-size: 11px;
        font-weight: 500;
        color: {text_muted};
        background: transparent;
    }}

    /* Metrics Container Card */
    QFrame#MetricsCard {{
        background-color: {base};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 4px 12px;
    }}

    QLabel#MetricsLabel {{
        color: {text_muted};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        background: transparent;
    }}
"""


def get_dark_stylesheet() -> str:
    """Return clean, refined Dark theme stylesheet."""
    icons = _ensure_icons()
    return _BASE_TEMPLATE.format(
        window="#090d16",
        text="#f8fafc",
        text_muted="#94a3b8",
        section_title="#94a3b8",
        base="#0f172a",
        surface="#111827",
        border="#1e293b",
        border_hover="#334155",
        accent="#3b82f6",
        accent_border="#2563eb",
        accent_hover="#2563eb",
        accent_text="#60a5fa",
        header_bg="#0d1322",
        btn_bg="#1e293b",
        btn_bg_hover="#28354e",
        btn_bg_pressed="#162035",
        btn_bg_disabled="#0f172a",
        text_disabled="#475569",
        header_section="#0f172a",
        table_grid="#162035",
        table_alt_row="#0d1424",
        row_selection="#172554",
        scrollbar_handle="#334155",
        header_title="#f8fafc",
        header_subtitle="#94a3b8",
        badge_bg="#172554",
        badge_text="#93c5fd",
        badge_border="#1e3a8a",
        pill_bg="#064e3b",
        pill_text="#34d399",
        pill_border="#059669",
        console_bg="#050811",
        console_text="#38bdf8",
        progress_track="#1e293b",
        warning_bg="#1e293b",
        warning_text="#fbbf24",
        warning_border="#78350f",
        warning_hover="#451a03",
        danger_bg="#1e293b",
        danger_text="#f87171",
        danger_border="#7f1d1d",
        danger_hover="#450a0a",
        checkbox_border="#475569",
        empty_dropzone_bg="#0b101d",
        arrow_down_icon=icons["arrow_down_dark"],
        arrow_up_icon=icons["arrow_up_dark"],
        check_icon=icons["check_white"],
    )


def get_light_stylesheet() -> str:
    """Return clean, refined Light theme stylesheet."""
    icons = _ensure_icons()
    return _BASE_TEMPLATE.format(
        window="#f8fafc",
        text="#0f172a",
        text_muted="#64748b",
        section_title="#475569",
        base="#ffffff",
        surface="#ffffff",
        border="#e2e8f0",
        border_hover="#cbd5e1",
        accent="#2563eb",
        accent_border="#1d4ed8",
        accent_hover="#1d4ed8",
        accent_text="#2563eb",
        header_bg="#ffffff",
        btn_bg="#ffffff",
        btn_bg_hover="#f1f5f9",
        btn_bg_pressed="#e2e8f0",
        btn_bg_disabled="#f8fafc",
        text_disabled="#94a3b8",
        header_section="#f8fafc",
        table_grid="#f1f5f9",
        table_alt_row="#fbfcfe",
        row_selection="#eff6ff",
        scrollbar_handle="#cbd5e1",
        header_title="#0f172a",
        header_subtitle="#64748b",
        badge_bg="#eff6ff",
        badge_text="#2563eb",
        badge_border="#bfdbfe",
        pill_bg="#f0fdf4",
        pill_text="#16a34a",
        pill_border="#bbf7d0",
        console_bg="#0f172a",
        console_text="#38bdf8",
        progress_track="#e2e8f0",
        warning_bg="#ffffff",
        warning_text="#d97706",
        warning_border="#fcd34d",
        warning_hover="#fef3c7",
        danger_bg="#ffffff",
        danger_text="#dc2626",
        danger_border="#fca5a5",
        danger_hover="#fee2e2",
        checkbox_border="#cbd5e1",
        empty_dropzone_bg="#f8fafc",
        arrow_down_icon=icons["arrow_down_light"],
        arrow_up_icon=icons["arrow_up_light"],
        check_icon=icons["check_white"],
    )


def get_stylesheet(theme_name: str = LIGHT) -> str:
    return get_dark_stylesheet() if theme_name == DARK else get_light_stylesheet()


def get_mnc_stylesheet() -> str:
    """Backwards-compatible alias."""
    return get_dark_stylesheet()
