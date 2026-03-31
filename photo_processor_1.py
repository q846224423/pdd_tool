"""
主图合成工具 v7  —  纯净 JSON 坐标物理内嵌版 (无预览精简版)
pip install PyQt6 pillow numpy
"""

import sys, os, json, ctypes, logging
from pathlib import Path
from typing  import Optional, List

import numpy as np
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QFileDialog, QFrame,
    QStatusBar, QMessageBox, QAbstractItemView, QSplitter,
    QSpinBox, QComboBox, QScrollArea
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QSettings
from PyQt6.QtGui   import QColor, QPalette

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
APP_ORG  = "Ralo"
APP_NAME = "CompositeMain"

QSS = """
* { box-sizing: border-box; outline: none; }
QMainWindow { background-color: #111113; }
QWidget {
    color: #dddde5;
    font-family: "Microsoft YaHei UI","PingFang SC","SF Pro Display",sans-serif;
    font-size: 13px; background: transparent;
}
QWidget#centralWidget { background-color: #111113; }
QWidget#leftPanel  { background: #161619; border: 1px solid #24242c; border-radius: 12px; }
QWidget#rightPanel { background: #161619; border: 1px solid #24242c; border-radius: 12px; }

QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #2a2a36; border-radius: 2px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #3a3a48; }

QLineEdit {
    background-color: #1e1e24; border: 1px solid #2c2c36;
    border-radius: 7px; padding: 8px 10px; color: #aaaab8; font-size: 12px;
}
QLineEdit:focus { border-color: #2c2c36; }

QListWidget {
    background-color: #1a1a20; border: 1px solid #2c2c36;
    border-radius: 8px; color: #c0c0cc; outline: none; padding: 3px; font-size: 12px;
}
QListWidget::item { padding: 7px 10px; border-radius: 5px; color: #c0c0cc; }
QListWidget::item:selected { background-color: #0a84ff; color: #fff; }
QListWidget::item:hover:!selected { background-color: #2a2a36; }

QPushButton {
    background-color: #2c2c36; color: #e0e0e0;
    border-radius: 7px; padding: 8px 14px;
    font-weight: 600; font-size: 13px; border: none; outline: none;
}
QPushButton:hover { background-color: #3a3a48; }

/* ========================================================= */
/* 开始批量合成按钮 - 立体渐变物理按压样式 */
/* ========================================================= */
QPushButton#btnStart {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2591ff, stop:1 #0073ea);
    border: 1px solid #005bb8;      
    border-top: 1px solid #5ab0ff;  
    color: #ffffff;                 
    font-size: 15px; 
    font-weight: 800;               
    letter-spacing: 2px;            
    padding: 12px 0px;              
    border-radius: 8px;             
}
QPushButton#btnStart:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #47a3ff, stop:1 #0a80f5);
    border-top: 1px solid #7bc0ff;  
}
QPushButton#btnStart:pressed { 
    background: #005ac8;      
    border: 1px solid #00408a;      
    padding-top: 14px; 
    padding-bottom: 10px; 
}
QPushButton#btnStart:disabled { 
    background: #24242c; 
    border: 1px solid #1e1e28;
    color: #505060; 
}
/* ========================================================= */

QPushButton#btnBrowse {
    background-color: #2a2a36; color: #c0c0d0;
    border: 1px solid #4a4a5a; font-size: 12px; padding: 8px 14px;
}
QPushButton#btnBrowse:hover { background-color: #3a3a48; color: #fff; border-color: #6a6a7a; }

QPushButton#btnAdd {
    background-color: rgba(40,196,84,0.15); color: #4ade80;
    border: 1px solid rgba(40,196,84,0.4); font-size: 12px; font-weight: 600;
}
QPushButton#btnAdd:hover { background-color: rgba(40,196,84,0.25); border-color: #4ade80; }

QPushButton#btnDel {
    background-color: rgba(240,64,48,0.15); color: #f87171;
    border: 1px solid rgba(240,64,48,0.4); font-size: 12px; font-weight: 600;
}
QPushButton#btnDel:hover { background-color: rgba(240,64,48,0.25); border-color: #f87171; }

QPushButton#btnImport {
    background-color: rgba(191,90,242,0.13); color: #d070f0;
    border: 1px solid rgba(191,90,242,0.35); font-size: 12px; font-weight: 600;
    padding: 8px 0; border-radius: 7px;
}
QPushButton#btnImport:hover { background-color: rgba(191,90,242,0.24); border-color: #c070e0; }

QPushButton#btnClear {
    background-color: rgba(255,255,255,0.05); color: #a0a0b0;
    border: 1px solid rgba(255,255,255,0.15); padding: 4px 12px;
    font-size: 11px; border-radius: 6px;
}
QPushButton#btnClear:hover { background-color: rgba(255,255,255,0.1); color: #fff; }

QWidget#coordBox {
    background: #1a1a26; border: 1px solid #2c2c42;
    border-radius: 8px;
}
QWidget#botArea { background: transparent; }

QComboBox {
    background-color: #1e1e24; border: 1px solid #2c2c36;
    border-radius: 7px; padding: 7px 10px; color: #aaaab8; font-size: 12px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #20202a; border: 1px solid #32323e;
    color: #c0c0d0; selection-background-color: #0a84ff; outline: none;
}

QSpinBox {
    background-color: #1e1e24; border: 1px solid #2c2c36;
    border-radius: 7px; padding: 7px 8px; color: #aaaab8; font-size: 12px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #2a2a36; border: none; width: 16px; border-radius: 3px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #4a4a5a; }

QProgressBar {
    background-color: #1a1a22; border: 1px solid #24242c;
    border-radius: 3px; height: 6px; color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0a84ff,stop:1 #5ac8fa);
    border-radius: 2px;
}

QTextEdit {
    background-color: #0e0e14; border: 1px solid #1e1e28;
    border-radius: 9px; color: #808090;
    font-family: "Cascadia Code","Consolas","Courier New",monospace;
    font-size: 11.5px; padding: 10px;
}

QStatusBar {
    background-color: #0c0c12; border-top: 1px solid #1a1a22;
    color: #606070; font-size: 11px; padding: 2px 14px;
}
QFrame#divider { background-color: #2c2c36; border: none; max-height: 1px; }
"""

# ─────────────────────────────────────────────────────────────
# 核心图像处理：物理挖洞内嵌 (基于精准 JSON 坐标)
# ─────────────────────────────────────────────────────────────

def composite_exact_json(photo: Image.Image, tpl_path: str,
                         left: int, top: int, fw: int, fh: int,
                         out_w: int, out_h: int) -> Image.Image:
    """
    根据 JSON 提供的准确绝对像素坐标，在相框内物理挖洞，将照片刚好镶嵌填充
    """
    tpl = Image.open(tpl_path).convert("RGBA")
    tw, th = tpl.size

    # 防呆机制：如果 JSON 没有尺寸或尺寸异常，默认用全图
    if fw <= 0 or fh <= 0:
        left, top, fw, fh = 0, 0, tw, th

    # 1. 物理挖洞：直接将目标矩形区域的 Alpha 通道刮成 0
    alpha = tpl.split()[3]
    draw_alpha = ImageDraw.Draw(alpha)
    draw_alpha.rectangle([left, top, left + fw, top + fh], fill=0)
    tpl.putalpha(alpha)

    # 2. 处理照片：等比拉伸、居中裁剪，使其完美填充目标洞口尺寸
    p = photo.convert("RGBA")
    sc = max(fw / p.width, fh / p.height)
    p = p.resize((max(1, int(p.width * sc)), max(1, int(p.height * sc))), Image.LANCZOS)
    lc, tc = (p.width - fw) // 2, (p.height - fh) // 2
    p = p.crop((lc, tc, lc + fw, tc + fh))

    # 3. 组装合成：创建底层白画布 -> 居中平移后的照片 -> 顶层挖了洞的相框
    canvas = Image.new("RGBA", (tw, th), (255, 255, 255, 255))
    canvas.paste(p, (left, top))
    result = Image.alpha_composite(canvas, tpl).convert("RGB")

    # 4. 按需输出分辨率
    if out_w > 0 and out_h > 0:
        result = result.resize((out_w, out_h), Image.LANCZOS)
    return result


class Worker(QThread):
    sig_log  = pyqtSignal(str)
    sig_prog = pyqtSignal(int, int)
    sig_done = pyqtSignal(int, int)

    def __init__(self, inp, out, templates, out_w, out_h, dpi, quality,
                 tpl_left, tpl_top, tpl_fw, tpl_fh):
        super().__init__()
        self.inp, self.out = inp, out
        self.templates = templates
        self.out_w, self.out_h, self.dpi, self.quality = out_w, out_h, dpi, quality
        self.tpl_left, self.tpl_top, self.tpl_fw, self.tpl_fh = tpl_left, tpl_top, tpl_fw, tpl_fh

    def run(self):
        files = [f for f in Path(self.inp).iterdir()
                 if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        total = len(files); ok = fail = 0
        Path(self.out).mkdir(parents=True, exist_ok=True)
        for i, src in enumerate(files):
            self.sig_log.emit(f"\n── [{i+1}/{total}]  {src.name}")
            try:
                photo = Image.open(src).convert("RGB")
                for tp_str in self.templates:
                    tp = Path(tp_str)
                    if not tp.exists():
                        self.sig_log.emit(f"⚠️  模板不存在: {tp.name}"); continue
                    suf  = f"_{tp.stem}" if len(self.templates) > 1 else ""
                    name = f"主图_{src.stem}{suf}.jpg"
                    self.sig_log.emit(f"🖼   {tp.name}  →  {name}")

                    # 批量时强制使用 JSON 坐标挖洞合成
                    r = composite_exact_json(
                        photo, tp_str,
                        self.tpl_left, self.tpl_top, self.tpl_fw, self.tpl_fh,
                        self.out_w, self.out_h
                    )

                    r.save(str(Path(self.out)/name), "JPEG",
                           quality=self.quality, dpi=(self.dpi,self.dpi))
                    self.sig_log.emit(f"✅  {name}")
                ok += 1
            except Exception as e:
                self.sig_log.emit(f"❌  {e}"); fail += 1
            self.sig_prog.emit(i+1, total)
        self.sig_done.emit(ok, fail)


# ─────────────────────────────────────────────────────────────
# UI 基础组件
# ─────────────────────────────────────────────────────────────

class NoScrollSpinBox(QSpinBox):
    def wheelEvent(self, e): e.ignore()

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, e): e.ignore()

class StatCard(QFrame):
    def __init__(self, title, val="—", color="#0a84ff", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self._color = color; self._apply()
        lay = QVBoxLayout(self); lay.setContentsMargins(10,14,10,14); lay.setSpacing(4)
        self._v = QLabel(val); self._v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._v.setStyleSheet(f"color:{color};font-size:28px;font-weight:800;background:transparent;border:none;")
        t = QLabel(title); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("color:#606070;font-size:10px;font-weight:600;letter-spacing:2px;background:transparent;border:none;")
        lay.addWidget(self._v); lay.addWidget(t)

    def _apply(self):
        self.setStyleSheet(f"QFrame#statCard{{background:#181820;border:1px solid #24242e;border-top:2px solid {self._color};border-radius:10px;}}")

    def set_value(self, v): self._v.setText(str(v))

class PathRow(QWidget):
    def __init__(self, icon, placeholder, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(8)
        ico = QLabel(icon); ico.setFixedWidth(20)
        ico.setStyleSheet("font-size:15px;background:transparent;color:#707080;")
        self.edit = QLineEdit(); self.edit.setPlaceholderText(placeholder)
        self.edit.setReadOnly(True)
        btn = QPushButton("浏览"); btn.setObjectName("btnBrowse")
        btn.setFixedWidth(54); btn.clicked.connect(self._browse)
        lay.addWidget(ico); lay.addWidget(self.edit,1); lay.addWidget(btn)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self,"选择文件夹")
        if d: self.edit.setText(d)

    def path(self): return self.edit.text().strip()
    def set_path(self, p): self.edit.setText(p)

def divider():
    f = QFrame(); f.setObjectName("divider"); f.setFrameShape(QFrame.Shape.HLine); return f

def sec(text):
    l = QLabel(text)
    l.setStyleSheet("color:#606070;font-size:10px;font-weight:700;letter-spacing:2.5px;background:transparent;")
    return l


# ─────────────────────────────────────────────────────────────
# 主窗口
# ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    _LC = {
        "✅":"#4ade80","❌":"#f87171","⚠️":"#fbbf24",
        "🚀":"#38bdf8","──":"#404050","🏁":"#c084fc","🖼":"#818cf8",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("主图合成工具 (无预览批量纯净版)")
        self.setMinimumSize(860, 620)
        self.resize(960, 720)

        self.templates: List[str] = []
        self._worker: Optional[Worker] = None

        # JSON 精确坐标存储变量
        self._tpl_left = 0
        self._tpl_top  = 0
        self._tpl_fw   = 0
        self._tpl_fh   = 0
        self._tpl_json_path = ""

        self._settings = QSettings(APP_ORG, APP_NAME)
        self._build_ui()
        self.setStyleSheet(QSS)
        self.setStatusBar(QStatusBar())
        self._load_settings()
        self.statusBar().showMessage("就绪")

    def _load_settings(self):
        s = self._settings
        inp = s.value("inp_dir", "")
        out = s.value("out_dir", "")
        if inp: self.row_in.set_path(inp)
        if out: self.row_out.set_path(out)

        saved_tpls = s.value("templates", [])
        if isinstance(saved_tpls, str): saved_tpls = [saved_tpls]
        for f in saved_tpls:
            if Path(f).exists() and f not in self.templates:
                self.templates.append(f)
                self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self.c_tpl.set_value(len(self.templates))

        tpl_json = s.value("tpl_json_path","")
        if tpl_json and Path(tpl_json).exists():
            self._load_tpl_json(tpl_json, silent=True)

        idx = s.value("preset_idx", 0, type=int)
        self.cmb.setCurrentIndex(idx)
        self.spn_w.setValue(s.value("out_w", 800, type=int))
        self.spn_h.setValue(s.value("out_h", 800, type=int))
        self.spn_dpi.setValue(s.value("out_dpi", 300, type=int))
        self.spn_q.setValue(s.value("out_q", 95, type=int))

        self._check_run_ready()

    def _save_settings(self):
        s = self._settings
        s.setValue("inp_dir",      self.row_in.path())
        s.setValue("out_dir",      self.row_out.path())
        s.setValue("templates",    self.templates)
        s.setValue("tpl_json_path",self._tpl_json_path)
        s.setValue("preset_idx",   self.cmb.currentIndex())
        s.setValue("out_w",        self.spn_w.value())
        s.setValue("out_h",        self.spn_h.value())
        s.setValue("out_dpi",      self.spn_dpi.value())
        s.setValue("out_q",        self.spn_q.value())

    def closeEvent(self, e):
        self._save_settings(); super().closeEvent(e)

    def _build_ui(self):
        cw = QWidget(); cw.setObjectName("centralWidget")
        self.setCentralWidget(cw)
        root = QVBoxLayout(cw)
        root.setContentsMargins(16,14,16,10); root.setSpacing(12)

        hdr = QHBoxLayout()
        t = QLabel("主图相框合成"); t.setStyleSheet("color:#fff;font-size:16px;font-weight:700;")
        s = QLabel("纯净自动化 · JSON精准坐标切割内嵌"); s.setStyleSheet("color:#606070;font-size:11px;")
        hdr.addWidget(t); hdr.addStretch(); hdr.addWidget(s)
        root.addLayout(hdr)

        cards = QHBoxLayout(); cards.setSpacing(8)
        self.c_total = StatCard("待处理","—","#0a84ff")
        self.c_ok    = StatCard("已成功","—","#28c454")
        self.c_fail  = StatCard("失败","—","#f04030")
        self.c_tpl   = StatCard("模板","0","#bf5af2")
        for c in (self.c_total,self.c_ok,self.c_fail,self.c_tpl):
            cards.addWidget(c,1)
        root.addLayout(cards)

        sp = QSplitter(Qt.Orientation.Horizontal); sp.setHandleWidth(1)
        sp.setStyleSheet("QSplitter::handle{background:#1e1e28;}")

        # ════ 左控制面板 ════
        lw = QWidget()
        lw.setStyleSheet("QWidget#lp{background:#161619;border:1px solid #22222e;border-radius:12px;}")
        lw.setObjectName("lp"); lw.setFixedWidth(400)
        ll = QVBoxLayout(lw); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        si = QWidget(); sl = QVBoxLayout(si)
        sl.setContentsMargins(16,16,16,12); sl.setSpacing(0)

        # ── 1. 路径 ──
        sl.addWidget(sec("1. 文件夹路径")); sl.addSpacing(10)
        self.row_in  = PathRow("📂","输入图库（待处理原图）")
        self.row_out = PathRow("💾","输出位置（保存合成结果）")
        sl.addWidget(self.row_in); sl.addSpacing(8); sl.addWidget(self.row_out)
        sl.addSpacing(18); sl.addWidget(divider()); sl.addSpacing(18)

        # ── 2. 相框模板 ──
        sl.addWidget(sec("2. 导入相框图纸 (支持PNG/JPG)")); sl.addSpacing(10)
        btn_tpl = QHBoxLayout(); btn_tpl.setSpacing(8)

        self.btn_add = QPushButton("＋  添加模板"); self.btn_add.setObjectName("btnAdd"); self.btn_add.setFixedHeight(36)
        self.btn_sel_all = QPushButton("☑  全选"); self.btn_sel_all.setObjectName("btnBrowse"); self.btn_sel_all.setFixedHeight(36)
        self.btn_del = QPushButton("－  删除"); self.btn_del.setObjectName("btnDel"); self.btn_del.setFixedHeight(36)

        btn_tpl.addWidget(self.btn_add,3); btn_tpl.addWidget(self.btn_sel_all,2); btn_tpl.addWidget(self.btn_del,2)
        sl.addLayout(btn_tpl); sl.addSpacing(8)

        self.tpl_list = QListWidget(); self.tpl_list.setFixedHeight(120)
        self.tpl_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        sl.addWidget(self.tpl_list)

        self.btn_add.clicked.connect(self._add_tpl)
        self.btn_sel_all.clicked.connect(self.tpl_list.selectAll)
        self.btn_del.clicked.connect(self._del_tpl)
        self.tpl_list.itemSelectionChanged.connect(self._check_run_ready)

        sl.addSpacing(18); sl.addWidget(divider()); sl.addSpacing(18)

        # ── 3. JSON 坐标系 ──
        sl.addWidget(sec("3. 导入 JSON 挖洞坐标系 (必须)")); sl.addSpacing(10)

        self.btn_import_coord = QPushButton("📥  选择坐标 JSON (.json)")
        self.btn_import_coord.setObjectName("btnImport")
        self.btn_import_coord.setFixedHeight(38)
        self.btn_import_coord.clicked.connect(self._import_coord)
        sl.addWidget(self.btn_import_coord); sl.addSpacing(8)

        coord_box = QWidget(); coord_box.setObjectName("coordBox")
        cb_lay = QVBoxLayout(coord_box); cb_lay.setContentsMargins(12,10,12,10); cb_lay.setSpacing(4)
        self.lbl_coord_mode = QLabel("状态：尚未导入坐标")
        self.lbl_coord_mode.setStyleSheet("color:#8888a0;font-size:11px;background:transparent;font-weight:600;")
        self.lbl_coord_detail = QLabel("程序需要依靠 JSON 指定的边距和宽高，在相框图上精确切割出透明洞口，才能进行照片内嵌合成。")
        self.lbl_coord_detail.setStyleSheet("color:#f87171;font-size:10.5px;background:transparent; line-height: 1.4;")
        self.lbl_coord_detail.setWordWrap(True)
        cb_lay.addWidget(self.lbl_coord_mode)
        cb_lay.addWidget(self.lbl_coord_detail)
        sl.addWidget(coord_box)

        sl.addSpacing(18); sl.addWidget(divider()); sl.addSpacing(18)

        # ── 4. 规格 ──
        sl.addWidget(sec("4. 最终输出规格")); sl.addSpacing(10)
        self.cmb = NoScrollComboBox()
        for p in ["正方形  800×800","正方形  1000×1000","正方形  1200×1200",
                  "竖版 5:7  1500×2100","横版 7:5  2100×1500","自定义…"]:
            self.cmb.addItem(p)
        self.cmb.currentIndexChanged.connect(self._on_preset)
        sl.addWidget(self.cmb); sl.addSpacing(10)

        g1 = QHBoxLayout(); g1.setSpacing(10)
        g2 = QHBoxLayout(); g2.setSpacing(10)

        def mk_spin(lo,hi,val,suf):
            s=NoScrollSpinBox(); s.setRange(lo,hi); s.setValue(val); s.setSuffix(suf); return s

        self.spn_w   = mk_spin(100,9999,800," px")
        self.spn_h   = mk_spin(100,9999,800," px")
        self.spn_dpi = mk_spin(72,600,300," DPI")
        self.spn_q   = mk_spin(80,100,95," %")

        def labeled(lt,widget):
            w=QWidget(); r=QHBoxLayout(w); r.setContentsMargins(0,0,0,0); r.setSpacing(6)
            l=QLabel(lt); l.setStyleSheet("color:#707080;font-size:11px;background:transparent;"); l.setFixedWidth(30)
            r.addWidget(l); r.addWidget(widget,1); return w

        g1.addWidget(labeled("宽",self.spn_w),1); g1.addWidget(labeled("高",self.spn_h),1)
        g2.addWidget(labeled("DPI",self.spn_dpi),1); g2.addWidget(labeled("品质",self.spn_q),1)
        sl.addLayout(g1); sl.addSpacing(8); sl.addLayout(g2); sl.addSpacing(16)
        sl.addStretch()

        # 装载进 scroll
        scroll.setWidget(si); ll.addWidget(scroll,1)

        # ── 底部区 ──
        bot = QWidget()
        bot.setObjectName("botArea")
        bl = QVBoxLayout(bot); bl.setContentsMargins(16,8,16,14); bl.setSpacing(8)

        self.btn_start = QPushButton("🚀  开始一键批量合成")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._start)

        self.prog = QProgressBar(); self.prog.setFixedHeight(4)
        self.prog.setTextVisible(False); self.prog.setVisible(False)

        bl.addWidget(self.btn_start); bl.addWidget(self.prog)

        # 将底部按钮区装载进左面板
        ll.addWidget(bot)

        # 【修复点】：将整体左面板添加到 Splitter
        sp.addWidget(lw)

        # ════ 右侧区 (纯净日志) ════
        right_outer = QWidget()
        ro = QVBoxLayout(right_outer); ro.setContentsMargins(6,0,0,0); ro.setSpacing(0)
        right = QWidget(); right.setObjectName("rightPanel")
        rl = QVBoxLayout(right); rl.setContentsMargins(16,14,16,14); rl.setSpacing(10)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(sec("处 理 日 志")); log_hdr.addStretch()
        bc = QPushButton("清空"); bc.setObjectName("btnClear")
        bc.clicked.connect(lambda: self.log_box.clear())
        log_hdr.addWidget(bc); rl.addLayout(log_hdr)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("所有处理记录将在这里实时全屏滚动显示…")
        rl.addWidget(self.log_box, 1)

        ro.addWidget(right); sp.addWidget(right_outer)
        sp.setSizes([400, 620]); root.addWidget(sp,1)

    _P = {0:(800,800),1:(1000,1000),2:(1200,1200),3:(1500,2100),4:(2100,1500)}
    def _on_preset(self,idx):
        if idx in self._P:
            w,h=self._P[idx]
            for s,v in [(self.spn_w,w),(self.spn_h,h)]:
                s.blockSignals(True); s.setValue(v); s.blockSignals(False)

    def _check_run_ready(self):
        # 要激活按钮，必须：模板列表有图 + JSON坐标就位
        ok = (len(self.templates) > 0 and self._tpl_fw > 0)
        self.btn_start.setEnabled(ok)

    def _add_tpl(self):
        fs,_=QFileDialog.getOpenFileNames(self,"选择相框模板",filter="图片 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)")
        for f in fs:
            if f not in self.templates:
                self.templates.append(f)
                self.tpl_list.addItem(QListWidgetItem(f"  {Path(f).name}"))
        self.c_tpl.set_value(len(self.templates))
        self._check_run_ready()

    def _del_tpl(self):
        for item in reversed(self.tpl_list.selectedItems()):
            r=self.tpl_list.row(item); self.tpl_list.takeItem(r); self.templates.pop(r)
        self.c_tpl.set_value(len(self.templates))
        self._check_run_ready()

    def _import_coord(self):
        p,_=QFileDialog.getOpenFileName(self,"导入相框 JSON",filter="JSON (*.json)")
        if not p: return
        self._load_tpl_json(p, silent=False)

    def _load_tpl_json(self, path: str, silent=False):
        try:
            with open(path,"r",encoding="utf-8") as f:
                d = json.load(f)

            # 提取 JSON 的绝对物理坐标
            self._tpl_left = int(d.get("left",  0))
            self._tpl_top  = int(d.get("top",   0))
            self._tpl_fw   = int(d.get("frame_w",0))
            self._tpl_fh   = int(d.get("frame_h",0))
            self._tpl_json_path = path

            self.lbl_coord_mode.setText("✅  物理切片模式已就绪")
            self.lbl_coord_mode.setStyleSheet("color:#4ade80;font-size:12px;background:transparent;font-weight:600;")

            self.lbl_coord_detail.setText(
                f"源文件: {Path(path).name}\n"
                f"切口起点: X: {self._tpl_left}px,  Y: {self._tpl_top}px\n"
                f"相框内板: 宽 {self._tpl_fw}px × 高 {self._tpl_fh}px\n"
                f"引擎状态: 随时准备切图合成！"
            )
            self.lbl_coord_detail.setStyleSheet("color:#a0a0b4;font-size:11px; line-height:1.4;")

            self._check_run_ready()
            if not silent:
                self.statusBar().showMessage(f"✅ 坐标已应用: {Path(path).name}")
        except Exception as e:
            if not silent:
                QMessageBox.warning(self,"导入失败",f"读取坐标失败：\n{e}")

    def _log(self, msg):
        color="#808090"
        for k,c in self._LC.items():
            if msg.startswith(k): color=c; break
        self.log_box.append(f'<span style="color:{color};font-family:Consolas,monospace;">{msg}</span>')
        sb=self.log_box.verticalScrollBar(); sb.setValue(sb.maximum())

    def _on_prog(self,cur,total):
        self.prog.setMaximum(total); self.prog.setValue(cur)
        self.statusBar().showMessage(f"合成中  {cur} / {total}")

    def _on_done(self,ok,fail):
        self.c_ok.set_value(ok); self.c_fail.set_value(fail)
        self.btn_start.setEnabled(True); self.btn_start.setText("🚀  开始一键批量合成")
        self.prog.setVisible(False)
        self.statusBar().showMessage(f"完成  ·  成功 {ok}  失败 {fail}")
        self._log(f"\n🏁  处理结束 — 成功 {ok} 张，失败 {fail} 张")
        msg = f"合成完毕！\n\n输出目录：\n{self.row_out.path()}"
        (QMessageBox.information if fail==0 else QMessageBox.warning)(
            self,"任务完成", msg if fail==0 else f"成功 {ok} 张，失败 {fail} 张\n\n{self.row_out.path()}")

    def _start(self):
        inp = self.row_in.path(); out = self.row_out.path()
        if not inp or not os.path.isdir(inp):
            QMessageBox.warning(self,"提示","请选择输入原图所在的文件夹！"); return
        if not out:
            QMessageBox.warning(self,"提示","请选择用来保存结果的输出文件夹！"); return
        if not self.templates:
            QMessageBox.warning(self,"提示","请至少添加一个相框模板图片！"); return
        if self._tpl_fw <= 0:
            QMessageBox.warning(self,"提示","请必须导入相框的 JSON 坐标系，这是内嵌的基础！"); return

        files=[f for f in Path(inp).iterdir()
               if f.suffix.lower() in SUPPORTED_EXT and not f.name.startswith("主图_")]
        if not files:
            QMessageBox.warning(self,"提示","原图文件夹中没有找到任何有效图片！"); return

        selected_items = self.tpl_list.selectedItems()
        if selected_items:
            active_templates = [self.templates[self.tpl_list.row(i)] for i in selected_items]
        else:
            active_templates = self.templates

        n = len(files)
        self.c_total.set_value(n); self.c_ok.set_value("—"); self.c_fail.set_value("—")
        self.prog.setVisible(True)
        self.prog.setValue(0); self.prog.setMaximum(n)
        self.btn_start.setEnabled(False); self.btn_start.setText("正在执行强制切割合成...")

        self._log(f"🚀  启动流水线：{n} 张原图，应用 {len(active_templates)} 个相框")
        self._log(f"    坐标引擎：JSON 绝对尺寸 [起口: ({self._tpl_left},{self._tpl_top}), 洞口: {self._tpl_fw}x{self._tpl_fh}]")

        self._worker = Worker(
            inp, out, active_templates,
            self.spn_w.value(), self.spn_h.value(),
            self.spn_dpi.value(), self.spn_q.value(),
            self._tpl_left, self._tpl_top, self._tpl_fw, self._tpl_fh
        )
        self._worker.sig_log.connect(self._log)
        self._worker.sig_prog.connect(self._on_prog)
        self._worker.sig_done.connect(self._on_done)
        self._worker.start()
        self._save_settings()

def main():
    if sys.platform=="win32":
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ralo.composite.v7")
        except: pass
        try: ctypes.windll.user32.SetProcessDPIAware()
        except: pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(17,17,19))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(216,216,224))
    p.setColor(QPalette.ColorRole.Base,            QColor(14,14,18))
    p.setColor(QPalette.ColorRole.Text,            QColor(192,192,208))
    p.setColor(QPalette.ColorRole.Button,          QColor(28,28,34))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(200,200,216))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(10,132,255))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255,255,255))
    app.setPalette(p)
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()