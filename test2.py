#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import math
from PIL import Image, ImageDraw, ImageFont

# ================= 配置区域 =================
# 字体路径：必须是支持中文的字体文件！
# Windows 默认可用: "C:/Windows/Fonts/msyh.ttc" (微软雅黑) 或 "simhei.ttf" (黑体)
# Mac 默认可用: "/System/Library/Fonts/PingFang.ttc" (苹方)
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"  # 请根据你的系统修改这里！

# 公章配置
SEAL_TEXT_TOP = "宝岛旅游股份有限公司"  # 你的自定义文字
SEAL_TEXT_BOTTOM = "版权所有"           # 底部辅助文字
SEAL_SIZE = 400                         # 公章生成的分辨率大小
SEAL_COLOR = (220, 20, 60, 255)         # 公章基础颜色 (RGB)，默认暗红色
# ============================================

def draw_curved_text(base_img, text, font, radius, color, start_angle, end_angle):
    """辅助函数：沿着圆弧绘制文字"""
    cx, cy = base_img.size[0] / 2, base_img.size[1] / 2
    chars = list(text)
    if not chars:
        return

    # 计算每个字的间隔角度
    angle_step = (end_angle - start_angle) / (len(chars) - 1) if len(chars) > 1 else 0

    for i, char in enumerate(chars):
        # 1. 创建单个字符的透明画布
        char_img = Image.new('RGBA', (font.size * 2, font.size * 2), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_img)
        char_draw.text((font.size, font.size), char, font=font, fill=color, anchor="mm")

        # 2. 计算当前字符所在的绝对角度 (极坐标)
        angle = start_angle + i * angle_step

        # 3. 旋转单字图片使其指向圆心 (Pillow旋转是逆时针)
        rot_angle = -math.degrees(angle) - 90
        rotated_char = char_img.rotate(rot_angle, resample=Image.Resampling.BICUBIC, expand=True)

        # 4. 计算贴图的直角坐标
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)

        # 5. 居中贴回原图
        px = int(x - rotated_char.size[0] / 2)
        py = int(y - rotated_char.size[1] / 2)
        base_img.paste(rotated_char, (px, py), rotated_char)

def create_transparent_seal():
    """生成带有环形文字的透明公章图片"""
    # 1. 创建透明正方形画布
    img = Image.new("RGBA", (SEAL_SIZE, SEAL_SIZE), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # 2. 画外圈粗线
    line_width = int(SEAL_SIZE * 0.03)
    pad = line_width
    draw.ellipse((pad, pad, SEAL_SIZE - pad, SEAL_SIZE - pad), outline=SEAL_COLOR, width=line_width)

    # 3. 画内圈细线
    pad2 = line_width * 3
    draw.ellipse((pad2, pad2, SEAL_SIZE - pad2, SEAL_SIZE - pad2), outline=SEAL_COLOR, width=int(line_width*0.3))

    try:
        font_top = ImageFont.truetype(FONT_PATH, int(SEAL_SIZE * 0.12))
        font_bottom = ImageFont.truetype(FONT_PATH, int(SEAL_SIZE * 0.08))
    except IOError:
        print(f"❌ 错误: 找不到字体文件 {FONT_PATH}。请检查路径是否正确！")
        return None

    # 4. 画中心五角星
    cx, cy = SEAL_SIZE / 2, SEAL_SIZE / 2
    r_star = SEAL_SIZE * 0.15
    points = []
    for i in range(5):
        # 五角星的角度计算
        angle = i * 4 * math.pi / 5 - math.pi / 2
        points.append((cx + r_star * math.cos(angle), cy + r_star * math.sin(angle)))
    draw.polygon(points, fill=SEAL_COLOR)

    # 5. 绘制环形文字 (顶部)
    # 起始和结束角度 (这里使用弧度，pi 相当于 180度)
    # -math.pi 是左边，0 是右边。我们让文字从左上到右上排布
    start_angle = -math.pi * 0.85
    end_angle = -math.pi * 0.15
    text_radius = SEAL_SIZE * 0.36
    draw_curved_text(img, SEAL_TEXT_TOP, font_top, text_radius, SEAL_COLOR, start_angle, end_angle)

    # 6. 绘制底部文字 (水平)
    draw.text((cx, cy + SEAL_SIZE * 0.25), SEAL_TEXT_BOTTOM, font=font_bottom, fill=SEAL_COLOR, anchor="mm")

    return img

def apply_seal_watermark(bg_image_path, output_path, opacity_percent=35, scale_percent=25):
    """将公章作为半透明水印打在图片上"""
    if not os.path.exists(bg_image_path):
        print(f"❌ 找不到原图: {bg_image_path}")
        return

    # 1. 生成公章
    seal = create_transparent_seal()
    if seal is None: return

    # 2. 打开原图
    bg = Image.open(bg_image_path).convert("RGBA")
    bg_w, bg_h = bg.size

    # 3. 调整公章大小 (根据原图的短边按比例缩放)
    target_seal_size = int(min(bg_w, bg_h) * (scale_percent / 100.0))
    seal = seal.resize((target_seal_size, target_seal_size), Image.Resampling.LANCZOS)

    # 4. 调整公章透明度 (防盗关键)
    # 分离出 alpha 通道，按照百分比降低透明度
    r, g, b, a = seal.split()
    a = a.point(lambda p: int(p * (opacity_percent / 100.0)))
    seal = Image.merge("RGBA", (r, g, b, a))

    # 5. 计算贴图位置 (默认放在右下角，留点边距)
    padding = int(min(bg_w, bg_h) * 0.05)
    x = bg_w - target_seal_size - padding
    y = bg_h - target_seal_size - padding

    # 6. 将公章贴合上去
    result = Image.alpha_composite(bg, Image.new("RGBA", bg.size, (0,0,0,0)))
    result.paste(seal, (x, y), seal)

    # 7. 保存结果 (去除 RGBA 的 A 通道保存为 JPG，或者直接存 PNG)
    result = result.convert("RGB")
    result.save(output_path, quality=95)
    print(f"✅ 水印添加成功！已保存至: {output_path}")

if __name__ == "__main__":
    # --- 测试运行 ---

    # 1. 如果你想先看看公章长什么样，可以单独保存公章：
    my_seal = create_transparent_seal()
    if my_seal:
        my_seal.save("my_seal_preview.png")
        print("✅ 公章预览已保存为 my_seal_preview.png")

    # 2. 把公章打在你的图片上 (请将 input.jpg 替换为你实际的图片路径)
    # 参数说明：
    # opacity_percent: 35 表示 35% 的不透明度，非常适合防盗
    # scale_percent: 25 表示公章大小占据图片短边的 25%
    source_image = "input.jpg"
    output_image = "output_watermarked.jpg"

    # 如果当前目录下存在 input.jpg，就执行打水印逻辑
    if os.path.exists(source_image):
        apply_seal_watermark(source_image, output_image, opacity_percent=35, scale_percent=25)
    else:
        print(f"\n⚠️ 提示: 请准备一张名为 '{source_image}' 的图片放在同一目录下，以测试盖章效果。")