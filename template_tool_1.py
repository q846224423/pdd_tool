"""
照片处理工具  —  合并版
════════════════════════════════════════════════════════════════
Tab 1  相框合成：加载相框图 → 调位置 → 保存模板 → 批量输出
Tab 2  主图合成：选 PNG 模板 → 导入相框坐标(可选) → 批量合成
两个 Tab 共享同一套相框模板坐标数据，无需重复操作。

pip install PyQt6 pillow numpy
════════════════════════════════════════════════════════════════
"""

import sys, os, json, ctypes, logging
from pathlib import Path
from typing  import Optional, List, Tuple

import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame, QSplitter,
    QStatusBar, QMessageBox, QSlider, QListWidget, QListWidgetItem,
    QProgressBar, QScrollArea, QAbstractItemView, QDoubleSpinBox,
    QTabWidget, QSpinBox, QComboBox, QRadioButton, QButtonGroup,
    QTextEdit, QLineEdit
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal
from PyQt6.QtGui   import QPixmap, QImage, QCursor, QColor, QPalette

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
CONFIG_FILE   = Path(__file__).parent / "photo_tool_config.json"


# ══════════════════════════════════════════════════════════════
# 配置持久化
# ══════════════════════════════════════════════════════════════

def load_cfg() -> dict:
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception: pass
    return {}

def save_cfg(d: dict):
    try: CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e: log.warning(f"配置保存失败: {e}")


# ══════════════════════════════════════════════════════════════
# 样式表
# ══════════════════════════════════════════════════════════════

QSS = """
* { box-sizing: border-box; outline: none; }
QMainWindow { background: #111113; }
QWidget {
    color: #dddde5;
    font-family: "Microsoft YaHei UI","PingFang SC","SF Pro Display",sans-serif;
    font-size: 13px; background: transparent;
}
QWidget#root { background: #111113; }

/* ── Tab ── */
QTabWidget::pane {
    border: none; background: transparent; margin-top: 2px;
}
QTabBar::tab {
    background: #1a1a22; color: #606075;
    border: 1px solid #26262e; border-bottom: none;
    padding: 9px 28px; font-size: 13px; font-weight: 600;
    border-radius: 8px 8px 0 0; margin-right: 3px;
}
QTabBar::tab:selected { background: #22222e; color: #dddde5; border-color: #32323e; }
QTabBar::tab:hover:!selected { background: #1e1e28; color: #9898b8; }

/* ── 面板容器 ── */
QWidget#panel {
    background: #161619; border: 1px solid #24242c; border-radius: 12px;
}
QWidget#rpanel {
    background: #161619; border: 1px solid #24242c; border-radius: 12px;
}

/* ── 分区标题 ── */
QLabel#sec {
    color: #505068; font-size: 10px; font-weight: 700;
    letter-spacing: 2.5px; background: transparent;
}

/* ── 分割线 ── */
QFrame#div { background: #26263a; border: none; max-height: 1px; }

/* ── 输入框 ── */
QLineEdit {
    background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 7px;
    padding: 8px 10px; color: #a8a8c0; font-size: 12px;
}
QLineEdit:focus { border-color: #2c2c3c; }
QLineEdit[readOnly="true"] { color: #505068; }

/* ── 列表 ── */
QListWidget {
    background: #1a1a22; border: 1px solid #2c2c3c; border-radius: 8px;
    color: #b8b8cc; outline: none; padding: 3px; font-size: 12px;
}
QListWidget::item { padding: 7px 10px; border-radius: 5px; }
QListWidget::item:selected { background: #0a84ff; color: #fff; }
QListWidget::item:hover:!selected { background: #242434; }

/* ── 滑块 ── */
QSlider::groove:horizontal { height: 3px; background: #282838; border-radius: 1px; }
QSlider::handle:horizontal {
    width: 13px; height: 13px; margin: -5px 0;
    background: #c0c0d8; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #fff; }
QSlider::sub-page:horizontal { background: #0a84ff; border-radius: 1px; }

/* ── 数字框 ── */
QDoubleSpinBox {
    background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 6px;
    padding: 5px 6px; color: #a8a8c0; font-size: 12px;
    min-width: 64px; max-width: 64px;
    font-family: "Cascadia Code","Consolas",monospace;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: #24242e; border: none; width: 15px;
}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #303040; }

QSpinBox {
    background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 7px;
    padding: 7px 8px; color: #a8a8c0; font-size: 12px;
}
QSpinBox::up-button, QSpinBox::down-button { background: #242434; border: none; width: 16px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #383848; }

QComboBox {
    background: #1e1e28; border: 1px solid #2c2c3c; border-radius: 7px;
    padding: 7px 10px; color: #a8a8c0; font-size: 12px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #20202c; border: 1px solid #32323e;
    color: #c0c0d0; selection-background-color: #0a84ff; outline: none;
}

/* ── 进度条 ── */
QProgressBar {
    background: #1a1a22; border: none; border-radius: 2px;
    height: 4px; color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0a84ff,stop:1 #5ac8fa);
    border-radius: 2px;
}

/* ── 日志 ── */
QTextEdit {
    background: #0e0e16; border: 1px solid #1e1e2a; border-radius: 9px;
    color: #707080; font-family: "Cascadia Code","Consolas","Courier New",monospace;
    font-size: 11.5px; padding: 10px;
}

/* ── 按钮基础 ── */
QPushButton {
    background: #24242e; color: #c8c8dc; border-radius: 7px;
    padding: 8px 14px; font-weight: 600; font-size: 13px; border: none;
}
QPushButton:hover { background: #30303e; color: #fff; }
QPushButton:disabled { background: #1a1a22; color: #404050; }

/* 主行动 */
QPushButton#btnPrimary {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2591ff,stop:1 #0073ea);
    border: 1px solid #005bb8; border-top: 1px solid #5ab0ff;
    color: #fff; font-size: 14px; font-weight: 800; letter-spacing: 1.5px;
    padding: 12px 0; border-radius: 9px;
}
QPushButton#btnPrimary:hover {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #47a3ff,stop:1 #0a80f5);
}
QPushButton#btnPrimary:pressed { background: #005ac8; }
QPushButton#btnPrimary:disabled { background: #1e1e28; border: 1px solid #22222a; color: #404052; }

/* 幽灵按钮 */
QPushButton#btnGhost {
    background: #1e1e2a; color: #8080a0; border: 1px solid #32323e; font-size: 12px;
}
QPushButton#btnGhost:hover { background: #28283a; color: #c0c0d8; }

/* 绿 */
QPushButton#btnGreen {
    background: rgba(40,196,84,0.13); color: #4ade80;
    border: 1px solid rgba(40,196,84,0.38); font-size: 12px; font-weight: 600;
}
QPushButton#btnGreen:hover { background: rgba(40,196,84,0.24); border-color: #4ade80; }

/* 红 */
QPushButton#btnRed {
    background: rgba(240,64,48,0.13); color: #f87171;
    border: 1px solid rgba(240,64,48,0.38); font-size: 12px; font-weight: 600;
}
QPushButton#btnRed:hover { background: rgba(240,64,48,0.24); border-color: #f87171; }

/* 橙 */
QPushButton#btnOrange {
    background: rgba(255,159,10,0.13); color: #ff9f0a;
    border: 1px solid rgba(255,159,10,0.38); font-size: 12px; font-weight: 700;
    padding: 9px 0; border-radius: 8px;
}
QPushButton#btnOrange:hover { background: rgba(255,159,10,0.24); border-color: #ff9f0a; }
QPushButton#btnOrange:disabled { background: #1a1a14; color: #3a3010; border-color: #1e1e14; }

/* 日志清空 */
QPushButton#btnClear {
    background: rgba(255,255,255,0.05); color: #606070;
    border: 1px solid rgba(255,255,255,0.12); padding: 4px 12px;
    font-size: 11px; border-radius: 6px;
}
QPushButton#btnClear:hover { background: rgba(255,255,255,0.1); color: #c0c0d0; }

/* Radio */
QRadioButton { color: #9090a8; font-size: 12px; spacing: 6px; }
QRadioButton::indicator {
    width: 14px; height: 14px; border-radius: 7px;
    border: 1.5px solid #38384a; background: #1e1e28;
}
QRadioButton::indicator:checked { background: #0a84ff; border-color: #0a84ff; }

/* 坐标信息卡 */
QWidget#coordCard {
    background: #1a1a26; border: 1px solid #2e2e40; border-radius: 8px;
}

/* 状态栏 */
QStatusBar { background: #0c0c12; border-top: 1px solid #1a1a22; color: #44445a; font-size: 11px; padding: 2px 14px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #282838; border-radius: 2px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #383848; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #1a1a24; }
"""


# ══════════════════════════════════════════════════════════════
# 图像处理工具函数
# ══════════════════════════════════════════════════════════════

def extract_frame(img: Image.Image) -> Image.Image:
    """去除纯色背景，返回 RGBA"""
    if img.mode == "RGBA": return img.copy()
    rgba = img.convert("RGBA"); arr = np.array(rgba)
    bg = np.mean([arr[0,0,:3],arr[0,-1,:3],arr[-1,0,:3],arr[-1,-1,:3]], axis=0).astype(np.uint8)
    arr[np.all(np.abs(arr[:,:,:3].astype(int)-bg.astype(int))<30, axis=2), 3] = 0
    return Image.fromarray(arr, "RGBA")

def frame_composite(bg: Image.Image, frame_rgba: Image.Image,
                    cx: float, cy: float, scale: float) -> Image.Image:
    """相框贴到背景上"""
    bw, bh = bg.size
    fw = int(bw * scale); fh = int(frame_rgba.height * fw / frame_rgba.width)
    fr = frame_rgba.resize((fw, fh), Image.LANCZOS)
    left = max(0, min(int(cx*bw - fw/2), bw-fw))
    top  = max(0, min(int(cy*bh - fh/2), bh-fh))
    out  = bg.convert("RGBA").copy(); out.paste(fr, (left, top), fr)
    return out.convert("RGB")

def main_composite_coords(photo: Image.Image, tpl_path: str,
                          x1:int, y1:int, x2:int, y2:int,
                          out_w:int, out_h:int, dpi:int) -> Image.Image:
    """主图合成：按指定坐标填入照片"""
    tpl = Image.open(tpl_path).convert("RGBA"); tw, th = tpl.size
    hw, hh = x2-x1, y2-y1
    p = photo.convert("RGBA")
    sc = max(hw/p.width, hh/p.height)
    p = p.resize((int(p.width*sc), int(p.height*sc)), Image.LANCZOS)
    lc, tc = (p.width-hw)//2, (p.height-hh)//2
    p = p.crop((lc, tc, lc+hw, tc+hh))
    canvas = Image.new("RGBA", (tw, th), (255,255,255,255))
    canvas.paste(p, (x1, y1))
    return Image.alpha_composite(canvas, tpl).convert("RGB").resize((out_w, out_h), Image.LANCZOS)

def main_composite_auto(photo: Image.Image, tpl_path: str,
                        out_w:int, out_h:int, dpi:int) -> Image.Image:
    """主图合成：自动检测透明镂空区域"""
    tpl = Image.open(tpl_path).convert("RGBA"); tw, th = tpl.size
    alpha = np.array(tpl)[:,:,3]
    rows = np.any(alpha==0, axis=1); cols = np.any(alpha==0, axis=0)
    if rows.any() and cols.any():
        y1,y2 = int(np.where(rows)[0][0]), int(np.where(rows)[0][-1])
        x1,x2 = int(np.where(cols)[0][0]), int(np.where(cols)[0][-1])
    else: x1,y1,x2,y2 = 0,0,tw,th
    return main_composite_coords(photo, tpl_path, x1,y1,x2,y2, out_w, out_h, dpi)


# ══════════════════════════════════════════════════════════════
# 模板数据
# ══════════════════════════════════════════════════════════════

class FrameTemplate:
    def __init__(self):
        self.cx=0.5; self.cy=0.5; self.scale=0.4
        self.ref_w=self.ref_h=0
        self.left=self.top=self.right=self.bottom=0
        self.frame_w=self.frame_h=0
        self.loaded=False

    def record(self, bg, frame_rgba, cx, cy, scale):
        bw,bh=bg.size; fw=int(bw*scale); fh=int(frame_rgba.height*fw/frame_rgba.width)
        left=max(0,min(int(cx*bw-fw/2),bw-fw)); top=max(0,min(int(cy*bh-fh/2),bh-fh))
        self.cx,self.cy,self.scale=cx,cy,scale
        self.ref_w,self.ref_h=bw,bh; self.left,self.top=left,top
        self.right=bw-(left+fw); self.bottom=bh-(top+fh)
        self.frame_w,self.frame_h=fw,fh; self.loaded=True

    def get_coords(self):
        """返回主图合成用的 (x1,y1,x2,y2)"""
        return self.left, self.top, self.left+self.frame_w, self.top+self.frame_h

    def to_dict(self): return dict(self.__dict__)
    def from_dict(self, d):
        for k,v in d.items():
            if hasattr(self,k): setattr(self,k,v)
        self.loaded=True

    def summary(self):
        if not self.loaded: return "尚无模板"
        return (f"参考图 {self.ref_w}×{self.ref_h}  中心({self.cx:.3f},{self.cy:.3f})\n"
                f"左{self.left} 右{self.right} 上{self.top} 下{self.bottom} px  "
                f"相框 {self.frame_w}×{self.frame_h} px")


# ══════════════════════════════════════════════════════════════
# 后台线程
# ══════════════════════════════════════════════════════════════

class FrameBatchWorker(QThread):
    sig_progress = pyqtSignal(int, str)
    sig_done     = pyqtSignal(int)
    sig_error    = pyqtSignal(str)

    def __init__(self, bg_paths, frame_rgba, template, out_dir):
        super().__init__()
        self.bg_paths=bg_paths; self.frame_rgba=frame_rgba
        self.template=template; self.out_dir=out_dir

    def run(self):
        saved=0
        for i,path in enumerate(self.bg_paths):
            try:
                bg=Image.open(path).convert("RGB")
                cx,cy,sc=self.template.cx,self.template.cy,self.template.scale
                r=frame_composite(bg,self.frame_rgba,cx,cy,sc)
                out=str(Path(self.out_dir)/f"{Path(path).stem}_合成.jpg")
                r.save(out,"JPEG",quality=95); saved+=1
                self.sig_progress.emit(i+1,Path(path).name)
            except Exception as e: self.sig_error.emit(f"{Path(path).name}: {e}")
        self.sig_done.emit(saved)


class MainBatchWorker(QThread):
    sig_log  = pyqtSignal(str)
    sig_prog = pyqtSignal(int, int)
    sig_done = pyqtSignal(int, int)

    def __init__(self, inp, out, templates, out_w, out_h, dpi, quality,
                 use_tpl_coords, template):
        super().__init__()
        self.inp,self.out=inp,out; self.templates=templates
        self.out_w,self.out_h,self.dpi,self.quality=out_w,out_h,dpi,quality
        self.use_tpl_coords=use_tpl_coords; self.template=template

    def run(self):
        files=[f for f in Path(self.inp).iterdir()
               if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        total=len(files); ok=fail=0
        Path(self.out).mkdir(parents=True, exist_ok=True)
        for i,src in enumerate(files):
            self.sig_log.emit(f"\n── [{i+1}/{total}]  {src.name}")
            try:
                photo=Image.open(src).convert("RGB")
                for tp_str in self.templates:
                    tp=Path(tp_str)
                    if not tp.exists(): self.sig_log.emit(f"⚠️  不存在: {tp.name}"); continue
                    suf=f"_{tp.stem}" if len(self.templates)>1 else ""
                    name=f"主图_{src.stem}{suf}.jpg"
                    self.sig_log.emit(f"🖼   {tp.name} → {name}")
                    if self.use_tpl_coords and self.template.loaded:
                        x1,y1,x2,y2=self.template.get_coords()
                        r=main_composite_coords(photo,tp_str,x1,y1,x2,y2,self.out_w,self.out_h,self.dpi)
                        self.sig_log.emit(f"   坐标({x1},{y1})→({x2},{y2})")
                    else:
                        r=main_composite_auto(photo,tp_str,self.out_w,self.out_h,self.dpi)
                    r.save(str(Path(self.out)/name),"JPEG",quality=self.quality,dpi=(self.dpi,self.dpi))
                    self.sig_log.emit(f"✅  {name}")
                ok+=1
            except Exception as e: self.sig_log.emit(f"❌  {e}"); fail+=1
            self.sig_prog.emit(i+1,total)
        self.sig_done.emit(ok,fail)


# ══════════════════════════════════════════════════════════════
# 公共小控件
# ══════════════════════════════════════════════════════════════

def sec(text):
    l=QLabel(text); l.setObjectName("sec"); return l

def div():
    f=QFrame(); f.setObjectName("div"); f.setFrameShape(QFrame.Shape.HLine); return f

class PathRow(QWidget):
    def __init__(self, icon, placeholder, parent=None):
        super().__init__(parent)
        lay=QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
        ico=QLabel(icon); ico.setFixedWidth(20)
        ico.setStyleSheet("font-size:15px;background:transparent;color:#606070;")
        self.edit=QLineEdit(); self.edit.setPlaceholderText(placeholder); self.edit.setReadOnly(True)
        btn=QPushButton("浏览"); btn.setObjectName("btnGhost"); btn.setFixedWidth(52)
        btn.clicked.connect(self._browse)
        lay.addWidget(ico); lay.addWidget(self.edit,1); lay.addWidget(btn)
    def _browse(self):
        d=QFileDialog.getExistingDirectory(self,"选择文件夹")
        if d: self.edit.setText(d); self.edit.setToolTip(d)
    def path(self): return self.edit.text().strip()
    def set_path(self,p): self.edit.setText(p); self.edit.setToolTip(p)

class StatCard(QFrame):
    def __init__(self, title, val="—", color="#0a84ff", parent=None):
        super().__init__(parent); self.setObjectName("sc"); self._color=color; self._sty()
        lay=QVBoxLayout(self); lay.setContentsMargins(8,12,8,12); lay.setSpacing(3)
        self._v=QLabel(val); self._v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._v.setStyleSheet(f"color:{color};font-size:26px;font-weight:800;background:transparent;border:none;")
        t=QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color:#404052;font-size:10px;font-weight:600;letter-spacing:2px;background:transparent;border:none;")
        lay.addWidget(self._v); lay.addWidget(t)
    def _sty(self): self.setStyleSheet(f"QFrame#sc{{background:#181820;border:1px solid #24242e;border-top:2px solid {self._color};border-radius:10px;}}")
    def set_value(self,v): self._v.setText(str(v))


# ══════════════════════════════════════════════════════════════
# 预览画布（Tab1 用）
# ══════════════════════════════════════════════════════════════

class PreviewCanvas(QLabel):
    pos_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(380, 280)
        self.setStyleSheet("background:#0e0e16;border-radius:10px;border:1px solid #1e1e2c;")
        self._bg=self._fr=None; self._cx=0.5; self._cy=0.5; self._sc=0.4
        self._dragging=False; self._dr=(0,0,1,1)
        ph=QLabel("先选相框图，再选一张背景图预览", self)
        ph.setStyleSheet("color:#303044;font-size:12px;background:transparent;")
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter); self._ph=ph

    def resizeEvent(self, e): self._ph.setGeometry(self.rect()); self._refresh(); super().resizeEvent(e)

    def set_images(self, bg, fr): self._bg,self._fr=bg,fr; self._ph.setVisible(bg is None); self._refresh()
    def set_placement(self, cx,cy,sc): self._cx,self._cy,self._sc=cx,cy,sc; self._refresh()

    def _refresh(self):
        if self._bg is None: self.clear(); return
        comp=frame_composite(self._bg,self._fr,self._cx,self._cy,self._sc) if self._fr else self._bg.copy()
        cw,ch=self.width(),self.height()
        if cw<10 or ch<10: return
        comp.thumbnail((cw,ch),Image.LANCZOS)
        d=comp.convert("RGB").tobytes("raw","RGB")
        qi=QImage(d,comp.width,comp.height,comp.width*3,QImage.Format.Format_RGB888)
        self.setPixmap(QPixmap.fromImage(qi))
        pw,ph=comp.width,comp.height; self._dr=((cw-pw)//2,(ch-ph)//2,pw,ph)

    def mousePressEvent(self,e):
        if e.button()==Qt.MouseButton.LeftButton and self._bg:
            self._dragging=True; self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
    def mouseMoveEvent(self,e):
        if not self._dragging or not self._bg: return
        dx,dy,pw,ph=self._dr
        self._cx=max(0.01,min(0.99,(e.position().x()-dx)/pw))
        self._cy=max(0.01,min(0.99,(e.position().y()-dy)/ph))
        self._refresh(); self.pos_changed.emit(self._cx,self._cy)
    def mouseReleaseEvent(self,e): self._dragging=False; self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


# ══════════════════════════════════════════════════════════════
# Tab 1  相框合成
# ══════════════════════════════════════════════════════════════

class FrameTab(QWidget):
    # 当模板保存/导入后，通知主窗口同步给 Tab2
    template_updated = pyqtSignal(object)   # FrameTemplate

    def __init__(self, shared_template: FrameTemplate, cfg: dict, parent=None):
        super().__init__(parent)
        self._tpl     = shared_template
        self._cfg     = cfg
        self._fr_rgba = None
        self._bg_pil  = None
        self._result  = None
        self._batch_paths: List[str] = []
        self._worker  = None
        self._build()
        self._restore()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,8,0,0); root.setSpacing(10)

        # ── 左控制面板 ──
        lp = QWidget(); lp.setObjectName("panel"); lp.setFixedWidth(300)
        ll = QVBoxLayout(lp); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        sc_area = QScrollArea(); sc_area.setWidgetResizable(True)
        sc_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); sl = QVBoxLayout(inner); sl.setContentsMargins(14,14,10,10); sl.setSpacing(0)

        # 相框图
        sl.addWidget(sec("相框图")); sl.addSpacing(8)
        fr_row = QHBoxLayout(); fr_row.setSpacing(8)
        self.lbl_fr = QLabel("未选择")
        self.lbl_fr.setStyleSheet("color:#505068;font-size:11px;background:transparent;")
        self.lbl_fr.setWordWrap(True)
        btn_fr = QPushButton("选择"); btn_fr.setObjectName("btnGhost"); btn_fr.setFixedWidth(52)
        btn_fr.clicked.connect(self._load_frame)
        fr_row.addWidget(self.lbl_fr,1); fr_row.addWidget(btn_fr)
        sl.addLayout(fr_row); sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # 预览背景 + 调整
        sl.addWidget(sec("预览调位置")); sl.addSpacing(8)
        prev_row = QHBoxLayout(); prev_row.setSpacing(8)
        self.lbl_prev = QLabel("未选择预览背景")
        self.lbl_prev.setStyleSheet("color:#505068;font-size:11px;background:transparent;")
        self.lbl_prev.setWordWrap(True)
        btn_prev = QPushButton("选背景"); btn_prev.setObjectName("btnGhost"); btn_prev.setFixedWidth(52)
        btn_prev.clicked.connect(self._load_preview)
        prev_row.addWidget(self.lbl_prev,1); prev_row.addWidget(btn_prev)
        sl.addLayout(prev_row); sl.addSpacing(10)

        def sld_row(lbl_txt, lo, hi, default):
            row=QHBoxLayout(); row.setSpacing(8)
            l=QLabel(lbl_txt); l.setFixedWidth(44)
            l.setStyleSheet("color:#606078;font-size:11.5px;background:transparent;")
            sld=QSlider(Qt.Orientation.Horizontal); sld.setRange(lo,hi); sld.setValue(default)
            spn=QDoubleSpinBox(); spn.setRange(lo/100,hi/100); spn.setDecimals(3)
            spn.setSingleStep(0.005); spn.setValue(default/100)
            row.addWidget(l); row.addWidget(sld,1); row.addWidget(spn)
            return row,sld,spn

        r1,self.sld_cx,   self.spn_cx    = sld_row("水平",1,99,50)
        r2,self.sld_cy,   self.spn_cy    = sld_row("垂直",1,99,50)
        r3,self.sld_scale,self.spn_scale = sld_row("大小",5,98,40)
        for r in (r1,r2,r3): sl.addLayout(r); sl.addSpacing(5)

        def link(sld,spn,fn):
            sld.valueChanged.connect(lambda v:[spn.blockSignals(True),spn.setValue(v/100),spn.blockSignals(False),fn(v)])
            spn.valueChanged.connect(lambda v:[sld.blockSignals(True),sld.setValue(int(round(v*100))),sld.blockSignals(False),fn(int(round(v*100)))])
        link(self.sld_cx,   self.spn_cx,   self._on_cx)
        link(self.sld_cy,   self.spn_cy,   self._on_cy)
        link(self.sld_scale,self.spn_scale,self._on_scale)

        self.lbl_pos = QLabel("—")
        self.lbl_pos.setStyleSheet("color:#303048;font-size:10.5px;background:transparent;")
        sl.addSpacing(4); sl.addWidget(self.lbl_pos)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # 保存模板
        sl.addWidget(sec("模板")); sl.addSpacing(8)
        self.btn_save_tpl = QPushButton("📐  保存当前位置为模板")
        self.btn_save_tpl.setObjectName("btnOrange"); self.btn_save_tpl.setEnabled(False)
        self.btn_save_tpl.clicked.connect(self._save_tpl)
        sl.addWidget(self.btn_save_tpl); sl.addSpacing(8)

        io_row = QHBoxLayout(); io_row.setSpacing(8)
        btn_exp = QPushButton("导出 JSON"); btn_exp.setObjectName("btnGhost")
        btn_imp = QPushButton("导入 JSON"); btn_imp.setObjectName("btnGhost")
        btn_exp.clicked.connect(self._export_tpl); btn_imp.clicked.connect(self._import_tpl)
        io_row.addWidget(btn_exp,1); io_row.addWidget(btn_imp,1)
        sl.addLayout(io_row); sl.addSpacing(8)

        self.lbl_tpl = QLabel("尚无模板")
        self.lbl_tpl.setStyleSheet("color:#404058;font-size:10.5px;background:transparent;")
        self.lbl_tpl.setWordWrap(True); sl.addWidget(self.lbl_tpl)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # 批量
        sl.addWidget(sec("批量背景图")); sl.addSpacing(8)
        add_row = QHBoxLayout(); add_row.setSpacing(8)
        btn_add = QPushButton("＋ 添加"); btn_add.setObjectName("btnGreen"); btn_add.setFixedHeight(32)
        btn_clr = QPushButton("清空");    btn_clr.setObjectName("btnRed");   btn_clr.setFixedHeight(32); btn_clr.setFixedWidth(48)
        btn_add.clicked.connect(self._add_batch); btn_clr.clicked.connect(self._clear_batch)
        add_row.addWidget(btn_add,1); add_row.addWidget(btn_clr)
        sl.addLayout(add_row); sl.addSpacing(8)

        self.lst = QListWidget(); self.lst.setFixedHeight(100)
        self.lst.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.lst)
        self.lbl_count = QLabel("0 张")
        self.lbl_count.setStyleSheet("color:#303048;font-size:10.5px;background:transparent;")
        sl.addSpacing(4); sl.addWidget(self.lbl_count); sl.addStretch()

        sc_area.setWidget(inner); ll.addWidget(sc_area,1)

        # 底部固定区
        bot = QWidget(); bot.setStyleSheet("background:transparent;")
        bl = QVBoxLayout(bot); bl.setContentsMargins(14,8,14,12); bl.setSpacing(6)
        self.prog = QProgressBar(); self.prog.setFixedHeight(4)
        self.prog.setTextVisible(False); self.prog.setVisible(False)
        self.btn_run = QPushButton("🚀  开始批量合成相框")
        self.btn_run.setObjectName("btnPrimary"); self.btn_run.setEnabled(False)
        self.btn_run.clicked.connect(self._run_batch)
        bl.addWidget(self.prog); bl.addWidget(self.btn_run)
        ll.addWidget(bot); root.addWidget(lp)

        # ── 右预览区 ──
        rp = QWidget(); rl = QVBoxLayout(rp); rl.setContentsMargins(0,0,0,0); rl.setSpacing(6)
        ph = QHBoxLayout()
        plbl = QLabel("PREVIEW"); plbl.setStyleSheet("color:#242438;font-size:10px;font-weight:700;letter-spacing:2px;background:transparent;")
        ph.addWidget(plbl); ph.addStretch()
        self.lbl_save = QPushButton("💾 保存当前"); self.lbl_save.setObjectName("btnGhost")
        self.lbl_save.setEnabled(False); self.lbl_save.clicked.connect(self._save_one)
        ph.addWidget(self.lbl_save); rl.addLayout(ph)
        self.canvas = PreviewCanvas(); self.canvas.pos_changed.connect(self._on_drag)
        rl.addWidget(self.canvas,1); root.addWidget(rp,1)

    def _restore(self):
        c = self._cfg
        if c.get("frame_fr"):
            p = c["frame_fr"]
            if Path(p).exists(): self._load_frame_path(p)
        if c.get("frame_prev"):
            p = c["frame_prev"]
            if Path(p).exists(): self._load_preview_path(p)
        if c.get("frame_tpl") and Path(c["frame_tpl"]).exists():
            self._load_tpl_from_file(c["frame_tpl"])
        if c.get("frame_cx") is not None:
            for sld,spn,v in [(self.sld_cx,self.spn_cx,int(c["frame_cx"]*100)),
                              (self.sld_cy,self.spn_cy,int(c.get("frame_cy",0.5)*100)),
                              (self.sld_scale,self.spn_scale,int(c.get("frame_scale",0.4)*100))]:
                sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
                spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        if c.get("frame_batch"):
            for p in c["frame_batch"]:
                if Path(p).exists() and p not in self._batch_paths:
                    self._batch_paths.append(p); self.lst.addItem(Path(p).name)
            self.lbl_count.setText(f"{len(self._batch_paths)} 张")
        self._refresh_run_btn()

    def _save_state(self):
        self._cfg.update({
            "frame_cx": self.sld_cx.value()/100,
            "frame_cy": self.sld_cy.value()/100,
            "frame_scale": self.sld_scale.value()/100,
            "frame_batch": self._batch_paths,
        }); save_cfg(self._cfg)

    # ── 加载 ──
    def _load_frame(self):
        p,_=QFileDialog.getOpenFileName(self,"选择相框图",filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if p: self._load_frame_path(p)

    def _load_frame_path(self, p):
        self._fr_rgba = extract_frame(Image.open(p))
        self.lbl_fr.setText(Path(p).name)
        self._cfg["frame_fr"] = p; save_cfg(self._cfg)
        self.btn_save_tpl.setEnabled(self._bg_pil is not None)
        if self._bg_pil: self.canvas.set_images(self._bg_pil, self._fr_rgba); self._apply()

    def _load_preview(self):
        p,_=QFileDialog.getOpenFileName(self,"选择预览背景图",filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        if p: self._load_preview_path(p)

    def _load_preview_path(self, p):
        self._bg_pil = Image.open(p).convert("RGB")
        self.lbl_prev.setText(Path(p).name)
        self._cfg["frame_prev"] = p; save_cfg(self._cfg)
        self.btn_save_tpl.setEnabled(self._fr_rgba is not None)
        self.lbl_save.setEnabled(True)
        self.canvas.set_images(self._bg_pil, self._fr_rgba); self._apply()

    # ── 滑块 ──
    def _on_cx(self,v):    self._apply(cx=v/100)
    def _on_cy(self,v):    self._apply(cy=v/100)
    def _on_scale(self,v): self._apply(scale=v/100)

    def _on_drag(self, cx, cy):
        for sld,spn,v in [(self.sld_cx,self.spn_cx,int(cx*100)),(self.sld_cy,self.spn_cy,int(cy*100))]:
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        self._apply(cx,cy,self.sld_scale.value()/100)

    def _apply(self, cx=None, cy=None, scale=None):
        if cx    is None: cx    = self.sld_cx.value()/100
        if cy    is None: cy    = self.sld_cy.value()/100
        if scale is None: scale = self.sld_scale.value()/100
        self.canvas.set_placement(cx,cy,scale)
        self.lbl_pos.setText(f"水平 {cx:.3f}  垂直 {cy:.3f}  大小 {scale:.3f}")
        if self._bg_pil and self._fr_rgba:
            self._result = frame_composite(self._bg_pil, self._fr_rgba, cx,cy,scale)
        self._save_state()

    # ── 模板 ──
    def _save_tpl(self):
        cx=self.sld_cx.value()/100; cy=self.sld_cy.value()/100; sc=self.sld_scale.value()/100
        self._tpl.record(self._bg_pil, self._fr_rgba, cx,cy,sc)
        self.lbl_tpl.setText("✅ " + self._tpl.summary())
        self.template_updated.emit(self._tpl)
        self._refresh_run_btn()

    def _export_tpl(self):
        if not self._tpl.loaded: QMessageBox.information(self,"提示","请先保存模板"); return
        p,_=QFileDialog.getSaveFileName(self,"导出模板","frame_template.json","JSON (*.json)")
        if not p: return
        with open(p,"w",encoding="utf-8") as f: json.dump(self._tpl.to_dict(),f,ensure_ascii=False,indent=2)
        self._cfg["frame_tpl"]=p; save_cfg(self._cfg)

    def _import_tpl(self):
        p,_=QFileDialog.getOpenFileName(self,"导入模板",filter="JSON (*.json)")
        if p: self._load_tpl_from_file(p)

    def _load_tpl_from_file(self, p):
        with open(p,"r",encoding="utf-8") as f: self._tpl.from_dict(json.load(f))
        self.lbl_tpl.setText("✅ " + self._tpl.summary())
        for sld,spn,v in [(self.sld_cx,self.spn_cx,int(self._tpl.cx*100)),
                          (self.sld_cy,self.spn_cy,int(self._tpl.cy*100)),
                          (self.sld_scale,self.spn_scale,int(self._tpl.scale*100))]:
            sld.blockSignals(True); sld.setValue(v); sld.blockSignals(False)
            spn.blockSignals(True); spn.setValue(v/100); spn.blockSignals(False)
        self._cfg["frame_tpl"]=p; save_cfg(self._cfg)
        self.template_updated.emit(self._tpl)
        self._refresh_run_btn()
        if self._bg_pil and self._fr_rgba:
            self._apply(self._tpl.cx,self._tpl.cy,self._tpl.scale)

    # ── 批量 ──
    def _add_batch(self):
        ps,_=QFileDialog.getOpenFileNames(self,"添加背景图（可多选）",filter="图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*.*)")
        for p in ps:
            if p not in self._batch_paths: self._batch_paths.append(p); self.lst.addItem(Path(p).name)
        self.lbl_count.setText(f"{len(self._batch_paths)} 张")
        self._refresh_run_btn(); self._save_state()

    def _clear_batch(self):
        self._batch_paths.clear(); self.lst.clear(); self.lbl_count.setText("0 张")
        self._refresh_run_btn(); self._save_state()

    def _refresh_run_btn(self):
        self.btn_run.setEnabled(self._fr_rgba is not None and self._tpl.loaded and len(self._batch_paths)>0)

    def _run_batch(self):
        out=QFileDialog.getExistingDirectory(self,"选择输出文件夹")
        if not out: return
        self.btn_run.setEnabled(False); self.prog.setVisible(True)
        self.prog.setMaximum(len(self._batch_paths)); self.prog.setValue(0)
        self._worker=FrameBatchWorker(self._batch_paths,self._fr_rgba,self._tpl,out)
        self._worker.sig_progress.connect(lambda i,n:(self.prog.setValue(i),self.lst.setCurrentRow(i-1)))
        self._worker.sig_error.connect(lambda m: None)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, saved):
        self.btn_run.setEnabled(True); self.prog.setVisible(False)
        QMessageBox.information(self,"完成",f"批量合成完成！共输出 {saved} 张。")

    def _save_one(self):
        if not self._result: return
        p,_=QFileDialog.getSaveFileName(self,"保存结果","合成结果.jpg","JPEG (*.jpg);;PNG (*.png);;所有文件 (*.*)")
        if not p: return
        self._result.save(p,format="PNG" if p.lower().endswith(".png") else "JPEG",quality=95)

    def sync_template(self, tpl: FrameTemplate):
        self._tpl = tpl
        if tpl.loaded: self.lbl_tpl.setText("✅ " + tpl.summary()); self._refresh_run_btn()


# ══════════════════════════════════════════════════════════════
# Tab 2  主图合成
# ══════════════════════════════════════════════════════════════

class MainTab(QWidget):
    _LC = {"✅":"#4ade80","❌":"#f87171","⚠️":"#fbbf24","🚀":"#38bdf8","──":"#303040","🏁":"#c084fc","🖼":"#818cf8"}

    def __init__(self, shared_template: FrameTemplate, cfg: dict, parent=None):
        super().__init__(parent)
        self._tpl = shared_template
        self._cfg = cfg
        self.templates: List[str] = []
        self._worker = None
        self._build()
        self._restore()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,8,0,0); root.setSpacing(10)

        # ── 左控制面板 ──
        lp = QWidget(); lp.setObjectName("panel"); lp.setFixedWidth(300)
        ll = QVBoxLayout(lp); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        sc = QScrollArea(); sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget(); sl = QVBoxLayout(inner); sl.setContentsMargins(14,14,10,10); sl.setSpacing(0)

        # 路径
        sl.addWidget(sec("路  径")); sl.addSpacing(8)
        self.row_in  = PathRow("📂","输入文件夹（照片）")
        self.row_out = PathRow("💾","输出文件夹")
        sl.addWidget(self.row_in); sl.addSpacing(6); sl.addWidget(self.row_out)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # PNG 模板
        sl.addWidget(sec("PNG 模板")); sl.addSpacing(8)
        bt = QHBoxLayout(); bt.setSpacing(8)
        self.btn_add_tpl = QPushButton("＋ 添加"); self.btn_add_tpl.setObjectName("btnGreen"); self.btn_add_tpl.setFixedHeight(32)
        self.btn_del_tpl = QPushButton("－ 删除"); self.btn_del_tpl.setObjectName("btnRed");   self.btn_del_tpl.setFixedHeight(32)
        self.btn_add_tpl.clicked.connect(self._add_tpl); self.btn_del_tpl.clicked.connect(self._del_tpl)
        bt.addWidget(self.btn_add_tpl,1); bt.addWidget(self.btn_del_tpl,1)
        sl.addLayout(bt); sl.addSpacing(8)
        self.tpl_list = QListWidget(); self.tpl_list.setFixedHeight(100)
        self.tpl_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.tpl_list)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # 坐标模式
        sl.addWidget(sec("填入坐标")); sl.addSpacing(8)
        self.rb_auto  = QRadioButton("自动检测透明区域")
        self.rb_share = QRadioButton("使用 Tab1 相框坐标（推荐）")
        self.rb_share.setChecked(True)
        bg = QButtonGroup(self); bg.addButton(self.rb_auto); bg.addButton(self.rb_share)
        sl.addWidget(self.rb_auto); sl.addSpacing(4); sl.addWidget(self.rb_share); sl.addSpacing(8)

        self.coord_lbl = QLabel("尚无坐标（请在 Tab1 保存/导入模板）")
        self.coord_lbl.setStyleSheet("color:#404058;font-size:10.5px;background:transparent;")
        self.coord_lbl.setWordWrap(True); sl.addWidget(self.coord_lbl)
        sl.addSpacing(16); sl.addWidget(div()); sl.addSpacing(16)

        # 输出规格
        sl.addWidget(sec("输出规格")); sl.addSpacing(8)
        self.cmb = QComboBox()
        for p in ["正方形  800×800","正方形  1000×1000","正方形  1200×1200","竖版 5:7  1500×2100","横版 7:5  2100×1500","自定义…"]:
            self.cmb.addItem(p)
        self.cmb.currentIndexChanged.connect(self._on_preset)
        self.cmb.wheelEvent = lambda e: e.ignore()
        sl.addWidget(self.cmb); sl.addSpacing(10)

        def mk(lo,hi,val,suf):
            s=QSpinBox(); s.setRange(lo,hi); s.setValue(val); s.setSuffix(suf)
            s.wheelEvent=lambda e:e.ignore(); return s

        self.spn_w=mk(100,9999,800," px"); self.spn_h=mk(100,9999,800," px")
        self.spn_dpi=mk(72,600,300," DPI"); self.spn_q=mk(80,100,95," %")

        def lw(txt,w):
            wr=QWidget(); r=QHBoxLayout(wr); r.setContentsMargins(0,0,0,0); r.setSpacing(6)
            l=QLabel(txt); l.setFixedWidth(28); l.setStyleSheet("color:#606070;font-size:11px;background:transparent;")
            r.addWidget(l); r.addWidget(w,1); return wr

        g1=QHBoxLayout(); g1.setSpacing(10); g2=QHBoxLayout(); g2.setSpacing(10)
        g1.addWidget(lw("宽",self.spn_w),1); g1.addWidget(lw("高",self.spn_h),1)
        g2.addWidget(lw("DPI",self.spn_dpi),1); g2.addWidget(lw("品质",self.spn_q),1)
        sl.addLayout(g1); sl.addSpacing(8); sl.addLayout(g2); sl.addStretch()

        sc.setWidget(inner); ll.addWidget(sc,1)

        # 底部固定
        bot=QWidget(); bot.setStyleSheet("background:transparent;")
        bl=QVBoxLayout(bot); bl.setContentsMargins(14,8,14,12); bl.setSpacing(6)
        self.prog=QProgressBar(); self.prog.setFixedHeight(4); self.prog.setTextVisible(False)
        self.btn_start=QPushButton("🚀  开始批量合成主图")
        self.btn_start.setObjectName("btnPrimary"); self.btn_start.clicked.connect(self._start)
        bl.addWidget(self.prog); bl.addWidget(self.btn_start)
        ll.addWidget(bot); root.addWidget(lp)

        # ── 右日志区 ──
        rp=QWidget(); rp.setObjectName("rpanel")
        rl=QVBoxLayout(rp); rl.setContentsMargins(14,14,14,14); rl.setSpacing(10)
        lh=QHBoxLayout(); lh.addWidget(sec("处 理 日 志")); lh.addStretch()
        bc=QPushButton("清空"); bc.setObjectName("btnClear"); bc.clicked.connect(lambda:self.log_box.clear())
        lh.addWidget(bc); rl.addLayout(lh)
        self.log_box=QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("日志将在这里实时显示…")
        rl.addWidget(self.log_box,1); root.addWidget(rp,1)

    def _restore(self):
        c=self._cfg
        if c.get("main_inp"):  self.row_in.set_path(c["main_inp"])
        if c.get("main_out"):  self.row_out.set_path(c["main_out"])
        if c.get("main_size"): self.cmb.setCurrentIndex(c["main_size"])
        if c.get("main_dpi"):  self.spn_dpi.setValue(c["main_dpi"])
        if c.get("main_q"):    self.spn_q.setValue(c["main_q"])
        if c.get("main_tpls"):
            for f in c["main_tpls"]:
                if Path(f).exists() and f not in self.templates:
                    self.templates.append(f); self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self._refresh_coord_lbl()

    def _save_state(self):
        self._cfg.update({
            "main_inp":  self.row_in.path(),
            "main_out":  self.row_out.path(),
            "main_size": self.cmb.currentIndex(),
            "main_dpi":  self.spn_dpi.value(),
            "main_q":    self.spn_q.value(),
            "main_tpls": self.templates,
        }); save_cfg(self._cfg)

    _P={0:(800,800),1:(1000,1000),2:(1200,1200),3:(1500,2100),4:(2100,1500)}
    def _on_preset(self,idx):
        if idx in self._P:
            w,h=self._P[idx]
            for s,v in[(self.spn_w,w),(self.spn_h,h)]:
                s.blockSignals(True);s.setValue(v);s.blockSignals(False)

    def _add_tpl(self):
        fs,_=QFileDialog.getOpenFileNames(self,"选择 PNG 模板",filter="PNG (*.png);;所有文件 (*.*)")
        for f in fs:
            if f not in self.templates: self.templates.append(f); self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self._save_state()

    def _del_tpl(self):
        for item in reversed(self.tpl_list.selectedItems()):
            r=self.tpl_list.row(item); self.tpl_list.takeItem(r); self.templates.pop(r)
        self._save_state()

    def _refresh_coord_lbl(self):
        if self._tpl.loaded:
            self.coord_lbl.setText("✅ " + self._tpl.summary())
        else:
            self.coord_lbl.setText("尚无坐标（请在 Tab1 保存/导入模板）")

    def sync_template(self, tpl: FrameTemplate):
        self._tpl = tpl; self._refresh_coord_lbl()

    def _log(self, msg):
        color="#606072"
        for k,c in self._LC.items():
            if msg.startswith(k): color=c; break
        self.log_box.append(f'<span style="color:{color};font-family:Consolas,monospace;">{msg}</span>')
        sb=self.log_box.verticalScrollBar(); sb.setValue(sb.maximum())

    def _on_prog(self,cur,total): self.prog.setMaximum(total); self.prog.setValue(cur)

    def _on_done(self,ok,fail):
        self.btn_start.setEnabled(True); self.btn_start.setText("🚀  开始批量合成主图")
        self.prog.setValue(self.prog.maximum()); self._log(f"\n🏁  完成 — 成功 {ok} 张  失败 {fail} 张")
        out=self.row_out.path()
        (QMessageBox.information if fail==0 else QMessageBox.warning)(
            self,"完成",f"成功合成 {ok} 张\n\n{out}" if fail==0 else f"成功 {ok}  失败 {fail}\n\n{out}")

    def _start(self):
        inp=self.row_in.path(); out=self.row_out.path()
        if not inp or not os.path.isdir(inp): QMessageBox.warning(self,"提示","请选择输入文件夹"); return
        if not out: QMessageBox.warning(self,"提示","请选择输出文件夹"); return
        if not self.templates: QMessageBox.warning(self,"提示","请添加 PNG 模板"); return
        use_tpl = self.rb_share.isChecked()
        if use_tpl and not self._tpl.loaded:
            QMessageBox.warning(self,"提示","已选择「相框坐标」模式，但 Tab1 尚无模板\n请先在 Tab1 完成定位并保存模板"); return
        files=[f for f in Path(inp).iterdir() if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        if not files: QMessageBox.warning(self,"提示","未找到图片"); return
        n=len(files)
        self.prog.setValue(0); self.prog.setMaximum(n)
        self.btn_start.setEnabled(False); self.btn_start.setText("合成中…")
        self._log(f"🚀  开始  {n} 张 · {len(self.templates)} 个模板 · {'相框坐标' if use_tpl else '自动检测'}")
        self._save_state()
        self._worker=MainBatchWorker(inp,out,self.templates,self.spn_w.value(),self.spn_h.value(),
                                     self.spn_dpi.value(),self.spn_q.value(),use_tpl,self._tpl)
        self._worker.sig_log.connect(self._log); self._worker.sig_prog.connect(self._on_prog)
        self._worker.sig_done.connect(self._on_done); self._worker.start()


# ══════════════════════════════════════════════════════════════
# 主窗口
# ══════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片处理工具")
        self.setMinimumSize(900, 620); self.resize(1100, 720)
        self._cfg = load_cfg()
        self._tpl = FrameTemplate()

        self._build_ui()
        self.setStyleSheet(QSS)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪  ·  Tab1 调好相框位置后，Tab2 直接批量合成主图")

    def _build_ui(self):
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root)
        rl = QVBoxLayout(root); rl.setContentsMargins(14,12,14,10); rl.setSpacing(10)

        # 顶栏
        hdr = QHBoxLayout()
        t = QLabel("照片处理工具"); t.setStyleSheet("color:#dddde8;font-size:16px;font-weight:700;")
        s = QLabel("相框合成  ·  主图合成  ·  模板共享"); s.setStyleSheet("color:#28283a;font-size:11px;")
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(s)
        rl.addLayout(hdr)

        # 细线
        ln = QFrame(); ln.setObjectName("div"); ln.setFrameShape(QFrame.Shape.HLine)
        rl.addWidget(ln)

        # Tab
        self.tabs = QTabWidget()
        self.tab_frame = FrameTab(self._tpl, self._cfg)
        self.tab_main  = MainTab( self._tpl, self._cfg)

        # 模板同步：两个 Tab 共享同一个 FrameTemplate 对象，Tab1 保存后通知 Tab2 刷新显示
        self.tab_frame.template_updated.connect(self.tab_main.sync_template)

        self.tabs.addTab(self.tab_frame, "  📐  Tab1 · 相框合成  ")
        self.tabs.addTab(self.tab_main,  "  🖼   Tab2 · 主图合成  ")
        rl.addWidget(self.tabs, 1)

    def closeEvent(self, e):
        save_cfg(self._cfg); super().closeEvent(e)


# ══════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════

def main():
    if sys.platform == "win32":
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ralo.photo_tool.v1")
        except: pass
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    app = QApplication(sys.argv); app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(17,17,19))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(221,221,229))
    p.setColor(QPalette.ColorRole.Base,            QColor(14,14,18))
    p.setColor(QPalette.ColorRole.Text,            QColor(200,200,212))
    p.setColor(QPalette.ColorRole.Button,          QColor(28,28,34))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(200,200,212))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(10,132,255))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
    app.setPalette(p)
    win = MainWindow(); win.show(); sys.exit(app.exec())

if __name__ == "__main__":
    main()