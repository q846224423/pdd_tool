import matplotlib
matplotlib.use('TkAgg')

import os
import math
from PIL import Image, ImageDraw, ImageFilter
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# ==========================================
# 优化版配置部分 (请确认图片路径和文件名)
# ==========================================
YOUR_IMAGE_PATH = r"C:\Users\84622\Desktop\银色竖向模板.jpg"
OUTPUT_PNG_NAME = r"C:\Users\84622\Desktop\银色竖向模板输出.png"
# ==========================================

class CoordinateGetter:
    def __init__(self, img_path):
        self.img_path = img_path
        self.points = []

    def get_coords(self):
        if not os.path.exists(self.img_path):
            print(f"❌ 找不到图片: {self.img_path}")
            return None

        print("\n准备开始取坐标。请在弹出的窗口中操作：")
        print("点击画框内角四个角（顺序任意，不用强制）。")
        print("完成后关闭窗口即可。程序会自动识别正确区域。\n")

        img = mpimg.imread(self.img_path)
        fig, ax = plt.subplots()
        ax.imshow(img)
        plt.title("随意点击四个内角，完成后关闭窗口")

        self.points = plt.ginput(4, timeout=0)
        plt.close()

        if len(self.points) < 4:
            print("❌ 取点失败：必须点击满 4 个点。")
            return None

        return [(int(x), int(y)) for x, y in self.points]

def sort_points_clockwise(points):
    """
    【核心优化】自动将任意顺序点击的四个点重新排列为顺时针顺序，防止出现自交（漏斗形）。
    算法依据：计算所有点的几何中心，按点相对于中心的角度排序。
    """
    # 计算几何中心点
    centroid_x = sum(x for x, y in points) / len(points)
    centroid_y = sum(y for x, y in points) / len(points)

    def get_angle(point):
        return math.atan2(point[1] - centroid_y, point[0] - centroid_x)

    # 按相对于中心点的角度从最小（接近水平右侧）到最大（逆时针）进行排序
    sorted_points = sorted(points, key=get_angle)
    return sorted_points

def create_transparent_png_v2(input_path, output_path, points):
    print(f"正在进行最终优化处理: {input_path} ...")

    # 核心修复点：对用户点击的点进行顺时针重新排序，防止漏斗形
    sorted_points = sort_points_clockwise(points)

    with Image.open(input_path).convert("RGBA") as base_img:
        width, height = base_img.size

        # 优化1：更高的超采样倍率，消除锯齿
        scale = 8
        oversize = (width * scale, height * scale)
        scaled_points = [(p[0] * scale, p[1] * scale) for p in sorted_points]

        mask = Image.new('L', oversize, 255)
        draw = ImageDraw.Draw(mask)

        # 优化2：在大图上填充黑色，边缘平滑
        draw.polygon(scaled_points, fill=0)

        # 优化3：更平滑的缩放滤镜，产生视觉羽化
        mask = mask.resize((width, height), resample=Image.LANCZOS)

        # 优化4：可选的轻微边缘羽化，让抠图更柔和
        # mask = mask.filter(ImageFilter.GaussianBlur(radius=0.5))

        base_img.putalpha(mask)
        base_img.save(output_path, "PNG")

        # 优化5：坐标推荐调整，返回推荐的对角坐标
        left_p, right_p = sorted(sorted_points, key=lambda p: p[0])[:2], sorted(sorted_points, key=lambda p: p[0])[2:]
        left = int(min(p[0] for p in left_p))
        right = int(max(p[0] for p in right_p))

        top_p, bottom_p = sorted(sorted_points, key=lambda p: p[1])[:2], sorted(sorted_points, key=lambda p: p[1])[2:]
        top = int(min(p[1] for p in top_p))
        bottom = int(max(p[1] for p in bottom_p))

        print("\n" + "="*50)
        print(f"✅ 最终优化透明模板已生成：{output_path}")
        print("="*50)
        print("请将以下配置复制到全自动主程序 TEMPLATES_CONFIG 中：")
        print(f"""
    "my_final_style": {{
        "path": r"{output_path}",
        "paste_area": ({left}, {top}, {right}, {bottom})
    }}
        """)
        print("="*50 + "\n")

if __name__ == "__main__":
    getter = CoordinateGetter(YOUR_IMAGE_PATH)
    coords = getter.get_coords()

    if coords:
        create_transparent_png_v2(YOUR_IMAGE_PATH, OUTPUT_PNG_NAME, coords)