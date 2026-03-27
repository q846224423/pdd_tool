import matplotlib
matplotlib.use('TkAgg')  # 强制弹出独立的交互窗口，防止 IDEA 拦截

import os
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# ==========================================
# 配置部分
# ==========================================
# 你的原始场景图片路径 (前面的 r 保证路径斜杠不报错)
YOUR_IMAGE_PATH = r"C:\Users\84622\Desktop\银色竖向模板.jpg"

# 生成的透明模板保存路径
OUTPUT_PNG_NAME = r"C:\Users\84622\Desktop\银色竖向模板输出.png"
# ==========================================

class CoordinateGetter:
    def __init__(self, img_path):
        self.img_path = img_path
        self.points = []

    def get_coords(self):
        if not os.path.exists(self.img_path):
            print(f"❌ 找不到图片: {self.img_path}")
            print("请确认图片名字后缀是否正确（比如是不是 .jpeg 或 .png），以及是否真在桌面上。")
            return None

        print("\n准备开始取坐标。请在弹出的窗口中操作：")
        print("按照【左上角】 -> 【右上角】 -> 【右下角】 -> 【左下角】")
        print("的顺序，依次点击画框的四个【内角】。")
        print("点击完成后，直接关闭图片窗口即可。\n")

        # 读取并显示图片
        img = mpimg.imread(self.img_path)
        fig, ax = plt.subplots()
        ax.imshow(img)
        plt.title("依次点击: 左上, 右上, 右下, 左下。完成后关闭窗口。")

        # 核心：获取 4 个点击坐标，不限制超时
        self.points = plt.ginput(4, timeout=0)
        plt.close()

        if len(self.points) < 4:
            print("❌ 取点失败：必须点击满 4 个点。")
            return None

        return [(int(x), int(y)) for x, y in self.points]

def create_transparent_png(input_path, output_path, points):
    print(f"正在处理图片: {input_path} ...")

    with Image.open(input_path).convert("RGBA") as base_img:
        # 创建一个和原图一样大的透明遮罩层 (L 模式，初始全白=不透明)
        mask = Image.new('L', base_img.size, 255)
        draw = ImageDraw.Draw(mask)

        # 在遮罩层上，把你圈出的多边形区域填成黑色 (完全透明)
        draw.polygon(points, fill=0)

        # 将遮罩层应用到原图的 Alpha 通道
        base_img.putalpha(mask)

        # 保存为 PNG
        base_img.save(output_path, "PNG")

        # 计算 PS 里需要的左上角和右下角坐标（用于代码合成）
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)

        print("\n" + "="*50)
        print(f"✅ 自定义透明模板已生成：{output_path}")
        print("="*50)
        print("请将以下配置复制到你的全自动主程序 TEMPLATES_CONFIG 中：")
        print(f"""
    "my_custom_style": {{
        "path": r"{output_path}",
        "paste_area": ({left}, {top}, {right}, {bottom})
    }}
        """)
        print("="*50 + "\n")

if __name__ == "__main__":
    getter = CoordinateGetter(YOUR_IMAGE_PATH)
    coords = getter.get_coords()

    if coords:
        create_transparent_png(YOUR_IMAGE_PATH, OUTPUT_PNG_NAME, coords)
