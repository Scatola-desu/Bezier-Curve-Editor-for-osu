import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QSlider, QHBoxLayout, QLabel
)
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QPixmap
from PyQt5.QtCore import Qt, QPoint


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
        self.dragging_curve = False  # 是否正在拖动曲线
        self.last_mouse_pos = QPoint()  # 上次鼠标位置
        self.curve_scale = 1.0  # 曲线整体缩放比例
        self.outline_width = 5  # 描边粗细
        self.outline_opacity = 0.5  # 描边透明度
        self.rect_scale = 0.75  # 矩形默认大小为窗口的 75%
        self.rect_width = 0    # 矩形宽度（动态计算）
        self.rect_height = 0   # 矩形高度（动态计算）
        self.init_ui()

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
            ALT+左键 增加中间锚点<br>
            ALT+右键 删除锚点<br>
            滚轮 缩放/平移<br>
            左键 新增锚点<br>
            右键 修改锚点
            """,
            self
        )
        self.help_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);  /* 半透明黑色背景 */
                color: white;                          /* 文字颜色 */
                padding: 10px;                         /* 内边距 */
                border-radius: 5px;                    /* 圆角 */
                font-size: 12px;                       /* 字体大小 */
            }
        """)
        self.help_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 文字左对齐
        self.help_label.setFixedSize(200, 120)  # 固定大小
        self.help_label.move(self.width() - 220, self.height() - 340)  # 右下角位置

        # 隐藏帮助按钮
        self.hide_help_button = QPushButton("隐藏帮助", self)
        self.hide_help_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 150);  /* 半透明黑色背景 */
                color: white;                          /* 文字颜色 */
                padding: 5px;                          /* 内边距 */
                border-radius: 5px;                    /* 圆角 */
                font-size: 12px;                       /* 字体大小 */
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 200);  /* 鼠标悬停时背景变深 */
            }
        """)
        self.hide_help_button.setFixedSize(80, 30)  # 固定大小
        self.hide_help_button.move(self.width() - 90, self.height() - 60)  # 右下角，稍微上移
        self.hide_help_button.clicked.connect(self.toggle_help_visibility)

        # 默认显示帮助
        self.help_visible = True

        # 顶部布局（按钮和滑块）
        top_layout = QHBoxLayout()

        # 按钮样式
        button_style = """
            QPushButton {
                background-color: #3F7CAD;  /* 背景颜色 */
                color: white;               /* 文字颜色 */
                border-radius: 10px;        /* 圆角 */
                padding: 10px;              /* 内边距 */
                font-size: 14px;            /* 字体大小 */
                font-weight: bold;          /* 字体加粗 */
            }
            QPushButton:hover {
                background-color: #181D28;  /* 鼠标悬停时的背景颜色 */
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

        # 描边粗细滑块
        outline_width_label = QLabel("Outline Width:", self)
        outline_width_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(outline_width_label)
        self.outline_width_slider = QSlider(Qt.Horizontal, self)
        self.outline_width_slider.setMinimum(1)
        self.outline_width_slider.setMaximum(400)
        self.outline_width_slider.setValue(5)
        self.outline_width_slider.valueChanged.connect(self.update_outline_width)
        bottom_layout.addWidget(self.outline_width_slider)

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
        rect_scale_label = QLabel("4:3 Rectangle Scale:", self)
        rect_scale_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(rect_scale_label)
        self.rect_scale_slider = QSlider(Qt.Horizontal, self)
        self.rect_scale_slider.setMinimum(10)  # 最小缩放比例为 10%
        self.rect_scale_slider.setMaximum(100)  # 最大缩放比例为 100%
        self.rect_scale_slider.setValue(int(self.rect_scale * 100))  # 默认值为 90%
        self.rect_scale_slider.valueChanged.connect(self.update_rect_scale)
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
            self.help_label.move(self.width() - 220, self.height() - 360)  # 稍微上移
            self.hide_help_button.move(self.width() - 90, self.height() - 260)  # 稍微上移

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
            self.future.append((self.control_points.copy(), self.image, self.image_scale, self.image_opacity, self.curve_scale, self.outline_width, self.outline_opacity))
            # 恢复到上一个状态
            last_state = self.history.pop()
            self.control_points = last_state[0]
            self.image = last_state[1]
            self.image_scale = last_state[2]
            self.image_opacity = last_state[3]
            self.curve_scale = last_state[4]
            self.outline_width = last_state[5]
            self.outline_opacity = last_state[6]
            self.update()

    def redo(self):
        if self.future:
            # 将当前状态保存到 history
            self.history.append((self.control_points.copy(), self.image, self.image_scale, self.image_opacity, self.curve_scale, self.outline_width, self.outline_opacity))
            # 恢复到下一个状态
            next_state = self.future.pop()
            self.control_points = next_state[0]
            self.image = next_state[1]
            self.image_scale = next_state[2]
            self.image_opacity = next_state[3]
            self.curve_scale = next_state[4]
            self.outline_width = next_state[5]
            self.outline_opacity = next_state[6]
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # 鼠标中键：开始拖动曲线
            self.dragging_curve = True
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
                    if (event.pos() - point).manhattanLength() < 10:
                        self.dragging_point = i
                        break

    def mouseMoveEvent(self, event):
        if self.dragging_curve:
            # 鼠标中键拖动：整体平移曲线
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.save_state()
            for i in range(len(self.control_points)):
                self.control_points[i] += delta
            self.update()
        elif self.dragging_point is not None:
            # 拖动控制点
            self.save_state()
            self.control_points[self.dragging_point] = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # 停止拖动曲线
            self.dragging_curve = False
        elif event.button() == Qt.RightButton:
            self.dragging_point = None

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
            scaled_image = self.image.scaled(
                int(self.image.width() * self.image_scale),
                int(self.image.height() * self.image_scale),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            # 将图片绘制在窗口中心
            image_x = center_x - scaled_image.width() // 2
            image_y = center_y - scaled_image.height() // 2
            painter.drawPixmap(image_x, image_y, scaled_image)

        # 重置透明度为 1.0，避免影响后续绘制
        painter.setOpacity(1.0)

        # 计算矩形的大小
        self.rect_width = int(self.width() * self.rect_scale)
        self.rect_height = int(self.rect_width * 3 / 4)  # 宽高比例为 4:3

        # 计算矩形的左上角坐标
        rect_x = center_x - self.rect_width // 2
        rect_y = center_y - self.rect_height // 2

        # 绘制矩形
        rect_color = QColor(255, 0, 0)  # 红色
        rect_color.setAlpha(128)  # 半透明（50% 透明度）
        painter.setPen(QPen(rect_color, 2))  # 描边宽度为 2
        painter.setBrush(Qt.NoBrush)  # 无填充
        painter.drawRect(rect_x, rect_y, self.rect_width, self.rect_height)

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
        self.history.append((self.control_points.copy(), self.image, self.image_scale, self.image_opacity, self.curve_scale, self.outline_width, self.outline_opacity))
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
        self.outline_width = self.outline_width_slider.value()
        self.update()

    def update_outline_opacity(self):
        """更新描边透明度"""
        self.outline_opacity = self.outline_opacity_slider.value() / 100.0
        self.update()

    def update_rect_scale(self):
        """更新矩形的大小"""
        self.rect_scale = self.rect_scale_slider.value() / 100.0
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
                    # 计算平移量
                    start_x = self.control_points[0].x()
                    start_y = self.control_points[0].y()
                    delta_x = 256 - start_x  # 目标 x 坐标 - 当前起始点 x 坐标
                    delta_y = 190 - start_y  # 目标 y 坐标 - 当前起始点 y 坐标

                    # 平移后的起始点
                    translated_start_x = start_x + delta_x
                    translated_start_y = start_y + delta_y
                    file.write(f"{translated_start_x},{translated_start_y},1000,2,0,B")

                    # 平移剩余的滑条点
                    for point in self.control_points[1:]:
                        translated_x = point.x() + delta_x
                        translated_y = point.y() + delta_y
                        file.write(f"|{translated_x}:{translated_y}")

                    # 滑条的其他参数（长度和重复次数）
                    file.write(",1,100\n")
                else:
                    print("至少需要两个控制点才能导出滑条路径。")
            print(f"Control points exported to {file_name}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BezierCurveEditor()
    window.show()
    sys.exit(app.exec_())