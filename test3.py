#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("pip install Pillow"); sys.exit(1)

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QSlider, QFileDialog, QTextEdit, QMessageBox, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QPointF
    from PyQt6.QtGui import (
        QFont, QPixmap, QDragEnterEvent, QDropEvent, QPainter,
        QColor, QPen, QBrush, QRadialGradient
    )
except ImportError:
    print("pip install PyQt6"); sys.exit(1)

CFG_FILE = "wm_config.json"
DEFAULTS = {"logo": "", "rel_x": 0.95, "rel_y": 0.95, "opacity": 80, "size": 20}

def load():
    if os.path.exists(CFG_FILE):
        try:
            d = json.load(open(CFG_FILE, encoding="utf-8"))
            for k, v in DEFAULTS.items(): d.setdefault(k, v)
            return d
        except: pass
    return DEFAULTS.copy()

def save(d):
    json.dump(d, open(CFG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def stamp(src_pil: Image.Image, logo_pil: Image.Image,
          rel_x: float, rel_y: float, opacity: int, size: int) -> Image.Image:
    W, H = src_pil.size
    max_r = int(min(W, H) * size / 100)
    logo  = logo_pil.copy().convert("RGBA")
    logo.thumbnail((max_r, max_r), Image.LANCZOS)
    lw, lh = logo.size

    x = int((W - lw) * rel_x)
    y = int((H - lh) * rel_y)

    if opacity < 100:
        r, g, b, a = logo.split()
        a = a.point(lambda v: int(v * opacity / 100))
        logo = Image.merge("RGBA", (r, g, b, a))

    base = src_pil.convert("RGBA")
    base.paste(logo, (x, y), logo)
    return base.convert("RGB")

class Worker(QThread):
    log      = pyqtSignal(str)
    finished = pyqtSignal(int, int)

    def __init__(self, in_dir, out_dir, logo_pil, rx, ry, op, sz):
        super().__init__()
        self.in_dir, self.out_dir = in_dir, out_dir
        self.logo_pil, self.rx, self.ry = logo_pil, rx, ry
        self.op, self.sz = op, sz

    def run(self):
        exts  = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        files = sorted(f for f in os.listdir(self.in_dir)
                       if Path(f).suffix.lower() in exts)
        if not files:
            self.log.emit("❌ 未找到图片"); self.finished.emit(0, 0); return

        os.makedirs(self.out_dir, exist_ok=True)
        ok = 0
        for i, name in enumerate(files, 1):
            self.log.emit(f"[{i}/{len(files)}] {name}")
            try:
                img    = Image.open(os.path.join(self.in_dir, name)).convert("RGB")
                result = stamp(img, self.logo_pil, self.rx, self.ry, self.op, self.sz)
                dst    = os.path.join(self.out_dir, Path(name).stem + "_wm.png")
                result.save(dst, "PNG", dpi=(300, 300))
                ok += 1
            except Exception as e:
                self.log.emit(f"  ❌ {e}")
        self.finished.emit(ok, len(files))

DARK = "#0F1117"; CARD = "#1A1B22"; CARD_HOVER = "#212229"; BORDER = "#2E2F38"
ACCENT = "#00D47E"; TEXT = "#E8E9F0"; MUTED = "#6B6D7A"

STYLE = f"""
QWidget {{ background:{DARK}; color:{TEXT};
    font-family:'Microsoft YaHei UI','PingFang SC',sans-serif; font-size:13px; }}
QLineEdit, QTextEdit {{
    background:{CARD}; border:1px solid {BORDER};
    border-radius:7px; padding:7px 10px; color:{TEXT}; }}
QPushButton {{
    background:#252630; border:1px solid {BORDER};
    border-radius:7px; padding:8px 16px; font-weight:600; color:{TEXT}; }}
QPushButton:hover {{ background:#2E3040; border-color:{ACCENT}; }}
QPushButton#run {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00C571,stop:1 #00A85C);
    color:white; border:none; font-size:14px;
    font-weight:700; border-radius:10px; }}
QPushButton#run:hover {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00D87A,stop:1 #00C066); }}
QPushButton#run:disabled {{ background:#162A1F; color:#2A5040; }}
QTextEdit {{ background:#0C0D12; font-family:'Consolas',monospace;
    font-size:12px; color:#9ECEFF;
    border:1px solid {BORDER}; border-radius:8px; padding:8px; }}
QSlider::groove:horizontal {{
    height:4px; background:{BORDER}; border-radius:2px; }}
QSlider::handle:horizontal {{
    width:14px; height:14px; background:{ACCENT};
    border-radius:7px; margin:-5px 0; }}
QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
QFrame#div {{ border:none; border-top:1px solid {BORDER}; max-height:1px; }}
"""

class PreviewCanvas(QLabel):
    changed = pyqtSignal(str)
    pos_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFixedHeight(220)
        self._path = ""
        self.logo_pix = None
        self.bg_pix = None
        self.rel_x = 0.95
        self.rel_y = 0.95
        self.logo_size = 20
        self.logo_op = 80
        self.dragging = False
        self._set_empty_style()

    def _set_empty_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {BORDER};
                border-radius: 15px;
                background: qradialgradient(cx:0.5, cy:0.5, radius:1, fx:0.5, fy:0.5, stop:0 {CARD}, stop:1 #13141A);
            }}
            QLabel:hover {{
                border-color: {ACCENT};
                background: qradialgradient(cx:0.5, cy:0.5, radius:1, fx:0.5, fy:0.5, stop:0 {CARD_HOVER}, stop:1 #16171F);
            }}
        """)

    def _set_active_style(self):
        self.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {ACCENT};
                border-radius: 15px;
                background-color: #0C0D12;
            }}
        """)

    def _set_drag_active(self, active):
        if active:
            self.setStyleSheet(f"""
                QLabel {{
                    border: 3px solid {ACCENT};
                    border-radius: 15px;
                    background-color: #162A1F;
                }}
            """)
        elif self.logo_pix:
            self._set_active_style()
        else:
            self._set_empty_style()

    def _set_logo(self, path):
        self._path = path
        self.logo_pix = QPixmap(path)
        self._set_active_style()
        self.update()
        self.changed.emit(path)

    def load_logo(self, path):
        if path and os.path.exists(path):
            self._set_logo(path)

    def load_bg(self, path):
        if path and os.path.exists(path):
            self.bg_pix = QPixmap(path)
            self._set_active_style()
        else:
            self.bg_pix = None
            if not self.logo_pix:
                self._set_empty_style()
        self.update()

    @property
    def path(self): return self._path

    def _get_active_rect(self):
        cw, ch = self.width(), self.height()
        if self.bg_pix and not self.bg_pix.isNull():
            scaled = self.bg_pix.scaled(cw, ch, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (cw - scaled.width()) // 2
            y = (ch - scaled.height()) // 2
            return QRect(x, y, scaled.width(), scaled.height()), scaled
        return QRect(0, 0, cw, ch), None

    def _get_logo_rect(self, active_rect):
        if not self.logo_pix: return QRect(), None
        side = int(min(active_rect.width(), active_rect.height()) * (self.logo_size / 100))
        if side <= 0: return QRect(), None

        scaled_logo = self.logo_pix.scaled(
            side, side, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        lw, lh = scaled_logo.width(), scaled_logo.height()
        px = int(active_rect.x() + (active_rect.width() - lw) * self.rel_x)
        py = int(active_rect.y() + (active_rect.height() - lh) * self.rel_y)
        return QRect(px, py, lw, lh), scaled_logo

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        active_rect, scaled_bg = self._get_active_rect()

        if scaled_bg:
            painter.drawPixmap(active_rect.topLeft(), scaled_bg)
            cx = float(active_rect.center().x())
            cy = float(active_rect.center().y())
            radius = float(max(active_rect.width(), active_rect.height()))
            vignette_gradient = QRadialGradient(cx, cy, radius)
            vignette_gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
            vignette_gradient.setColorAt(0.8, QColor(0, 0, 0, 20))
            vignette_gradient.setColorAt(1.0, QColor(0, 0, 0, 60))
            painter.fillRect(active_rect, QBrush(vignette_gradient))
        else:
            icon_w, icon_h = 60, 60
            icon_x = active_rect.center().x() - icon_w // 2
            icon_y = active_rect.center().y() - icon_h - 10
            icon_rect = QRect(icon_x, icon_y, icon_w, icon_h)

            painter.setPen(QPen(QColor(MUTED), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(icon_rect, 8, 8)

            painter.drawLine(icon_rect.left() + 10, icon_rect.bottom() - 15, icon_rect.left() + 25, icon_rect.top() + 15)
            painter.drawLine(icon_rect.left() + 25, icon_rect.top() + 15, icon_rect.right() - 10, icon_rect.bottom() - 15)
            painter.drawEllipse(icon_rect.right() - 25, icon_rect.top() + 15, 15, 15)

            painter.setPen(QColor(TEXT))
            font = QFont("Microsoft YaHei UI", 13)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)

            text_rect = active_rect.adjusted(0, icon_h + 10, 0, 0)
            text = "将 Logo 拖到这里\n（加载源目录后，会显示第一张图作为预览）"
            align = int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.AlignmentFlag.AlignTop)
            painter.drawText(text_rect, align, text)
            return

        if not self.logo_pix: return

        l_rect, scaled_logo = self._get_logo_rect(active_rect)
        if scaled_logo:
            painter.setOpacity(self.logo_op / 100.0)
            painter.drawPixmap(l_rect.topLeft(), scaled_logo)
            painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(ACCENT), 2, Qt.PenStyle.DashLine))
            painter.drawRect(l_rect)

    def mousePressEvent(self, e):
        if not self.logo_pix:
            f, _ = QFileDialog.getOpenFileName(
                self, "选择 Logo", "", "图片 (*.png *.jpg *.jpeg *.webp)"
            )
            if f: self._set_logo(f)
            return

        active_rect, _ = self._get_active_rect()
        l_rect, _ = self._get_logo_rect(active_rect)
        if l_rect.contains(e.position().toPoint()):
            self.dragging = True

    def mouseMoveEvent(self, e):
        if self.dragging and self.logo_pix:
            active_rect, _ = self._get_active_rect()
            l_rect, scaled_logo = self._get_logo_rect(active_rect)
            if not scaled_logo: return

            lw, lh = scaled_logo.width(), scaled_logo.height()
            aw, ah = active_rect.width(), active_rect.height()

            denom_x = max(1, aw - lw)
            denom_y = max(1, ah - lh)

            new_x = (e.position().x() - active_rect.x() - lw/2) / denom_x
            new_y = (e.position().y() - active_rect.y() - lh/2) / denom_y

            self.rel_x = max(0.0, min(1.0, new_x))
            self.rel_y = max(0.0, min(1.0, new_y))
            self.update()
            self.pos_changed.emit()

    def mouseReleaseEvent(self, e):
        self.dragging = False

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, e):
        self._set_drag_active(False)

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()
        self._set_drag_active(False)
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                self._set_logo(path)

def mkdiv():
    f = QFrame(); f.setObjectName("div"); return f

def slider_row(label, mn, mx, val):
    row  = QHBoxLayout()
    lbl  = QLabel(label)
    lbl.setFixedWidth(60)
    sl   = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(mn, mx); sl.setValue(val)
    val_lbl = QLabel(f"{val}%")
    val_lbl.setFixedWidth(36)
    val_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:600;")
    sl.valueChanged.connect(lambda v: val_lbl.setText(f"{v}%"))
    row.addWidget(lbl); row.addWidget(sl, stretch=1); row.addWidget(val_lbl)
    return row, sl

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("水印叠加工具")
        self.resize(520, 660)
        self.setStyleSheet(STYLE)
        self.cfg = load()
        self._build()

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        lay  = QVBoxLayout(root)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        t = QLabel("水印叠加工具")
        t.setFont(QFont("Microsoft YaHei UI", 14, QFont.Weight.Bold))
        lay.addWidget(t)
        lay.addWidget(mkdiv())

        self.canvas = PreviewCanvas()
        self.canvas.rel_x = self.cfg["rel_x"]
        self.canvas.rel_y = self.cfg["rel_y"]
        self.canvas.logo_size = self.cfg["size"]
        self.canvas.logo_op = self.cfg["opacity"]

        self.canvas.load_logo(self.cfg["logo"])
        self.canvas.changed.connect(self._on_logo)
        self.canvas.pos_changed.connect(self._save)
        lay.addWidget(self.canvas)

        lay.addWidget(mkdiv())

        op_row, self.sl_op = slider_row("透明度", 10, 100, self.cfg["opacity"])
        self.sl_op.valueChanged.connect(self._on_slider_changed)
        lay.addLayout(op_row)

        sz_row, self.sl_sz = slider_row("大小", 5, 40, self.cfg["size"])
        self.sl_sz.valueChanged.connect(self._on_slider_changed)
        lay.addLayout(sz_row)

        lay.addWidget(mkdiv())

        for attr, ph, btn_t in [
            ("edit_in",  "源图片文件夹...", "源目录"),
            ("edit_out", "输出目录（留空自动创建）...", "输出目录"),
        ]:
            row = QHBoxLayout()
            from PyQt6.QtWidgets import QLineEdit
            e = QLineEdit(); e.setPlaceholderText(ph); e.setReadOnly(True)
            setattr(self, attr, e)
            b = QPushButton(f"📁 {btn_t}"); b.setFixedWidth(110)
            b.clicked.connect(lambda _, ed=e: self._pick(ed))
            row.addWidget(e, stretch=1); row.addWidget(b)
            lay.addLayout(row)

        lay.addWidget(mkdiv())

        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.log.setFixedHeight(110)
        self.log.setPlaceholderText("日志...")
        lay.addWidget(self.log)

        self.btn = QPushButton("🚀  开始批量处理")
        self.btn.setObjectName("run"); self.btn.setFixedHeight(46)
        self.btn.clicked.connect(self._run)
        lay.addWidget(self.btn)

    def _on_logo(self, path):
        self.cfg["logo"] = path
        self._save()

    def _on_slider_changed(self):
        self.canvas.logo_size = self.sl_sz.value()
        self.canvas.logo_op = self.sl_op.value()
        self.canvas.update()
        self._save()

    def _save(self):
        self.cfg.update({
            "rel_x": self.canvas.rel_x,
            "rel_y": self.canvas.rel_y,
            "opacity": self.sl_op.value(),
            "size":  self.sl_sz.value(),
        })
        save(self.cfg)

    def _pick(self, edit):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            edit.setText(d)
            if edit == self.edit_in:
                self._load_preview_bg(d)

    def _load_preview_bg(self, directory):
        exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        try:
            files = sorted(f for f in os.listdir(directory) if Path(f).suffix.lower() in exts)
            if files:
                first_img_path = os.path.join(directory, files[0])
                self.canvas.load_bg(first_img_path)
            else:
                self.canvas.load_bg("")
        except Exception:
            self.canvas.load_bg("")

    def _run(self):
        if not self.canvas.path:
            QMessageBox.warning(self, "提示", "请先拖入或选择 Logo 图片！"); return
        in_d = self.edit_in.text().strip()
        if not in_d:
            QMessageBox.warning(self, "提示", "请选择源图片文件夹！"); return

        out_d = self.edit_out.text().strip() or os.path.join(in_d, "watermarked")
        self._save()

        try:
            logo_pil = Image.open(self.canvas.path).convert("RGBA")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"Logo 加载失败: {e}"); return

        self.btn.setEnabled(False); self.btn.setText("⏳ 处理中...")
        self.log.clear()

        self.w = Worker(in_d, out_d, logo_pil,
                        self.canvas.rel_x, self.canvas.rel_y,
                        self.sl_op.value(), self.sl_sz.value())
        self.w.log.connect(self.log.append)
        self.w.finished.connect(self._done)
        self.w.start()

    def _done(self, ok, total):
        self.btn.setEnabled(True); self.btn.setText("🚀  开始批量处理")
        self.log.append(f"✅ 完成 {ok}/{total} 张 → {self.w.out_dir}")
        QMessageBox.information(self, "完成", f"成功 {ok}/{total} 张\n\n{self.w.out_dir}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    App().show()
    sys.exit(app.exec())