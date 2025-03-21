import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QSlider, QHBoxLayout, QLabel
)
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QPixmap, QBrush
from PyQt5.QtCore import Qt, QPoint

import clr
import os
import math

class BezierCurveEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bezier Curve Editor for osu!")
        self.setGeometry(100, 100, 800, 600)
        self.control_points = []  # 存储控制点
        self.history = []  # 操作历史
        self.future = []  # 撤销后的操作
        self.dragging_point = None  # 当前拖动的控制点索引
        self.image = None  # 导入的图片
        self.image_scale = 1.0  # 图片缩放比例
        self.image_opacity = 1.0  # 图片透明度
        self.curve_segments = 100  # 曲线绘制段数
        self.dragging_curve_only = False  # 是否正在单独拖动曲线 (新增)
        self.dragging_curve_and_image = False  # 是否正在拖动曲线和图片 (新增)
        self.last_mouse_pos = QPoint()  # 上次鼠标位置
        self.curve_scale = 1.0  # 曲线整体缩放比例
        self.outline_width = 4  # 描边粗细 (初始值，之后会被计算的值覆盖)
        self.outline_opacity = 0.5  # 描边透明度
        self.rect_scale = 0.95  # 矩形默认大小为窗口的 95%
        self.rect_width = 0    # 矩形宽度（动态计算）
        self.rect_height = 0   # 矩形高度（动态计算）
        self.image_offset_x = 0  # 图片水平偏移量
        self.image_offset_y = 0  # 图片垂直偏移量
        self.highlighted_segment_index = None
        self.is_dragging_control_point = False
        self.init_ui()

        # 在 init_ui() 之后，根据初始 Circle size 值计算 outline_width
        initial_circle_size_value = self.circle_size_slider.value() # 获取 Circle size 滑块的初始值
        estimated_rect_height_large = int(self.width() * self.rect_scale * 3 / 4) # 估计初始矩形高度
        initial_outline_width_calculated = (estimated_rect_height_large / 480) * (54.4 - 4.48 * initial_circle_size_value) * 1.65
        self.outline_width = max(0, initial_outline_width_calculated) # 确保非负值

        self.update_circle_size() #  **重要:** 初始调用 update_circle_size，确保初始描边宽度正确设置并应用到界面上

    def bernstein_basis_polynomial(self, n, i, t):
        if not 0 <= t <= 1:
            return 0
        binomial_coefficient = math.factorial(n) / (math.factorial(i) * math.factorial(n - i))
        power_of_t = t ** i
        power_of_one_minus_t = (1 - t) ** (n - i)
        basis = binomial_coefficient * power_of_t * power_of_one_minus_t
        return basis

    def init_ui(self):
        # 设置窗口背景颜色
        self.setStyleSheet("background-color: #0C0C0C; color: #FFFFFF;")

        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 操作提示标签
        self.help_label = QLabel(
            """
            <b>操作提示：</b><br>
            左键 新增锚点<br>
            右键 修改锚点<br>
            中键 拖动曲线<br>
            滚轮 缩放/平移<br>
            ALT+左键 增加中间锚点<br>
            ALT+右键 删除锚点<br>
            ALT+右键（按住） 高亮附近线<br>
            CTRL+中键 拖动曲线和图片
            """,
            self
        )
        self.help_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);  /* 半透明黑色背景 */
                color: white;                            /* 文字颜色 */
                padding: 10px;                             /* 内边距 */
                border-radius: 5px;                          /* 圆角 */
                font-size: 12px;                             /* 字体大小 */
            }
        """)
        self.help_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 文字左对齐
        self.help_label.setFixedSize(200, 150)  # 固定大小 (高度增加以容纳新提示)
        self.help_label.move(self.width() - 220, self.height() - 360)  # 右下角位置

        # 隐藏帮助按钮
        self.hide_help_button = QPushButton("隐藏帮助", self)
        self.hide_help_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(72, 93, 219, 150);  /* 半透明黑色背景 */
                color: white;                            /* 文字颜色 */
                padding: 5px;                              /* 内边距 */
                border-radius: 5px;                          /* 圆角 */
                font-size: 12px;                             /* 字体大小 */
            }
            QPushButton:hover {
                background-color: rgba(91, 70, 192, 200);  /* 鼠标悬停时背景变深 */
            }
        """)
        self.hide_help_button.setFixedSize(80, 30)  # 固定大小
        self.hide_help_button.move(self.width() - 90, self.height() - 80)  # 右下角，稍微上移 (根据帮助标签高度调整位置)
        self.hide_help_button.clicked.connect(self.toggle_help_visibility)

        # 默认显示帮助
        self.help_visible = True

        # 顶部布局（按钮和滑块）
        top_layout = QHBoxLayout()

        # 按钮样式
        button_style = """
            QPushButton {
                background-color: #495CDA;  /* 背景颜色 */
                color: white;                /* 文字颜色 */
                border-radius: 10px;         /* 圆角 */
                padding: 10px;               /* 内边距 */
                font-size: 14px;             /* 字体大小 */
                font-weight: bold;           /* 字体加粗 */
            }
            QPushButton:hover {
                background-color: #5C44BE;  /* 鼠标悬停时的背景颜色 */
            }
        """

        # 导出按钮
        export_button = QPushButton("Export Control Points", self)
        export_button.setStyleSheet(button_style)
        export_button.clicked.connect(self.export_points)
        top_layout.addWidget(export_button)

        # 导入图片按钮
        import_button = QPushButton("Import Image", self)
        import_button.setStyleSheet(button_style)
        import_button.clicked.connect(self.import_image)
        top_layout.addWidget(import_button)

        # 图片缩放滑块
        scale_label = QLabel("Image Scale:", self)
        scale_label.setStyleSheet("color: #FFFFFF;")
        top_layout.addWidget(scale_label)
        self.scale_slider = QSlider(Qt.Horizontal, self)
        self.scale_slider.setMinimum(10)
        self.scale_slider.setMaximum(200)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.update_image_scale)
        top_layout.addWidget(self.scale_slider)

        # 图片透明度滑块
        opacity_label = QLabel("Image Opacity:", self)
        opacity_label.setStyleSheet("color: #FFFFFF;")
        top_layout.addWidget(opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_image_opacity)
        top_layout.addWidget(self.opacity_slider)

        # 曲线绘制段数滑块
        segments_label = QLabel("Curve Segments:", self)
        segments_label.setStyleSheet("color: #FFFFFF;")
        top_layout.addWidget(segments_label)
        self.segments_slider = QSlider(Qt.Horizontal, self)
        self.segments_slider.setMinimum(10)
        self.segments_slider.setMaximum(500)
        self.segments_slider.setValue(100)
        self.segments_slider.valueChanged.connect(self.update_curve_segments)
        top_layout.addWidget(self.segments_slider)

        # 将顶部布局添加到主布局
        main_layout.addLayout(top_layout)

        # 底部布局（描边滑块）
        bottom_layout = QHBoxLayout()

        # Circle size 滑块
        circle_size_label = QLabel("Circle size:", self)
        circle_size_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(circle_size_label)
        self.circle_size_slider = QSlider(Qt.Horizontal, self)
        self.circle_size_slider.setMinimum(0)
        self.circle_size_slider.setMaximum(10)
        self.circle_size_slider.setValue(5)
        self.circle_size_slider.valueChanged.connect(self.update_circle_size)

        # **新增: 显示 Circle size 滑块值的 QLabel**
        self.circle_size_value_label = QLabel(str(self.circle_size_slider.value()), self) # 初始显示滑块的默认值
        self.circle_size_value_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(self.circle_size_value_label)

        # 将滑块的 valueChanged 信号连接到更新 QLabel 的函数
        self.circle_size_slider.valueChanged.connect(self.update_circle_size_label) # 新增信号连接

        bottom_layout.addWidget(self.circle_size_slider) # 确保滑块仍然被添加到布局 (如果上面移动了添加代码，确保这一行在正确的位置)

        # 描边透明度滑块
        outline_opacity_label = QLabel("Outline Opacity:", self)
        outline_opacity_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(outline_opacity_label)
        self.outline_opacity_slider = QSlider(Qt.Horizontal, self)
        self.outline_opacity_slider.setMinimum(0)
        self.outline_opacity_slider.setMaximum(90)
        self.outline_opacity_slider.setValue(50)
        self.outline_opacity_slider.valueChanged.connect(self.update_outline_opacity)
        bottom_layout.addWidget(self.outline_opacity_slider)

        # 矩形大小滑块
        rect_scale_label = QLabel("Playfield Boundary:", self)
        rect_scale_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(rect_scale_label)
        self.rect_scale_slider = QSlider(Qt.Horizontal, self)
        self.rect_scale_slider.setMinimum(10)  # 最小缩放比例为 10%
        self.rect_scale_slider.setMaximum(100)  # 最大缩放比例为 100%
        self.rect_scale_slider.setValue(int(self.rect_scale * 100))  # 默认值为 90%
        self.rect_scale_slider.valueChanged.connect(self.update_rect_scale)
        self.rect_scale_slider.valueChanged.connect(self.update_circle_size)
        bottom_layout.addWidget(self.rect_scale_slider)

        # 导入滑条按钮
        import_slider_button = QPushButton("Import Slider", self)
        import_slider_button.setStyleSheet(button_style)
        import_slider_button.clicked.connect(self.import_slider)
        bottom_layout.addWidget(import_slider_button)

        # 将底部布局添加到主布局
        main_layout.addLayout(bottom_layout)

        # 设置顶部布局的对齐方式
        main_layout.setAlignment(top_layout, Qt.AlignTop)

    def toggle_help_visibility(self):
        """切换帮助的可见性"""
        self.help_visible = not self.help_visible
        self.help_label.setVisible(self.help_visible)
        self.hide_help_button.setText("隐藏帮助" if self.help_visible else "显示帮助")

    def resizeEvent(self, event):
        """窗口大小变化时更新帮助位置"""
        super().resizeEvent(event)
        if hasattr(self, 'help_label') and hasattr(self, 'hide_help_button'):
            self.help_label.move(self.width() - 220, self.height() - 360) 
            self.hide_help_button.move(self.width() - 90, self.height() - 350) 

    def keyPressEvent(self, event):
        # 撤销操作 (Ctrl+Z)
        if event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo()
        # 恢复操作 (Ctrl+Y)
        elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
            self.redo()

    def undo(self):
        if self.history:
            # 将当前状态保存到 future
            self.future.append((self.control_points.copy(), self.image, self.image_scale, self.image_opacity, self.curve_scale, self.outline_width, self.outline_opacity, self.image_offset_x, self.image_offset_y)) # 保存 image_offset_x 和 image_offset_y
            # 恢复到上一个状态
            last_state = self.history.pop()
            self.control_points = last_state[0]
            self.image = last_state[1]
            self.image_scale = last_state[2]
            self.image_opacity = last_state[3]
            self.curve_scale = last_state[4]
            self.outline_width = last_state[5]
            self.outline_opacity = last_state[6]
            self.image_offset_x = last_state[7] # 恢复 image_offset_x
            self.image_offset_y = last_state[8] # 恢复 image_offset_y
            self.update()

    def redo(self):
        if self.future:
            # 将当前状态保存到 history
            self.history.append((self.control_points.copy(), self.image, self.image_scale, self.image_opacity, self.curve_scale, self.outline_width, self.outline_opacity, self.image_offset_x, self.image_offset_y)) # 保存 image_offset_x 和 image_offset_y
            # 恢复到下一个状态
            next_state = self.future.pop()
            self.control_points = next_state[0]
            self.image = next_state[1]
            self.image_scale = next_state[2]
            self.image_opacity = next_state[3]
            self.curve_scale = next_state[4]
            self.outline_width = next_state[5]
            self.outline_opacity = next_state[6]
            self.image_offset_x = next_state[7] # 恢复 image_offset_x
            self.image_offset_y = next_state[8] # 恢复 image_offset_y
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if event.modifiers() == Qt.ControlModifier:
                # Ctrl + 鼠标中键：开始拖动曲线和图片 (新增)
                self.dragging_curve_and_image = True
                self.dragging_curve_only = False # 确保单独拖动曲线标志为False
            else:
                # 鼠标中键：开始单独拖动曲线 (新增)
                self.dragging_curve_only = True
                self.dragging_curve_and_image = False # 确保同时拖动曲线和图片标志为False
            self.last_mouse_pos = event.pos()
        elif event.button() == Qt.LeftButton:
            if event.modifiers() == Qt.AltModifier:
                # Alt + 左键：在最近的两个连续控制点中间插入新控制点
                self.insert_control_point(event.pos())
            else:
                # 普通左键：添加控制点
                self.save_state()
                self.control_points.append(event.pos())
                self.update()
        elif event.button() == Qt.RightButton:
            if event.modifiers() == Qt.AltModifier:
                # Alt + 右键：删除点击的控制点
                self.delete_control_point(event.pos())
            else:
                # 普通右键：检查是否点击了控制点
                for i, point in enumerate(self.control_points):
                    if self.distance(point, event.pos()) < 10:
                        self.dragging_point = i
                        self.save_state()
                        self.is_dragging_control_point = True  #  <---  请确认这行代码是否已添加！
                        self.drag_start_point = event.pos()
                        self.update()
                        return

    def mouseMoveEvent(self, event):
        if self.dragging_curve_and_image:
            # Ctrl + 鼠标中键拖动：整体平移曲线和图片 (修改)
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.save_state()

            # 平移曲线
            for i in range(len(self.control_points)):
                self.control_points[i] += delta

            # 平移图片
            self.image_offset_x += delta.x()
            self.image_offset_y += delta.y()

            self.update()
            return
        elif self.dragging_curve_only:
            # 鼠标中键拖动：单独平移曲线 (新增)
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.save_state()

            # 平移曲线
            for i in range(len(self.control_points)):
                self.control_points[i] += delta

            self.update() # 只更新曲线，图片不移动
            return
        elif self.dragging_point is not None:
            # 拖动控制点
            self.save_state()
            self.control_points[self.dragging_point] = event.pos()
            self.update()
            return

        if event.modifiers() & Qt.AltModifier: # 检查 Alt 键是否被按下
            min_distance = float('inf')
            closest_line_index = None

            for i in range(len(self.control_points) - 1):
                start_point = self.control_points[i]
                end_point = self.control_points[i + 1]
                distance = self.point_to_line_distance(event.pos(), start_point, end_point)
                if distance < min_distance:
                    min_distance = distance
                    closest_line_index = i

            if closest_line_index is not None and min_distance < 20: # 如果找到最近线段且距离小于阈值
                self.highlighted_segment_index = closest_line_index # 保存高亮线段索引
            else:
                self.highlighted_segment_index = None # 否则，取消高亮显示
            self.update() # 触发重绘，更新高亮显示
        else: # 如果 Alt 键没有被按下
            self.highlighted_segment_index = None # 取消高亮显示
            # 如果没有 Alt 键按下，也需要 update， 清除之前的高亮显示
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # 停止拖动曲线和图片/或单独拖动曲线 (修改)
            self.dragging_curve_only = False
            self.dragging_curve_and_image = False
        elif event.button() == Qt.RightButton:
            self.dragging_point = None
            self.is_dragging_control_point = False
            self.update()

    def wheelEvent(self, event):
        # 滚轮：整体缩放曲线
        self.save_state()
        delta = event.angleDelta().y() / 120  # 获取滚轮滚动方向
        scale_factor = 1.1 if delta > 0 else 0.9
        self.curve_scale *= scale_factor

        # 以窗口中心为基准缩放
        center = QPoint(self.width() // 2, self.height() // 2)
        for i in range(len(self.control_points)):
            self.control_points[i] = center + (self.control_points[i] - center) * scale_factor
        self.update()

    def insert_control_point(self, pos):
        """在最近的两个连续控制点中间插入新控制点"""
        if len(self.control_points) < 2:
            return

        # 找到最近的两个连续控制点
        min_distance = float('inf')
        insert_index = -1
        for i in range(len(self.control_points) - 1):
            p1 = self.control_points[i]
            p2 = self.control_points[i + 1]
            distance = self.point_to_line_distance(pos, p1, p2)
            if distance < min_distance:
                min_distance = distance
                insert_index = i + 1

        if insert_index != -1:
            # 在两个控制点中间插入新控制点
            new_point = QPoint(
                (self.control_points[insert_index - 1].x() + self.control_points[insert_index].x()) // 2,
                (self.control_points[insert_index - 1].y() + self.control_points[insert_index].y()) // 2
            )
            self.save_state()
            self.control_points.insert(insert_index, new_point)
            self.update()

    def delete_control_point(self, pos):
        """删除点击的控制点"""
        for i, point in enumerate(self.control_points):
            if (pos - point).manhattanLength() < 10:
                self.save_state()
                self.control_points.pop(i)
                self.update()
                break

    def point_to_line_distance(self, point, line_start, line_end):
        """计算点到直线的距离"""
        x0, y0 = point.x(), point.y()
        x1, y1 = line_start.x(), line_start.y()
        x2, y2 = line_end.x(), line_end.y()
        numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denominator = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
        return numerator / denominator if denominator != 0 else float('inf')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置窗口背景颜色
        painter.fillRect(self.rect(), QColor("#0C0C0C"))

        # 计算窗口中心
        center_x = self.width() // 2
        center_y = self.height() // 2

        # 绘制图片
        if self.image:
            painter.setOpacity(self.image_opacity)

            # 计算综合缩放比例： image_scale (滑块控制) * rect_scale (Playfield Boundary 控制)
            combined_scale = self.image_scale * self.rect_scale

            # 使用综合缩放比例缩放图片
            scaled_image = self.image.scaled(
                int(self.image.width() * combined_scale),  
                int(self.image.height() * combined_scale), 
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            image_x = center_x - scaled_image.width() // 2 + self.image_offset_x
            image_y = center_y - scaled_image.height() // 2 + self.image_offset_y
            painter.drawPixmap(image_x, image_y, scaled_image)
        painter.setOpacity(1.0) # 重置透明度

        # 计算大矩形的大小
        rect_width_large = int(self.width() * self.rect_scale)
        rect_height_large = int(rect_width_large * 3 / 4)  # 宽高比例为 4:3

        # 计算大矩形的左上角坐标
        rect_x_large = center_x - rect_width_large // 2
        rect_y_large = center_y - rect_height_large // 2

        # **绘制大矩形 (虚线)**
        rect_color = QColor(64, 64, 69)  
        rect_color.setAlpha(128)  # 半透明（50% 透明度）
        pen = QPen(rect_color, 2) # 描边宽度为 2
        pen.setStyle(Qt.DashLine) # 设置为虚线风格  <--- 修改点: 设置线条风格为虚线
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)  # 无填充
        painter.drawRect(rect_x_large, rect_y_large, rect_width_large, rect_height_large)

        # **计算小矩形的大小和坐标**
        rect_width_small = int(rect_width_large * 0.8) # 宽度为大矩形的 80%
        rect_height_small = int(rect_height_large * 0.8) # 高度为大矩形的 80%
        rect_x_small = center_x - rect_width_small // 2 # 小矩形中心与大矩形中心对齐
        rect_y_small = center_y - rect_height_small // 2 # 小矩形中心与大矩形中心对齐

        # **绘制小矩形 (实线)**
        rect_color_small = QColor(64, 64, 69)  # 颜色与大矩形相同
        rect_color_small.setAlpha(128)  # 半透明，透明度与大矩形相同
        pen_small = QPen(rect_color_small, 2) # 描边宽度为 2，与大矩形相同
        pen_small.setStyle(Qt.SolidLine) # 设置为实线风格  <--- 确保小矩形是实线
        painter.setPen(pen_small)
        painter.setBrush(Qt.NoBrush)  # 无填充
        painter.drawRect(rect_x_small, rect_y_small, rect_width_small, rect_height_small)


        # 绘制描边和圆环（位于控制点下方）
        if len(self.control_points) >= 2:
            outline_path = QPainterPath()
            outline_path.moveTo(self.control_points[0])

            # 使用德卡斯特里奥算法计算全局贝塞尔曲线
            for t in range(0, self.curve_segments + 1):
                t /= self.curve_segments
                point = self.calculate_bezier_point(t, self.control_points)
                if t == 0:
                    outline_path.moveTo(point)
                else:
                    outline_path.lineTo(point)

            # 绘制外侧白色描边
            outer_width = self.outline_width + self.outline_width / 8
            outer_color = QColor("#FFFFFF")
            outer_color.setAlphaF(self.outline_opacity)  # 使用描边的透明度
            painter.setPen(QPen(outer_color, outer_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(outline_path)

            # 绘制内侧粉色描边
            inner_color = QColor("#F766A7")
            inner_color.setAlphaF(self.outline_opacity)  # 使用描边的透明度
            painter.setPen(QPen(inner_color, self.outline_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(outline_path)

            # 绘制头尾空心白色圆环
            start_point = self.control_points[0]
            end_point = self.control_points[-1]
            ring_radius = self.outline_width * (17 / 32)

            # 计算圆环的线宽为半径的 1/8
            pen_width = ring_radius / 8

            # 设置画笔颜色并应用透明度
            ring_color = QColor("#FFFFFF")
            ring_color.setAlphaF(self.outline_opacity)  # 使用描边的透明度

            # 设置画笔和画刷
            painter.setPen(QPen(ring_color, pen_width))  # 设置线宽为半径的 1/8
            painter.setBrush(Qt.NoBrush)

            # 绘制起始点圆环
            painter.drawEllipse(start_point, ring_radius, ring_radius)

            # 绘制结束点圆环
            painter.drawEllipse(end_point, ring_radius, ring_radius)

        # 绘制控制点
        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor("#FFFFFF"), 5))
        for point in self.control_points:
            painter.drawPoint(point)

        # 绘制控制线
        painter.setPen(QPen(QColor("#FFFFFF"), 1, Qt.DashLine))
        for i in range(len(self.control_points) - 1):
            painter.drawLine(self.control_points[i], self.control_points[i + 1])

        # 绘制高亮显示的控制线段 (在普通控制线之上绘制)
        if self.highlighted_segment_index is not None: # 检查是否有需要高亮显示的线段
            highlighted_index = self.highlighted_segment_index
            highlight_color = QColor("#f4d68f") #  #26a13c -  高亮线段颜色
            adjacent_color = QColor("#f4d68f")  #  #788d66 -  相邻线段颜色
            highlight_color.setAlphaF(0.8)
            adjacent_color.setAlphaF(0.4)

            # 绘制高亮线段
            painter.setPen(QPen(highlight_color, 8, Qt.SolidLine)) # 粗实线，更醒目
            start_point_highlight = self.control_points[highlighted_index]
            end_point_highlight = self.control_points[highlighted_index + 1]
            painter.drawLine(start_point_highlight, end_point_highlight)

            # 绘制相邻的前一条线段 (如果存在)
            if highlighted_index > 0:
                painter.setPen(QPen(adjacent_color, 5, Qt.DashLine)) # 稍细虚线，区分主高亮
                start_point_adjacent_prev = self.control_points[highlighted_index - 1]
                end_point_adjacent_prev = self.control_points[highlighted_index]
                painter.drawLine(start_point_adjacent_prev, end_point_adjacent_prev)

            # 绘制相邻的后一条线段 (如果存在)
            if highlighted_index < len(self.control_points) - 2: # 注意索引范围
                painter.setPen(QPen(adjacent_color, 5, Qt.DashLine)) # 稍细虚线，区分主高亮
                start_point_adjacent_next = self.control_points[highlighted_index + 1]
                end_point_adjacent_next = self.control_points[highlighted_index + 2]
                painter.drawLine(start_point_adjacent_next, end_point_adjacent_next)


        # 绘制全局贝塞尔曲线（蓝色实线）
        if len(self.control_points) >= 2:
            path = QPainterPath()
            path.moveTo(self.control_points[0])

            # 使用德卡斯特里奥算法计算全局贝塞尔曲线
            for t in range(0, self.curve_segments + 1):
                t /= self.curve_segments
                point = self.calculate_bezier_point(t, self.control_points)
                if t == 0:
                    path.moveTo(point)
                else:
                    path.lineTo(point)

            painter.setPen(QPen(QColor("#0000FF"), 2))
            painter.drawPath(path)

        # 绘制染色曲线（黄色，透明度由影响力权重控制）
        if self.is_dragging_control_point:
            influence_color = QColor("#FFFF00") # 黄色染色
            # painter.setPen(QPen(influence_color, 30)) # Pen 设置移动到循环内

            path = QPainterPath() # 为染色曲线创建新的 path
            path.moveTo(self.control_points[0])
            dragged_point_index = self.dragging_point # 获取被拖动的控制点索引 (索引值)
            curve_order = len(self.control_points) - 1 #  动态计算贝塞尔曲线的阶数 n

            segment_influence_weights = [] #  存储每段线段的影响力权重的列表

            # ---  第一遍循环：计算每段线段的影响力权重 ---
            for t in range(0, self.curve_segments ): # 逐段计算染色曲线
                t_start = t / self.curve_segments # 当前段的起始 t 值
                t_end = (t + 1) / self.curve_segments # 当前段的结束 t 值
                t_mid = (t_start + t_end) / 2 #  使用线段中点对应的 t 值 (近似)

                # --- 计算被拖动控制点的影响力权重 ---
                influence_weight = self.bernstein_basis_polynomial(curve_order, dragged_point_index, t_mid)
                segment_influence_weights.append({'index': t, 'weight': influence_weight}) # 存储字典，包含索引和权重
                # print(f" influence_weight: {influence_weight}")

                # ---  计算所有线段影响力权重的最大值 (添加到这里) ---
                max_influence_weight = 0 #  初始化最大权重值
                for segment_weight in segment_influence_weights: # 遍历所有线段的权重
                    if segment_weight['weight'] > max_influence_weight: # 如果当前线段的权重值大于当前最大值
                        max_influence_weight = segment_weight['weight'] #  更新最大权重值

            # ---  第二遍循环：绘制黄色实心圈，替代染色曲线 ---
            # print("\n--- Second Loop: Drawing Yellow Circles ---") # 标记第二遍循环开始 (绘制黄色圆圈)
            for t in range(0, self.curve_segments ): # 再次循环，逐段绘制染色标记 (黄色圆圈)
                t_start = t / self.curve_segments # 当前段的起始 t 值
                t_end = (t + 1) / self.curve_segments # 当前段的结束 t 值
                t_mid = (t_start + t_end) / 2 #  线段中点对应的 t 值

                # ---  获取排序后的影响力权重 (目前已移除排序，直接使用原始权重) ---
                influence_weight = segment_influence_weights[t]['weight'] #  从字典中获取 'weight' 键的值 (float)
                normalized_influence_weight = influence_weight / max_influence_weight if max_influence_weight > 0 else 0

                # --- 透明度映射 (反转映射，权重越大，Alpha越小，越不透明) ---
                max_alpha = 0.8 # 最大透明度 (最透明，颜色最浅)  对应 100% 透明度
                min_alpha = 0 # 最小透明度 (最不透明，颜色最深)  对应 0% 透明度
                alpha = min_alpha + (max_alpha - min_alpha) * (1 - influence_weight ** 2) # 应用反转平方映射

                influence_color.setAlphaF(alpha) # 动态设置画笔透明度


                # ---  半径映射：影响力权重越大，半径越大，反之半径越小 ---
                max_radius = 10 #  最大半径 (可以调整)
                min_radius = 0 #  最小半径 (可以调整，可以设为 0，如果希望权重为 0 时，圆圈完全消失)
                radius = min_radius + (max_radius - min_radius) * (normalized_influence_weight ** 2) #  线性半径映射


                painter.setBrush(QBrush(influence_color)) # 设置画刷颜色 (黄色和动态透明度)
                painter.setPen(Qt.NoPen) #  设置为无轮廓线

                # --- 计算线段中点 ---
                point_mid = self.calculate_bezier_point(t_mid, self.control_points) # 计算当前段的 *中点*

                # ---  绘制实心圆形标记 ---
                painter.drawEllipse(point_mid, radius, radius) #  在线段中点绘制圆形，半径由 radius 决定

                # ---  添加调试打印：输出圆形绘制信息 (添加到这里) ---
                # print(f"Segment Index (t): {t},  t_mid: {t_mid:.3f},  Weight: {influence_weight:.4f},  Alpha: {alpha:.4f}, Radius: {radius:.2f}")
                # ---  调试打印结束 ---
            # print("--- Second Loop End ---") # 标记第二遍循环结束 (黄色圆圈绘制完成)


        painter.end()

    def calculate_bezier_point(self, t, control_points):
        """根据参数 t 计算贝塞尔曲线上的点"""
        n = len(control_points) - 1
        x, y = 0, 0
        for i, point in enumerate(control_points):
            # 计算贝塞尔基函数
            coefficient = self.binomial_coefficient(n, i) * (1 - t) ** (n - i) * t ** i
            x += point.x() * coefficient
            y += point.y() * coefficient
        return QPoint(int(x), int(y))

    def distance(self, p1, p2):
        """计算两点之间距离的辅助函数 (使用距离公式)"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.sqrt(dx * dx + dy * dy)

    def binomial_coefficient(self, n, k):
        """计算二项式系数 C(n, k)"""
        if k < 0 or k > n:
            return 0
        if k == 0 or k == n:
            return 1
        k = min(k, n - k)  # 利用对称性优化计算
        result = 1
        for i in range(k):
            result = result * (n - i) // (i + 1)
        return result

    def save_state(self):
        """保存当前状态到历史记录"""
        self.history.append((self.control_points.copy(), self.image, self.image_scale, self.image_opacity, self.curve_scale, self.outline_width, self.outline_opacity, self.image_offset_x, self.image_offset_y)) # 保存 image_offset_x 和 image_offset_y
        self.future.clear()

    def import_image(self):
        """导入图片"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_name:
            self.image = QPixmap(file_name)
            self.update()

    def update_image_scale(self):
        """更新图片缩放比例"""
        self.image_scale = self.scale_slider.value() / 100.0
        self.update()

    def update_circle_size_label(self, value):
        """更新 Circle size 滑块旁边的 QLabel 显示的值"""
        self.circle_size_value_label.setText(str(value)) # 将 QLabel 的文本设置为滑块的当前值 (转换为字符串)

    def update_image_opacity(self):
        """更新图片透明度"""
        self.image_opacity = self.opacity_slider.value() / 100.0
        self.update()

    def update_curve_segments(self):
        """更新曲线绘制段数"""
        self.curve_segments = self.segments_slider.value()
        self.update()

    def update_outline_width(self):
        """更新描边粗细"""
        self.outline_width = self.circle_size_slider.value()
        self.update()

    def update_outline_opacity(self):
        """更新描边透明度"""
        self.outline_opacity = self.outline_opacity_slider.value() / 100.0
        self.update()

    def update_rect_scale(self):
        """更新矩形的大小，并连带缩放曲线和背景图片"""
        old_rect_scale = self.rect_scale
        self.rect_scale = self.rect_scale_slider.value() / 100.0
        scale_factor = self.rect_scale / old_rect_scale if old_rect_scale != 0 else 1.0

        center = QPoint(self.width() // 2, self.height() // 2)

        # 缩放控制点 (保持不变)
        for i in range(len(self.control_points)):
            self.control_points[i] = center + (self.control_points[i] - center) * scale_factor

        self.update()

    def update_circle_size(self): # 请检查函数名拼写是否完全一致！
        """更新描边粗细 (根据 Circle size 滑块值计算)"""
        circle_size_value = self.circle_size_slider.value() # 获取 Circle size 滑块的值 # 修改: 滑块变量名
        rect_height_large = int(self.width() * self.rect_scale * 3 / 4) # 计算大矩形高度

        # 应用公式计算描边粗细
        outline_width_calculated = (rect_height_large / 480) * (54.4 - 4.48 * circle_size_value) * 1.65
        if outline_width_calculated < 0 : # 确保描边粗细不为负值，最小值设为0
            outline_width_calculated = 0

        self.outline_width = max(0, outline_width_calculated)  # 确保描边粗细不为负值，取 0 和计算结果的较大值
        self.update()

    def import_slider(self):
        """从文件导入滑条路径"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Slider File", "", "Text Files (*.txt)")
        if file_name:
            with open(file_name, "r") as file:
                content = file.read().strip()
                # 解析滑条路径
                try:
                    # 示例格式：x,y,time,type,curve_type,B|...
                    parts = content.split(",")
                    if len(parts) >= 6 and parts[5].startswith("B|"):
                        # 第一个滑条点
                        start_x = int(parts[0])
                        start_y = int(parts[1])
                        self.control_points = [QPoint(start_x, start_y)]

                        # 解析剩余的滑条点
                        slider_points = parts[5][2:].split("|")  # 去掉 "B|"
                        for point in slider_points:
                            x, y = point.split(":")
                            self.control_points.append(QPoint(int(x), int(y)))

                        self.save_state()
                        self.update()
                        print(f"Slider imported from {file_name}")
                    else:
                        print("Invalid slider file format.")
                except Exception as e:
                    print(f"Error parsing slider file: {e}")

    def export_points(self):
        if not self.control_points:
            return

        # 打开文件对话框
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Control Points", "", "Text Files (*.txt)")
        if file_name:
            with open(file_name, "w") as file:
                # 按照 osu! 滑条路径格式导出
                if len(self.control_points) >= 2:
                    # 计算窗口中心
                    center_x = self.width() // 2
                    center_y = self.height() // 2

                    # 计算矩形的大小
                    rect_width = int(self.width() * self.rect_scale)
                    rect_height = int(rect_width * 3 / 4)
                    rect_x = center_x - rect_width // 2
                    rect_y = center_y - rect_height // 2

                    # 定义红色矩形在当前坐标系中的坐标
                    rect_bottom_left_current_x = rect_x
                    rect_bottom_left_current_y = rect_y + rect_height
                    rect_top_right_current_x = rect_x + rect_width
                    rect_top_right_current_y = rect_y

                    # 第一个控制点
                    first_point = self.control_points[0]
                    remapped_first_point = self.remap_coordinates(
                        first_point,
                        rect_bottom_left_current_x, rect_bottom_left_current_y,
                        rect_top_right_current_x, rect_top_right_current_y
                    )
                    file.write(
                        f"{int(remapped_first_point.x())},{int(remapped_first_point.y())},1000,2,0,B"
                    )

                    # 后续控制点
                    for point in self.control_points[1:]:
                        remapped_point = self.remap_coordinates(
                            point,
                            rect_bottom_left_current_x, rect_bottom_left_current_y,
                            rect_top_right_current_x, rect_top_right_current_y
                        )
                        file.write(f"|{int(remapped_point.x())}:{int(remapped_point.y())}")

                    # 滑条的其他参数（长度和重复次数）
                    file.write(",1,100\n")
                else:
                    print("至少需要两个控制点才能导出滑条路径。")
            print(f"Control points exported to {file_name}")

    def remap_coordinates(self, point, rect_bottom_left_x, rect_bottom_left_y, rect_top_right_x, rect_top_right_y):
            """
            将点坐标从当前坐标系重新映射到新的坐标系。
            **新的坐标系以红色矩形左下角为 (-65, 424)，右上角为 (575, -56)。** (已更新)

            Args:
                point: 要重新映射的 QPoint 对象 (当前坐标系).
                rect_bottom_left_x: 红色矩形左下角在当前坐标系中的 X 坐标.
                rect_bottom_left_y: 红色矩形左下角在当前坐标系中的 Y 坐标.
                rect_top_right_x: 红色矩形右上角在当前坐标系中的 X 坐标.
                rect_top_right_y: 红色矩形右上角在当前坐标系中的 Y 坐标.

            Returns:
                重新映射后的 QPoint 对象 (新的坐标系).
            """
            current_x = point.x()
            current_y = point.y()

            # **新的坐标系的范围 (已更新)**
            new_x_min = -65
            new_x_max = 575
            new_y_min = -56
            new_y_max = 424

            # 当前坐标系中红色矩形的宽度和高度
            rect_width_current = rect_top_right_x - rect_bottom_left_x
            rect_height_current = rect_bottom_left_y - rect_top_right_y

            if rect_width_current == 0 or rect_height_current == 0:
                return QPoint(0, 0)  # 避免除以零

            # 计算 X 坐标的比例和偏移
            scale_x = (new_x_max - new_x_min) / rect_width_current
            offset_x = new_x_min - rect_bottom_left_x * scale_x

            # 计算 Y 坐标的比例和偏移 (注意 Y 轴方向反转)
            scale_y = (new_y_max - new_y_min) / rect_height_current
            offset_y = new_y_max - rect_bottom_left_y * scale_y # 注意这里使用 new_y_max 和 rect_bottom_left_y

            # 应用映射
            new_x = scale_x * current_x + offset_x
            new_y = scale_y * current_y + offset_y

            return QPoint(int(new_x), int(new_y))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BezierCurveEditor()
    window.show()
    sys.exit(app.exec_())