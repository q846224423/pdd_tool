import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox,
    QLineEdit, QSpinBox, QColorDialog, QComboBox, QSlider, QFormLayout
)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont
from PIL import Image, ImageDraw, ImageFont
import os

class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("商品主图编辑器 - 去水印 & 添加文字")
        self.setGeometry(100, 100, 1200, 800)

        # 原始图片数据 (OpenCV格式 BGR)
        self.original_cv_image = None
        # 当前显示的图片 (用于预览，可能包含文字，但不含水印修复后的结果)
        self.current_cv_image = None
        # 显示用的QPixmap
        self.display_pixmap = None
        # 水印选择矩形
        self.selecting_watermark = False
        self.watermark_rect = None
        self.start_point = None

        # 界面组件
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(300)

        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout()
        self.btn_load = QPushButton("加载图片")
        self.btn_load.clicked.connect(self.load_image)
        self.btn_save = QPushButton("保存图片")
        self.btn_save.clicked.connect(self.save_image)
        file_layout.addWidget(self.btn_load)
        file_layout.addWidget(self.btn_save)
        file_group.setLayout(file_layout)
        control_layout.addWidget(file_group)

        # 去水印组
        watermark_group = QGroupBox("去水印")
        watermark_layout = QVBoxLayout()
        self.btn_select_watermark = QPushButton("框选水印区域")
        self.btn_select_watermark.setCheckable(True)
        self.btn_select_watermark.toggled.connect(self.toggle_watermark_selection)
        self.btn_remove_watermark = QPushButton("执行去水印")
        self.btn_remove_watermark.clicked.connect(self.remove_watermark)
        self.watermark_radius = QSpinBox()
        self.watermark_radius.setRange(1, 20)
        self.watermark_radius.setValue(3)
        self.watermark_radius.setPrefix("修复半径: ")
        watermark_layout.addWidget(self.btn_select_watermark)
        watermark_layout.addWidget(self.watermark_radius)
        watermark_layout.addWidget(self.btn_remove_watermark)
        watermark_group.setLayout(watermark_layout)
        control_layout.addWidget(watermark_group)

        # 添加文字组
        text_group = QGroupBox("添加文字")
        text_layout = QFormLayout()
        self.text_content = QLineEdit("水晶相框")
        self.text_font_size = QSpinBox()
        self.text_font_size.setRange(8, 200)
        self.text_font_size.setValue(48)
        self.text_color_btn = QPushButton("选择颜色")
        self.text_color = QColor(255, 255, 255)  # 默认白色
        self.text_color_btn.setStyleSheet("background-color: white;")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        self.text_x = QSpinBox()
        self.text_x.setRange(0, 2000)
        self.text_y = QSpinBox()
        self.text_y.setRange(0, 2000)
        self.text_x.setValue(100)
        self.text_y.setValue(100)
        # 位置预设
        self.pos_preset = QComboBox()
        self.pos_preset.addItems(["自定义", "左上角", "居中", "右下角"])
        self.pos_preset.currentTextChanged.connect(self.apply_pos_preset)
        self.btn_add_text = QPushButton("添加文字到图片")
        self.btn_add_text.clicked.connect(self.add_text_to_image)

        text_layout.addRow("文字内容:", self.text_content)
        text_layout.addRow("字体大小:", self.text_font_size)
        text_layout.addRow("文字颜色:", self.text_color_btn)
        text_layout.addRow("X 坐标:", self.text_x)
        text_layout.addRow("Y 坐标:", self.text_y)
        text_layout.addRow("位置预设:", self.pos_preset)
        text_layout.addRow("", self.btn_add_text)
        text_group.setLayout(text_layout)
        control_layout.addWidget(text_group)

        control_layout.addStretch()
        main_layout.addWidget(control_panel)

        # 右侧图像显示区域
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #2d2d2d;")
        self.image_label.setMinimumSize(600, 500)
        self.image_label.setScaledContents(False)
        main_layout.addWidget(self.image_label, 1)

        # 鼠标事件用于框选水印
        self.image_label.mousePressEvent = self.image_mouse_press
        self.image_label.mouseMoveEvent = self.image_mouse_move
        self.image_label.mouseReleaseEvent = self.image_mouse_release

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not file_path:
            return
        # 读取图片为OpenCV BGR格式
        self.original_cv_image = cv2.imread(file_path)
        if self.original_cv_image is None:
            QMessageBox.warning(self, "错误", "无法加载图片")
            return
        self.current_cv_image = self.original_cv_image.copy()
        self.update_display()
        QMessageBox.information(self, "成功", "图片加载成功")

    def update_display(self):
        """将当前cv图像转换为QPixmap并显示在label上，同时保持缩放比例"""
        if self.current_cv_image is None:
            return
        rgb_image = cv2.cvtColor(self.current_cv_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.display_pixmap = QPixmap.fromImage(qt_image)
        # 缩放以适应label，保持宽高比
        scaled_pixmap = self.display_pixmap.scaled(
            self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """窗口缩放时重新缩放显示"""
        if self.display_pixmap:
            scaled = self.display_pixmap.scaled(
                self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
        super().resizeEvent(event)

    # ---------- 去水印功能 ----------
    def toggle_watermark_selection(self, checked):
        if checked:
            self.selecting_watermark = True
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.btn_select_watermark.setText("取消选择")
        else:
            self.selecting_watermark = False
            self.watermark_rect = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.btn_select_watermark.setText("框选水印区域")
            # 清除绘制矩形，刷新显示
            self.update_display()

    def image_mouse_press(self, event):
        if not self.selecting_watermark or self.current_cv_image is None:
            return
        # 获取相对于QLabel的实际坐标（QLabel可能缩放显示，需要映射回原始图像坐标）
        label_pos = event.position().toPoint()
        # 获取当前显示的pixmap在label中的矩形区域（居中显示）
        pixmap_rect = self.get_pixmap_rect()
        if not pixmap_rect.contains(label_pos):
            return
        # 将label上的坐标映射到原始图像坐标
        self.start_point = self.map_to_image_coord(label_pos)

    def image_mouse_move(self, event):
        if not self.selecting_watermark or self.start_point is None or self.current_cv_image is None:
            return
        label_pos = event.position().toPoint()
        pixmap_rect = self.get_pixmap_rect()
        if not pixmap_rect.contains(label_pos):
            return
        current_point = self.map_to_image_coord(label_pos)
        # 更新矩形
        x1 = min(self.start_point.x(), current_point.x())
        y1 = min(self.start_point.y(), current_point.y())
        x2 = max(self.start_point.x(), current_point.x())
        y2 = max(self.start_point.y(), current_point.y())
        self.watermark_rect = QRect(x1, y1, x2 - x1, y2 - y1)
        # 实时绘制矩形（在显示pixmap上画临时矩形）
        self.draw_temp_rectangle()

    def image_mouse_release(self, event):
        if not self.selecting_watermark or self.start_point is None:
            return
        self.start_point = None
        # 保持矩形显示，等待用户点击“执行去水印”
        if self.watermark_rect:
            self.draw_temp_rectangle()

    def draw_temp_rectangle(self):
        """在显示的pixmap上绘制矩形框（临时效果）"""
        if self.display_pixmap is None or self.watermark_rect is None:
            return
        # 复制一份pixmap进行绘制
        temp_pixmap = self.display_pixmap.copy()
        painter = QPainter(temp_pixmap)
        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        # 需要将图像坐标的矩形转换为显示坐标
        display_rect = self.map_image_rect_to_display(self.watermark_rect)
        painter.drawRect(display_rect)
        painter.end()
        # 缩放显示
        scaled = temp_pixmap.scaled(
            self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def get_pixmap_rect(self):
        """获取显示的pixmap在QLabel中的实际矩形区域（居中放置）"""
        if self.display_pixmap is None:
            return QRect()
        label_size = self.image_label.size()
        pix_size = self.display_pixmap.size()
        x = (label_size.width() - pix_size.width()) // 2
        y = (label_size.height() - pix_size.height()) // 2
        return QRect(x, y, pix_size.width(), pix_size.height())

    def map_to_image_coord(self, label_point):
        """将QLabel上的点坐标映射到原始图像坐标"""
        pix_rect = self.get_pixmap_rect()
        if pix_rect.width() == 0 or pix_rect.height() == 0:
            return QPoint(0, 0)
        # 计算比例
        img_w = self.current_cv_image.shape[1]
        img_h = self.current_cv_image.shape[0]
        # label上的相对坐标（相对于pixmap的左上角）
        rx = (label_point.x() - pix_rect.x()) / pix_rect.width()
        ry = (label_point.y() - pix_rect.y()) / pix_rect.height()
        img_x = int(rx * img_w)
        img_y = int(ry * img_h)
        img_x = max(0, min(img_x, img_w - 1))
        img_y = max(0, min(img_y, img_h - 1))
        return QPoint(img_x, img_y)

    def map_image_rect_to_display(self, image_rect):
        """将原始图像中的矩形映射到显示用的QRect"""
        if self.display_pixmap is None:
            return QRect()
        pix_rect = self.get_pixmap_rect()
        img_w = self.current_cv_image.shape[1]
        img_h = self.current_cv_image.shape[0]
        # 计算显示缩放比例
        scale_x = pix_rect.width() / img_w
        scale_y = pix_rect.height() / img_h
        x = int(image_rect.x() * scale_x) + pix_rect.x()
        y = int(image_rect.y() * scale_y) + pix_rect.y()
        w = int(image_rect.width() * scale_x)
        h = int(image_rect.height() * scale_y)
        return QRect(x, y, w, h)

    def remove_watermark(self):
        if self.current_cv_image is None:
            QMessageBox.warning(self, "警告", "请先加载图片")
            return
        if self.watermark_rect is None or self.watermark_rect.width() == 0 or self.watermark_rect.height() == 0:
            QMessageBox.warning(self, "警告", "请先用鼠标框选水印区域（点击'框选水印区域'按钮后拖拽）")
            return

        # 创建mask，将选中区域设为白色（需要修复的区域）
        mask = np.zeros(self.current_cv_image.shape[:2], dtype=np.uint8)
        x1 = self.watermark_rect.x()
        y1 = self.watermark_rect.y()
        x2 = x1 + self.watermark_rect.width()
        y2 = y1 + self.watermark_rect.height()
        mask[y1:y2, x1:x2] = 255

        radius = self.watermark_radius.value()
        # 使用OpenCV的图像修复算法
        result = cv2.inpaint(self.current_cv_image, mask, radius, cv2.INPAINT_TELEA)
        self.current_cv_image = result
        self.update_display()
        # 清除矩形选择
        self.watermark_rect = None
        if self.btn_select_watermark.isChecked():
            self.btn_select_watermark.setChecked(False)
        QMessageBox.information(self, "完成", "水印已去除")

    # ---------- 添加文字功能 ----------
    def choose_text_color(self):
        color = QColorDialog.getColor(self.text_color, self, "选择文字颜色")
        if color.isValid():
            self.text_color = color
            self.text_color_btn.setStyleSheet(f"background-color: {color.name()};")

    def apply_pos_preset(self, preset):
        if self.current_cv_image is None:
            return
        h, w = self.current_cv_image.shape[:2]
        font_size = self.text_font_size.value()
        # 简单估算文字尺寸（近似）
        text = self.text_content.text()
        approx_width = len(text) * font_size * 0.6
        approx_height = font_size * 1.2
        if preset == "左上角":
            self.text_x.setValue(20)
            self.text_y.setValue(int(approx_height) + 10)
        elif preset == "居中":
            self.text_x.setValue(int((w - approx_width) / 2))
            self.text_y.setValue(int((h + approx_height) / 2))
        elif preset == "右下角":
            self.text_x.setValue(int(w - approx_width - 20))
            self.text_y.setValue(int(h - 20))
        else:  # 自定义
            pass

    def add_text_to_image(self):
        if self.current_cv_image is None:
            QMessageBox.warning(self, "警告", "请先加载图片")
            return
        text = self.text_content.text()
        if not text.strip():
            QMessageBox.warning(self, "警告", "文字内容不能为空")
            return

        # 将OpenCV BGR转为PIL RGB
        pil_image = Image.fromarray(cv2.cvtColor(self.current_cv_image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # 字体选择（这里使用默认字体，可自行指定ttf文件路径）
        try:
            # 尝试使用系统常见字体，若失败则使用默认字体
            font = ImageFont.truetype("arial.ttf", self.text_font_size.value())
        except:
            font = ImageFont.load_default()
        # 颜色转换
        color = (self.text_color.red(), self.text_color.green(), self.text_color.blue())

        x = self.text_x.value()
        y = self.text_y.value()
        draw.text((x, y), text, font=font, fill=color)

        # 转回OpenCV BGR
        self.current_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        self.update_display()
        QMessageBox.information(self, "成功", f"已添加文字: {text}")

    def save_image(self):
        if self.current_cv_image is None:
            QMessageBox.warning(self, "警告", "没有图片可保存")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "保存图片", "", "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)")
        if file_path:
            cv2.imwrite(file_path, self.current_cv_image)
            QMessageBox.information(self, "成功", f"图片已保存至 {file_path}")

def main():
    app = QApplication(sys.argv)
    window = ImageEditor()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
