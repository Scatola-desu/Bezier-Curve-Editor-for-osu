from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QSlider, QHBoxLayout, QLabel, QMessageBox, QShortcut
)
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QPixmap, QBrush, QVector2D
from PyQt5.QtCore import Qt, QPoint, QLocale, QLineF, QTimer, QPropertyAnimation, QRect
import sys
import math
import pickle
import os
import datetime

class BezierCurveEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True) 
        self.setWindowTitle("Bezier Curve Editor for osu!")
        self.setGeometry(100, 100, 1600, 900)
        self.control_points = []  # 存储控制点
        self.history = []  # 操作历史
        self.future = []  # 撤销后的操作
        self.max_history_size = 20  # 设置最大历史记录长度
        self.dragging_point = None  # 当前拖动的控制点索引
        self.image = None  # 导入的图片
        self.image_scale = 1.0  # 图片缩放比例
        self.image_opacity = 1.0  # 图片透明度
        self.curve_segments = 100  # 曲线绘制段数

        self.dragging_curve_only = False  # 是否正在单独拖动曲线 (新增)
        self.dragging_curve_and_image = False  # 是否正在拖动曲线和图片 (新增)
        self.is_ctrl_right_dragging = False  # 是否正在拖动曲线的局部
        self.last_mouse_pos = QPoint()  # 上次鼠标位置
        self.drag_start_pos = None
        self.locked_closest_point = None
        self.locked_t = None # 保存拖动开始时的 t 值

        self.curve_scale = 1.0  # 曲线整体缩放比例
        self.outline_width = 4  # 描边粗细 (初始值，之后会被计算的值覆盖)
        self.outline_opacity = 0.85  # 描边透明度
        self.rect_scale = 0.95  # 矩形默认大小为窗口的 95%
        self.rect_width = 0    # 矩形宽度（动态计算）
        self.rect_height = 0   # 矩形高度（动态计算）
        self.image_offset_x = 0  # 图片水平偏移量
        self.image_offset_y = 0  # 图片垂直偏移量
        self.preview_point = None  # 预览点的 QPoint 对象
        self.is_preview_enabled = False  # 布尔值，指示是否启用预览
        self.preview_segment_index = -1 # 预览插入线段的索引
        self.highlighted_segment_index = None
        self.is_dragging_control_point = False
        self.pre_selected_point_index = None
        self.is_visualization_enabled = True
        self.rect_height_large = 0
        self.is_right_button_pressed = False
        self.cached_curve_points = None  # 初始化缓存为空
        self.update_curve_cache()  # 初始调用，计算缓存
        self.is_alt_pressed = False  # 新增：跟踪 Alt 键状态
        self.get_button_texts()

        self.is_ctrl_pressed = False
        self.closest_curve_point = None  # 最近曲线点
        self.anchor_influences = []  # 锚点影响力列表

        # 初始化自动备份
        self.backup_file = "bezier_Curve_backup.pkl"
        self.backup_counter = 0  # 历史记录更新计数器
        self.backup_threshold = 5  # 每 5 次历史记录更新触发备份
        self.restore_backup_on_startup() # 检查并恢复备份

        # 绑定 Ctrl + S 快捷键
        self.save_shortcut = QShortcut(Qt.Key_S | Qt.ControlModifier, self)
        self.save_shortcut.activated.connect(self.quick_save)

        self.init_ui()

        # 在 init_ui() 之后，根据初始 Circle size 值计算 outline_width
        initial_circle_size_value = self.circle_size_slider.value() # 获取 Circle size 滑块的初始值
        estimated_rect_height_large = int(self.width() * self.rect_scale * 3 / 4) # 估计初始矩形高度
        initial_outline_width_calculated = (estimated_rect_height_large / 480) * (54.4 - 4.48 * initial_circle_size_value) * 1.65
        self.outline_width = max(0, initial_outline_width_calculated) # 确保非负值

        self.update_circle_size() #  **重要:** 初始调用 update_circle_size，确保初始描边宽度正确设置并应用到界面上

        # 初始化快速保存提示标签（居中）
        self.save_label = QLabel(self.msg_quick_save_success, self)
        self.save_label.setStyleSheet("""
            QLabel {
                background-color: rgba(94, 184, 75, 180);
                color: white;
                padding: 5px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.save_label.setVisible(False)
        # 设置居中位置
        label_width = self.save_label.sizeHint().width()
        label_height = self.save_label.sizeHint().height()
        self.save_label.move((self.width() - label_width) // 2, (self.height() - label_height) // 2)

    def get_button_texts(self):
        """根据系统语言加载按钮文本"""
        system_locale_name = QLocale.system().name()
        is_chinese_system = system_locale_name.startswith("zh")

        # 根据系统语言选择对应的文本
        if is_chinese_system:
            self.button_text_export_control_points = "导出控制点"
            self.button_text_import_image = "导入图像"
            self.button_text_image_scale = "图像缩放"
            self.button_text_image_opacity = "图像透明度"
            self.button_text_curve_segments = "曲线段数"
            self.button_text_circle_size = "圆圈大小(CS)"
            self.button_text_outline_opacity = "滑条透明度"
            self.button_text_playfield_boundary = "游戏&编辑器边界"
            self.button_text_import_slider = "导入滑条"
            self.button_text_enable_visualizations = "可视化效果已关闭"
            self.button_text_disable_visualizations = "可视化效果已打开"
            self.button_text_show_help = "显示帮助"
            self.button_text_hide_help = "隐藏帮助"

            self.delete_control_point_msg = "锚点数量已达最小值（2 个），无法继续删除！"
            self.msg_slider_import_success = "滑条已成功从 {file_name} 导入！"
            self.msg_slider_import_failed = "导入滑条失败：{error}"
            self.msg_points_export_min = "至少需要两个控制点才能导出！"
            self.msg_points_export_success = "控制点已成功导出到 {file_name}！"
            self.msg_title_prompt = "提示"
            self.msg_restore_backup = "检测到上次未保存的备份数据，是否恢复？"
            self.msg_title_backup = "恢复备份"
            self.msg_restore_backup2 = "无法恢复备份数据：{error}"
            self.msg_title_backup2 = "恢复失败"
            self.msg_close_prompt = "是否保存当前工作并退出？"
            self.msg_close_title = "退出程序"
            self.msg_quick_save_success = "快速保存成功"

            self.help_label_text = """
                操作提示：<br>
                <b><span style="color:#50B9FE">左键</span></b> 新增锚点<br>
                <b><span style="color:#AC9178">右键</span></b> 拖动锚点<br>
                <b><span style="color:#DCDC8B">滚轮</span></b> 缩放/平移<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#50B9FE">左键</span></b> 增加中间锚点<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#354EEC">CTRL</span>+<span style="color:#50B9FE">左键</span></b> 增加头尾锚点<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#AC9178">右键</span></b> 删除锚点<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#DCDC8B">中键</span></b> 拖动曲线和图片<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#AC9178">右键</span></b> 拖动曲线变形<br>
                <b><span style="color:#354EEC">CTRL</span>+S</b> 快速保存<br>
                <b><span style="color:#354EEC">CTRL</span>+Z</b> 撤销<br>
                <b><span style="color:#354EEC">CTRL</span>+Y</b> 重做<br>
            """
        else:
            self.button_text_export_control_points = "Export Control Points"
            self.button_text_import_image = "Import Image"
            self.button_text_image_scale = "Image Scale"
            self.button_text_image_opacity = "Image Opacity"
            self.button_text_curve_segments = "Curve Segments"
            self.button_text_circle_size = "Circle Size"
            self.button_text_outline_opacity = "Slider Opacity"
            self.button_text_playfield_boundary = "Playfield Boundary"
            self.button_text_import_slider = "Import Slider"
            self.button_text_enable_visualizations = "Visualization off"
            self.button_text_disable_visualizations = "Visualization on"
            self.button_text_show_help = "Show Help"
            self.button_text_hide_help = "Hide Help"

            self.delete_control_point_msg = "The number of anchor points has reached the minimum (2) and cannot be deleted further!"
            self.msg_slider_import_success = "Slider imported successfully from {file_name}!"
            self.msg_slider_import_failed = "Failed to import slider: {error}"
            self.msg_points_export_min = "At least two control points are required to export!"
            self.msg_points_export_success = "Control points exported successfully to {file_name}!"
            self.msg_title_prompt = "Prompt"
            
            self.msg_restore_backup = "Detected unsaved backup data from the last session. Do you want to restore it?"
            self.msg_title_backup = "Restore Backup"
            self.msg_restore_backup2 = "Unable to restore backup data: {error}"
            self.msg_title_backup2 = "Restore Failed"
            self.msg_close_prompt = "Do you want to save your current work and exit?"
            self.msg_close_title = "Exit Program"
            self.msg_quick_save_success = "Quick Save Successful"

            self.help_label_text = """
                Operation Hints:<br>
                <b><span style="color:#50B9FE">Left Click:</span></b> Add Anchor Point<br>
                <b><span style="color:#AC9178">Right Click:</span></b> Modify Anchor Point<br>
                <b><span style="color:#DCDC8B">Mouse Wheel:</span></b> Zoom/Pan<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#50B9FE">Left Click:</span></b> Add Mid Anchor Point<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#354EEC">CTRL</span>+<span style="color:#50B9FE">Left Click</span>:</b> Add Start/End Anchor Point<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#AC9178">Right Click:</span></b> Delete Anchor Point<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#DCDC8B">Middle Click:</span></b> Drag Curve and Image<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#AC9178">Right Click:</span></b> Deform Curve<br>
                <b><span style="color:#354EEC">CTRL</span>+S:</b> Quick Save<br>
                <b><span style="color:#354EEC">CTRL</span>+Z:</b> Undo<br>
                <b><span style="color:#354EEC">CTRL</span>+Y:</b> Redo<br>
            """


    def bernstein_basis_polynomial(self, n, i, t):
        if not (0 <= i <= n) or not (0 <= t <= 1):
            return 0
        if i < 0 or n < 0 or (n - i) < 0:
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
        self.help_label = QLabel(self.help_label_text, self) 
        self.help_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);  /* 半透明黑色背景 */
                color: white;                            /* 文字颜色 */
                padding: 10px;                           /* 内边距 */
                border-radius: 5px;                      /* 圆角 */
                font-size: 12px;                         /* 字体大小 */
            }
        """)
        self.help_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 文字左对齐
        self.help_label.setWordWrap(True)  # 启用自动换行功能
        self.help_label.adjustSize()  # 根据内容自适应大小
        self.update_help_position()  # 动态设置初始位置

        # 隐藏帮助按钮
        self.hide_help_button = QPushButton(self.button_text_hide_help,self)
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
        self.hide_help_button.move(self.width() - 90, self.height() - 150)  # 右下角，稍微上移 (根据帮助标签高度调整位置)
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

        # 创建可视化效果开关按钮
        self.visualization_button = QPushButton(
            self.button_text_disable_visualizations if self.is_visualization_enabled else self.button_text_enable_visualizations, self)
        self.visualization_button.setStyleSheet(button_style)
        self.visualization_button.setCheckable(True)
        self.visualization_button.setChecked(not self.is_visualization_enabled)
        self.visualization_button.clicked.connect(self.toggle_visualization_display)
        top_layout.addWidget(self.visualization_button)

        # 导入图片按钮
        import_button = QPushButton(self.button_text_import_image)
        import_button.setStyleSheet(button_style)
        import_button.clicked.connect(self.import_image)
        top_layout.addWidget(import_button)

        # 图片缩放滑块
        scale_label = QLabel(self.button_text_image_scale)
        scale_label.setStyleSheet("color: #FFFFFF;")
        top_layout.addWidget(scale_label)
        self.scale_slider = QSlider(Qt.Horizontal, self)
        self.scale_slider.setMinimum(10)
        self.scale_slider.setMaximum(200)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.update_image_scale)
        top_layout.addWidget(self.scale_slider)

        # 图片透明度滑块
        opacity_label = QLabel(self.button_text_image_opacity)
        opacity_label.setStyleSheet("color: #FFFFFF;")
        top_layout.addWidget(opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setMinimum(0)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_image_opacity)
        top_layout.addWidget(self.opacity_slider)

        # 曲线绘制段数滑块
        segments_label = QLabel(self.button_text_curve_segments)
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

        # Circle Size 滑块
        circle_size_label = QLabel(self.button_text_circle_size)
        circle_size_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(circle_size_label)
        self.circle_size_slider = QSlider(Qt.Horizontal, self)
        self.circle_size_slider.setMinimum(0)
        self.circle_size_slider.setMaximum(10)
        self.circle_size_slider.setValue(4)
        self.circle_size_slider.valueChanged.connect(self.update_circle_size)

        # **新增: 显示 Circle size 滑块值的 QLabel**
        self.circle_size_value_label = QLabel(str(self.circle_size_slider.value()), self)
        self.circle_size_value_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(self.circle_size_value_label)

        # 将滑块的 valueChanged 信号连接到更新 QLabel 的函数
        self.circle_size_slider.valueChanged.connect(self.update_circle_size_label)

        bottom_layout.addWidget(self.circle_size_slider)

        # 描边透明度滑块
        outline_opacity_label = QLabel(self.button_text_outline_opacity)
        outline_opacity_label.setStyleSheet("color: #FFFFFF;")
        bottom_layout.addWidget(outline_opacity_label)
        self.outline_opacity_slider = QSlider(Qt.Horizontal, self)
        self.outline_opacity_slider.setMinimum(0)
        self.outline_opacity_slider.setMaximum(90)
        self.outline_opacity_slider.setValue(85)
        self.outline_opacity_slider.valueChanged.connect(self.update_outline_opacity)
        bottom_layout.addWidget(self.outline_opacity_slider)

        # 矩形大小滑块
        rect_scale_label = QLabel(self.button_text_playfield_boundary)
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
        import_slider_button = QPushButton(self.button_text_import_slider)
        import_slider_button.setStyleSheet(button_style)
        import_slider_button.clicked.connect(self.import_slider)
        bottom_layout.addWidget(import_slider_button)

        # 导出按钮
        export_button = QPushButton(self.button_text_export_control_points)
        export_button.setStyleSheet(button_style)
        export_button.clicked.connect(self.export_points)
        bottom_layout.addWidget(export_button)

        # 将底部布局添加到主布局
        main_layout.addLayout(bottom_layout)

        # 设置顶部布局的对齐方式
        main_layout.setAlignment(top_layout, Qt.AlignTop)

    def toggle_visualization_display(self):
        """
        切换可视化效果的显示状态 (槽函数，连接到开关按钮的 clicked 信号)
        """
        self.is_visualization_enabled = not self.is_visualization_enabled
        self.visualization_button.setText(
            self.button_text_disable_visualizations if self.is_visualization_enabled else self.button_text_enable_visualizations
        )
        self.update()

    def toggle_help_visibility(self):
        """切换帮助的可见性"""
        self.help_visible = not self.help_visible
        self.help_label.setVisible(self.help_visible)
        if self.help_visible:
            self.hide_help_button.setText(self.button_text_hide_help)
        else:
            self.hide_help_button.setText(self.button_text_show_help) 

    def update_help_position(self):
        """更新帮助标签的右下角位置"""
        # 获取帮助标签的推荐大小
        help_size = self.help_label.sizeHint()
        help_width = help_size.width() + 20  # 增加 padding
        help_height = help_size.height() + 20
        # 计算右下角位置，留出 10px 边距
        label_x = self.width() - help_width - 10
        label_y = self.height() - help_height - 10
        self.help_label.move(label_x, label_y)

    def resizeEvent(self, event):
        """窗口大小变化时更新帮助位置"""
        super().resizeEvent(event)
        if hasattr(self, 'help_label') and hasattr(self, 'hide_help_button'):
            self.update_help_position()  # 更新帮助标签位置
            self.hide_help_button.move(self.width() - 100, self.height() - 85) 
        if hasattr(self, 'save_label'):
            # 更新保存提示位置为屏幕中心
            label_width = self.save_label.sizeHint().width()
            label_height = self.save_label.sizeHint().height()
            self.save_label.move((self.width() - label_width) // 2, (self.height() - label_height) // 2)
        self.update_circle_size()   # 在窗口大小改变时调用 update_circle_size 函数，更新描边粗细
        self.update_curve_cache()  # 刷新缓存
        self.update()              # 并请求重绘，应用新的描边粗细

    def keyPressEvent(self, event):
        # 撤销操作 (Ctrl+Z)
        if event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo()
        # 恢复操作 (Ctrl+Y)
        elif event.key() == Qt.Key_Y and event.modifiers() == Qt.ControlModifier:
            self.redo()

    def undo(self):
        if self.history:
            self.future.append((self.control_points.copy(),))  # 保存当前状态到 future
            last_state = self.history.pop()  # 恢复上一个状态
            self.control_points = last_state[0]
            self.pre_selected_point_index = None
            self.update_curve_cache()
            self.update()
        else:
            print("No history to undo")

    def redo(self):
        if self.future:
            # 将当前状态保存到 history
            self.history.append((self.control_points.copy(),))
            # 恢复到下一个状态
            next_state = self.future.pop()
            self.control_points = next_state[0]
            self.update_curve_cache()  # 刷新缓存
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
            # Alt + Ctrl：添加头尾锚点
            if event.modifiers() & Qt.AltModifier and event.modifiers() & Qt.ControlModifier and len(self.control_points) >= 2:
                self.save_state()
                insert_index = self.get_insert_position(event.pos())
                if insert_index is not None:
                    if insert_index == 0:
                        self.control_points.insert(0, event.pos())  # 添加到起点
                    else:
                        self.control_points.append(event.pos())     # 添加到终点
                    self.update_curve_cache()
                    self.update()
            # 仅 Alt：添加中间锚点
            elif event.modifiers() == Qt.AltModifier:
                self.insert_control_point(event.pos())
            else:
                self.save_state()
                self.control_points.append(event.pos())
                self.update_curve_cache()
                self.update()
        elif event.button() == Qt.RightButton:
            self.is_right_button_pressed = True
            if event.modifiers() == Qt.ControlModifier and self.closest_curve_point is not None:
                # Ctrl + 右键：开始拖动曲线变形
                self.save_state()  # 保存当前状态以支持撤销
                self.is_ctrl_right_dragging = True
                self.drag_start_pos = event.pos()
                self.locked_closest_point = self.closest_curve_point  # 锁定 closest_curve_point
                # 计算并锁定 t 值
                min_distance = float('inf')
                closest_idx = -1
                for i, point in enumerate(self.cached_curve_points):
                    distance = self.distance(self.locked_closest_point, point)
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i
                self.locked_t = closest_idx / self.curve_segments if self.curve_segments > 0 else 0
            elif event.modifiers() == Qt.AltModifier:
                # Alt + 右键：删除点击的控制点
                self.delete_control_point(event.pos())
            else:
                # 普通右键：检查是否点击了控制点
                for i, point in enumerate(self.control_points):
                    if self.distance(point, event.pos()) < 10:
                        self.dragging_point = i
                        self.save_state()
                        self.is_dragging_control_point = True  # 请确认这行代码是否已添加！
                        self.drag_start_point = event.pos()
                        self.update()
                        return
            self.update()

    def mouseMoveEvent(self, event):
        self.pre_selected_point_index = None  # 每次鼠标移动时，先重置预选中锚点索引为 None
        min_distance_pre_select = float('inf') # 初始化最小距离为无穷大
        pre_select_threshold = 10 # 预选择的距离阈值，可以根据需要调整

        if not self.is_ctrl_pressed:
            for i, point in enumerate(self.control_points):
                distance = self.distance(point, event.pos())
                if distance < pre_select_threshold:
                    if distance < min_distance_pre_select: # 找到更近的锚点时才更新预选
                        min_distance_pre_select = distance
                        self.pre_selected_point_index = i # 更新预选中锚点索引

        if self.is_ctrl_right_dragging and self.closest_curve_point is not None:
            # Ctrl + 右键拖动：变形曲线
            current_pos = event.pos()
            delta = current_pos - self.drag_start_pos  # 计算鼠标移动向量

            # 使用固定的 self.locked_t 计算拖动
            t = self.locked_t
            curve_order = len(self.control_points) - 1
            for i in range(len(self.control_points)):
                influence = self.bernstein_basis_polynomial(curve_order, i, t)
                move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                self.control_points[i] = self.control_points[i] + move_vector

            self.drag_start_pos = current_pos  # 更新起始位置为当前位置
            self.update_curve_cache()  # 刷新曲线缓存
            self.update()
            return
        if self.dragging_curve_and_image:
            # Ctrl + 鼠标中键拖动：整体平移曲线和图片 (修改)
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()

            # 平移曲线
            for i in range(len(self.control_points)):
                self.control_points[i] += delta

            # 平移图片
            self.image_offset_x += delta.x()
            self.image_offset_y += delta.y()

            self.update_curve_cache()  # 刷新缓存
            self.update()
            return
        elif self.dragging_curve_only:
            # 鼠标中键拖动：单独平移曲线 (新增)
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()

            # 平移曲线
            for i in range(len(self.control_points)):
                self.control_points[i] += delta

            self.update_curve_cache()  # 刷新缓存
            self.update() # 只更新曲线，图片不移动
            return
        elif self.dragging_point is not None:
            # 拖动控制点
            self.control_points[self.dragging_point] = event.pos()
            self.update_curve_cache()  # 刷新缓存
            self.update()
            return
        elif self.is_ctrl_right_dragging and self.locked_closest_point is not None:
            current_pos = event.pos()
            delta = current_pos - self.drag_start_pos
            t = self.locked_t
            curve_order = len(self.control_points) - 1
            for i in range(len(self.control_points)):
                influence = self.bernstein_basis_polynomial(curve_order, i, t)
                move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                self.control_points[i] = self.control_points[i] + move_vector
            self.drag_start_pos = current_pos
            self.update_curve_cache()
            self.update()
            return
        # 更新修饰键状态并调用预览函数
        self.is_ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
        self.is_alt_pressed = bool(event.modifiers() & Qt.AltModifier)
        self.update_preview_slider(event)

        ctrl_highlight_threshold = self.outline_width * 0.9 if self.outline_width > 0 else 50 # 动态计算距离阈值, 默认值 50
        self.update_ctrl_highlight(event, ctrl_highlight_threshold) # 调用 Ctrl 高亮更新函数
        self.update() # 触发重绘，更新高亮和预览显示

    def calculate_bezier_curve(self, control_points, num_segments):
        """
        使用德卡斯特里奥算法计算贝塞尔曲线上的点.

        Args:
            control_points: 控制点列表 (QPointF 列表).
            num_segments:  曲线分段数.

        Returns:
            曲线上的点列表 (QPointF 列表).
        """
        curve_points = []
        if not control_points:
            return curve_points

        for i in range(num_segments + 1):
            t = i / num_segments
            points = control_points[:]  # 复制控制点列表，避免修改原始列表
            n = len(points)
            for r in range(1, n):
                for j in range(n - r):
                    p1 = points[j]
                    p2 = points[j + 1]
                    points[j] = p1 + (p2 - p1) * t  # 线性插值
            curve_points.append(points[0]) # 德卡斯特里奥算法的最终点

        return curve_points

    def update_curve_cache(self):
        """刷新贝塞尔曲线缓存，使用 calculate_bezier_point 逐步计算"""
        if len(self.control_points) >= 2:
            self.cached_curve_points = []
            for t in range(0, self.curve_segments + 1):
                t_normalized = t / self.curve_segments
                point = self.calculate_bezier_point(t_normalized, self.control_points)
                self.cached_curve_points.append(point)
        else:
            self.cached_curve_points = None  # 如果控制点少于2个，清空缓存

    def interpolate_color(self, offset, max_offset, max_color="#f177ae", min_color="#00BECA" ):
        """根据偏移量插值计算颜色，从 #00beca 到 #f177ae"""
        if max_offset == 0:
            return QColor(min_color)  # 无偏移时返回最小颜色
        
        # 定义颜色范围
        min_color = QColor(min_color)
        max_color = QColor(max_color)
        
        # 计算插值比例
        ratio = min(offset / max_offset, 1.0)  # 限制在 [0, 1] 区间
        
        # 线性插值计算 RGB
        r = int(min_color.red() + (max_color.red() - min_color.red()) * (ratio ** 3))
        g = int(min_color.green() + (max_color.green() - min_color.green()) * (ratio ** 3))
        b = int(min_color.blue() + (max_color.blue() - min_color.blue()) * (ratio ** 3))
        
        return QColor(r, g, b)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # 停止拖动曲线和图片/或单独拖动曲线 (修改)
            self.dragging_curve_only = False
            self.dragging_curve_and_image = False
        elif event.button() == Qt.RightButton:
            self.is_right_button_pressed = False
            self.dragging_point = None
            self.is_dragging_control_point = False
            self.is_ctrl_right_dragging = False  # 结束 Ctrl + 右键拖动
            self.drag_start_pos = None           # 清空拖动起始位置
            self.locked_closest_point = None
            self.locked_t = None  # 清理 locked_t
            self.update()

    def wheelEvent(self, event):
        # 滚轮：整体缩放曲线
        if not self.is_ctrl_pressed and not self.is_alt_pressed:
            self.save_state()
            delta = event.angleDelta().y() / 120  # 获取滚轮滚动方向
            scale_factor = 1.05 if delta > 0 else 0.95
            self.curve_scale *= scale_factor

            # 以窗口中心为基准缩放
            center = QPoint(self.width() // 2, self.height() // 2)
            for i in range(len(self.control_points)):
                self.control_points[i] = center + (self.control_points[i] - center) * scale_factor
            self.update_curve_cache()  # 刷新缓存
            self.update()

    def insert_control_point(self, pos):
        """在最近的两个连续控制点中间插入新控制点 (增加距离阈值，并使用鼠标位置作为插入点)"""
        if len(self.control_points) < 2:
            return

        closest_distance = float('inf')
        insert_segment_index = -1
        distance_threshold = self.rect_height_large * 0.11 # self.outline_width * 0.85

        # 遍历所有线段，寻找最近距离的线段
        for i in range(len(self.control_points) - 1):
            segment_start_point = self.control_points[i]
            segment_end_point = self.control_points[i + 1]
            segment_distance = self.point_to_line_distance(pos, segment_start_point, segment_end_point)

            if segment_distance < closest_distance:
                closest_distance = segment_distance
                insert_segment_index = i + 1

        # 只有当最近距离小于阈值时才插入
        if insert_segment_index != -1 and closest_distance <= distance_threshold:
            # 插入位置策略更改为当前鼠标位置 pos
            new_point = pos #  直接使用鼠标点击位置 pos 作为新控制点的位置

            self.save_state()
            self.control_points.insert(insert_segment_index, new_point)
            self.update_curve_cache()  # 刷新缓存
            self.update()

    def delete_control_point(self, pos):
        """删除点击的控制点"""
        if len(self.control_points) <= 2:
        # 弹出提示窗口
            msg = QMessageBox(self)
            msg.setWindowTitle(self.msg_title_prompt)
            msg.setText(self.delete_control_point_msg)
            msg.setStandardButtons(QMessageBox.Ok)
            # msg.setStyleSheet("QMessageBox { background-color: #1A1A1A; color: #FFFFFF; } QPushButton { background-color: #007AFF; color: #FFFFFF; }")
            msg.exec_()
            return  # 禁止删除，直接返回
        
        for i, point in enumerate(self.control_points):
            if (pos - point).manhattanLength() < 10:
                self.save_state()
                self.control_points.pop(i)
                # 同步更新高亮索引
                if self.highlighted_segment_index is not None and self.highlighted_segment_index >= i:
                    if self.highlighted_segment_index > 0:
                        self.highlighted_segment_index -= 1
                    else:
                        self.highlighted_segment_index = None
                if self.pre_selected_point_index is not None:
                    if i < self.pre_selected_point_index:
                        self.pre_selected_point_index -= 1
                    elif i == self.pre_selected_point_index:
                        self.pre_selected_point_index = None
                self.update_curve_cache()  # 刷新缓存
                self.update()
                break

    def point_to_line_distance(self, point, line_point1, line_point2): #  函数名保持不变
        """计算点到线段的距离 (版本 2: 点积 + 向量长度平方)""" #  可以更新函数注释
        if line_point1 == line_point2:
            return QLineF(line_point1, point).length()

        ap = point - line_point1
        ab = line_point2 - line_point1

        ab_squared_length = QVector2D(ab).lengthSquared()

        if ab_squared_length == 0:
            return QLineF(line_point1, point).length()

        param = QVector2D.dotProduct(QVector2D(ap), QVector2D(ab)) / ab_squared_length

        if param <= 0:
            return QLineF(line_point1, point).length()
        elif param >= 1:
            return QLineF(line_point2, point).length()
        else:
            projection_point = line_point1 + ab * param
            return QLineF(projection_point, point).length()

    def update_ctrl_highlight(self, event, ctrl_highlight_threshold):
        """更新 Ctrl 键高亮功能：计算最近点和锚点影响力"""
        self.is_ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
        if self.is_ctrl_pressed and self.cached_curve_points is not None and len(self.cached_curve_points) > 0:
            # 计算鼠标与曲线的最近点
            min_distance = float('inf')
            closest_idx = -1
            for i, point in enumerate(self.cached_curve_points):
                distance = self.distance(event.pos(), point)
                if distance < min_distance:
                    min_distance = distance
                    closest_idx = i
            
            if min_distance < ctrl_highlight_threshold:
                self.closest_curve_point = self.cached_curve_points[closest_idx]
                t = closest_idx / self.curve_segments  # 归一化 t 值
                
                # 计算每个锚点的影响力
                self.anchor_influences = []
                curve_order = len(self.control_points) - 1
                for i in range(len(self.control_points)):
                    influence = self.bernstein_basis_polynomial(curve_order, i, t)
                    self.anchor_influences.append(influence)
            else:
                self.closest_curve_point = None
                self.anchor_influences = []
        else:
            self.closest_curve_point = None
            self.anchor_influences = []

    def draw_ctrl_highlight(self, painter):
        """绘制 Ctrl 键高亮效果：最近点和锚点影响力圆圈"""
        if self.is_ctrl_pressed and self.closest_curve_point and not self.is_alt_pressed:
            # 如果正在拖动，使用 locked_t 计算圆形位置
            if self.is_ctrl_right_dragging and self.locked_t is not None:
                # 从当前曲线中计算基于 locked_t 的位置
                t = self.locked_t
                closest_point = self.calculate_bezier_point(t, self.control_points)
            else:
                closest_point = self.closest_curve_point
            
            # 绘制最近点（蓝色实心圆）
            painter.setBrush(QBrush(QColor("#495CDA")))
            painter.setPen(Qt.NoPen)
            painter.setOpacity(0.5 if self.is_ctrl_right_dragging else 1)

            base_radius = 16 if self.is_ctrl_right_dragging else 8  # 基础半径
            feather_steps = 5  # 羽化层数
            feather_spread = 1.5  # 羽化扩展倍数（控制羽化范围）

            # 绘制羽化效果
            if self.is_visualization_enabled:
                for i in range(feather_steps, -1, -1):  # 从外到内绘制
                    radius = base_radius * (1 + feather_spread * (i / feather_steps))
                    alpha = 1.0 - (i / feather_steps)  # 从全透明到不透明
                    color = QColor("#495CDA")
                    color.setAlphaF(alpha * 0.8)  # 调整总体透明度
                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(closest_point, radius, radius)
            else:
                painter.drawEllipse(closest_point, base_radius, base_radius)

            # 绘制锚点影响力圆圈（动态颜色）
            if self.anchor_influences and len(self.anchor_influences) <= len(self.control_points) and self.is_visualization_enabled:
                max_influence = max(self.anchor_influences) if max(self.anchor_influences) > 0 else 1.0
                max_influence_idx = self.anchor_influences.index(max_influence)  # 最大影响力点的索引
                
                # 存储筛选出的锚点信息
                anchor_data = []

                for i, influence in enumerate(self.anchor_influences):
                    normalized_influence = influence / max_influence
                    radius = 4 + 9 * (normalized_influence) ** 3  # 半径 4-12
                    alpha = normalized_influence  # 透明度 0.2-1.0
                    pen_width =  6 * normalized_influence  # 描边粗细 1-3
                    
                    # 动态颜色插值，默认最大为 rgb(72, 75, 100)
                    if i == max_influence_idx:
                        ring_color = QColor("#354eec")  # 最大影响力点为红色
                        ring_color.setAlphaF(1)
                    else:
                        ring_color = self.interpolate_color(influence, max_influence, max_color="#2E3DA1",min_color="#484B64")
                        ring_color.setAlphaF(alpha)
                    
                    painter.setPen(QPen(ring_color, pen_width))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(self.control_points[i], radius, radius)
                    
                    # 为影响力最大的点增加小同心圆
                    if i == max_influence_idx:
                        small_radius = radius * 1.6  # 小圆半径为外径的 50%
                        painter.setPen(QPen(ring_color, 3))  # 固定描边粗细为 2
                        painter.drawEllipse(self.control_points[i], small_radius, small_radius)

                    # 筛选 normalized_influence > 0.5 的锚点
                    if normalized_influence > 0.4:
                        anchor_data.append({
                            'index': i,
                            'point': self.control_points[i],
                            'radius': radius,
                            'color': ring_color,
                            'alpha': alpha
                        })
                
                # 绘制相邻锚点的连线
                if len(anchor_data) > 1:
                    for j in range(len(anchor_data) - 1):
                        point1 = anchor_data[j]['point']
                        point2 = anchor_data[j + 1]['point']
                        color1 = anchor_data[j]['color']
                        color2 = anchor_data[j + 1]['color']
                        radius1 = anchor_data[j]['radius']
                        radius2 = anchor_data[j + 1]['radius']
                        alpha1 = anchor_data[j]['alpha']
                        alpha2 = anchor_data[j + 1]['alpha']

                        # 计算平均颜色
                        avg_color = QColor(
                            (color1.red() + color2.red()) // 2,
                            (color1.green() + color2.green()) // 2,
                            (color1.blue() + color2.blue()) // 2
                        )
                        avg_color.setAlphaF((alpha1 + alpha2) / 2)  # 平均透明度
                        
                        # 计算平均粗细
                        avg_thickness = (radius1 + radius2) / 6  # 半径平均值的 1/4
                        
                        # 设置虚线样式
                        painter.setPen(QPen(avg_color, avg_thickness, Qt.DashLine))
                        painter.drawLine(point1, point2)

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

        self.rect_height_large = rect_height_large

        # 计算大矩形的左上角坐标
        rect_x_large = center_x - rect_width_large // 2
        rect_y_large = center_y - rect_height_large // 2

        # **绘制大矩形 (虚线)**
        rect_color = QColor(64, 64, 69)  
        rect_color.setAlpha(170)  # 半透明（50% 透明度）
        pen = QPen(rect_color, 2) # 描边宽度为 2
        pen.setStyle(Qt.DashLine) # 设置为虚线风格 修改点: 设置线条风格为虚线
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
        rect_color_small.setAlpha(170)  # 半透明，透明度与大矩形相同
        pen_small = QPen(rect_color_small, 2) # 描边宽度为 2，与大矩形相同
        pen_small.setStyle(Qt.SolidLine) # 设置为实线风格 确保小矩形是实线
        painter.setPen(pen_small)
        painter.setBrush(Qt.NoBrush)  # 无填充
        painter.drawRect(rect_x_small, rect_y_small, rect_width_small, rect_height_small)

        # 绘制描边和圆环（位于控制点下方）
        if self.cached_curve_points:
            outline_path = QPainterPath()
            outline_path.moveTo(self.cached_curve_points[0])
            for point in self.cached_curve_points[1:]:
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
        for i, point in enumerate(self.control_points):
            painter.drawPoint(point)
            if i == self.pre_selected_point_index:
                painter.save()  # 保存当前画笔状态
                # 删除预览时预选圆圈为红色，添加预览时为黄色
                ring_color = QColor("#FF0000") if self.is_alt_pressed else QColor("#FFFF00")
                pre_select_ring_pen = QPen(ring_color, 3) # 线宽为 3
                painter.setPen(pre_select_ring_pen)
                painter.setBrush(Qt.NoBrush) # 空心圆环
                ring_inner_radius = 4 # 内径为 4
                ring_outer_radius = 8 # 外径为 8
                painter.drawEllipse(point, ring_outer_radius, ring_outer_radius) # 绘制外圆
                painter.drawEllipse(point, ring_inner_radius, ring_inner_radius) # 绘制内圆 (覆盖中心区域，形成空心)
                painter.restore()  # 恢复画笔状态

        # 绘制控制线
        painter.setOpacity(0.1 if self.is_alt_pressed or self.is_ctrl_pressed or self.is_right_button_pressed or self.pre_selected_point_index is not None else 0.6)
        painter.setPen(QPen(QColor("#FFFFFF"), 1, Qt.DashLine))
        for i in range(len(self.control_points) - 1):
            painter.drawLine(self.control_points[i], self.control_points[i + 1])
        painter.setOpacity(1.0) # 恢复透明度

        # 绘制全局贝塞尔曲线（蓝色实线）
        if self.cached_curve_points:
            path = QPainterPath()
            path.moveTo(self.cached_curve_points[0])
            for point in self.cached_curve_points[1:]:
                path.lineTo(point)
            painter.setPen(QPen(QColor("#0000FF"), 2))
            painter.drawPath(path)

        # 绘制高亮显示的控制线段
        if self.pre_selected_point_index is not None and len(self.control_points) > 1:  # 检查是否有预选锚点且控制点足够
            pre_selected_idx = self.pre_selected_point_index
            highlight_color = QColor("#FF1111" if self.is_alt_pressed else "#ffffff")  # 高亮线段颜色 (相邻线段)
            highlight_color.setAlphaF(1.0)       # 完全不透明
            secondary_color = QColor("#FF3333" if self.is_alt_pressed else "#ffffff")  # 次高亮线段颜色 (前第二和后第二线段)
            secondary_color.setAlphaF(0.5)       # 较低透明度

            # 绘制相邻的前一条线段 (如果存在)
            if pre_selected_idx > 0:
                painter.setPen(QPen(highlight_color, 2, Qt.DashLine))  # 高亮粗虚线
                start_point_prev = self.control_points[pre_selected_idx - 1]
                end_point_prev = self.control_points[pre_selected_idx]
                painter.drawLine(start_point_prev, end_point_prev)

            # 绘制相邻的后一条线段 (如果存在)
            if pre_selected_idx < len(self.control_points) - 1:
                painter.setPen(QPen(highlight_color, 2, Qt.DashLine))  # 高亮粗虚线
                start_point_next = self.control_points[pre_selected_idx]
                end_point_next = self.control_points[pre_selected_idx + 1]
                painter.drawLine(start_point_next, end_point_next)

            # 绘制前第二条线段 (如果存在)
            if pre_selected_idx > 1:
                painter.setPen(QPen(secondary_color, 2, Qt.DashLine))  # 次高亮细虚线
                start_point_prev_second = self.control_points[pre_selected_idx - 2]
                end_point_prev_second = self.control_points[pre_selected_idx - 1]
                painter.drawLine(start_point_prev_second, end_point_prev_second)

            # 绘制后第二条线段 (如果存在)
            if pre_selected_idx < len(self.control_points) - 2:
                painter.setPen(QPen(secondary_color, 2, Qt.DashLine))  # 次高亮细虚线
                start_point_next_second = self.control_points[pre_selected_idx + 1]
                end_point_next_second = self.control_points[pre_selected_idx + 2]
                painter.drawLine(start_point_next_second, end_point_next_second)

        if self.is_visualization_enabled: #  <--  新增：总开关，控制可视化效果是否绘制
            if not self.is_alt_pressed and not self.is_ctrl_pressed:# 仅在未按 Alt 键时绘制影响力权重染色
                # 绘制影响力权重染色
                painter.setOpacity(0.1 if self.is_right_button_pressed else 0.5) # 设置染色层的整体透明度
                self.draw_influence_weights(painter)
                painter.setOpacity(1.0) # 恢复透明度

        self.draw_ctrl_highlight(painter) # 调用 Ctrl 高亮绘制函数

        if self.highlighted_segment_index is not None and self.highlighted_segment_index + 1 < len(self.control_points): # 检查是否有需要高亮显示的线段
            highlighted_index = self.highlighted_segment_index
            adjacent_color = QColor("#FEFD02")  # 相邻线段颜色
            adjacent_color.setAlphaF(0.7)

            # 绘制相邻的前一条线段 (如果存在)
            if highlighted_index > 0:
                painter.setPen(QPen(adjacent_color, 2, Qt.DashLine)) 
                start_point_adjacent_prev = self.control_points[highlighted_index - 1]
                end_point_adjacent_prev = self.control_points[highlighted_index]
                painter.drawLine(start_point_adjacent_prev, end_point_adjacent_prev)

            # 绘制相邻的后一条线段 (如果存在)
            if highlighted_index < len(self.control_points) - 2: # 注意索引范围
                painter.setPen(QPen(adjacent_color, 2, Qt.DashLine)) 
                start_point_adjacent_next = self.control_points[highlighted_index + 1]
                end_point_adjacent_next = self.control_points[highlighted_index + 2]
                painter.drawLine(start_point_adjacent_next, end_point_adjacent_next)

        # --- 绘制预览效果 ---
        if self.is_preview_enabled:
            # 添加锚点时的预览点
            if self.preview_point is not None:
                # 根据插入位置选择颜色（Ctrl 添加起点/终点用绿色）
                if self.is_ctrl_pressed:
                    painter.setBrush(QBrush(QColor("#00FF00")))  # 绿色表示起点/终点
                else:
                    painter.setBrush(QBrush(QColor("#fefd02")))  # 黄色表示中间点
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(self.preview_point, 5, 5)

            # 绘制预览曲线（删除或添加时都显示）
            if self.preview_slider_points and self.is_visualization_enabled:
                painter.setBrush(Qt.NoBrush)
                max_offset = max(self.preview_offsets) if self.preview_offsets and any(o > 0 for o in self.preview_offsets) else 1.0
                
                for i in range(1, len(self.preview_slider_points)):
                    offset = self.preview_offsets[i] if i < len(self.preview_offsets) else self.preview_offsets[-1]
                    # 删除预览时 max_color 为 #FF0000 添加预览时为 #fefd02
                    max_color = "#FF0000" if self.preview_point is None else "#fefd02"
                    color = self.interpolate_color(offset, max_offset, max_color=max_color,)
                    pen = QPen(color)
                    pen.setWidthF(3.5)
                    pen.setDashPattern([2, 2])
                    painter.setPen(pen)
                    painter.drawLine(self.preview_slider_points[i - 1], self.preview_slider_points[i])
                    
            if self.preview_segment_index != -1:
                pen = QPen(QColor("#00FF00" if self.is_ctrl_pressed else "#fefd02"))
                pen.setStyle(Qt.DashLine)
                pen.setWidth(pen.width() * 2)
                painter.setPen(pen)
                if self.is_ctrl_pressed:
                    # 起点或终点连接线
                    if self.preview_segment_index == 0:
                        p1 = self.control_points[0]
                    else:
                        p1 = self.control_points[-1]
                else:
                    p1 = self.control_points[self.preview_segment_index - 1]
                    p2 = self.control_points[self.preview_segment_index]
                    painter.drawLine(self.preview_point, p2)
                painter.drawLine(self.preview_point, p1)

        painter.end()

    def draw_influence_weights(self, painter):
        """绘制影响力权重染色（黄色圆圈）"""
        if self.pre_selected_point_index is None:
            return

        influence_color = QColor("#FFFF00")
        dragged_point_index = self.pre_selected_point_index
        curve_order = len(self.control_points) - 1

        # 计算每段影响力权重
        segment_influence_weights = []
        for t in range(0, self.curve_segments):
            t_start = t / self.curve_segments
            t_end = (t + 1) / self.curve_segments
            t_mid = (t_start + t_end) / 2

            if dragged_point_index == 0:
                t_value_for_weight = t_start
            elif dragged_point_index == len(self.control_points) - 1:
                t_value_for_weight = t_end
            else:
                t_value_for_weight = t_mid

            influence_weight = self.bernstein_basis_polynomial(curve_order, dragged_point_index, t_value_for_weight)
            segment_influence_weights.append({'index': t, 'weight': influence_weight})

        max_influence_weight = max(segment['weight'] for segment in segment_influence_weights) if segment_influence_weights else 0

        # 绘制染色圆圈
        for t in range(0, self.curve_segments):
            t_start = t / self.curve_segments
            t_end = (t + 1) / self.curve_segments
            t_mid = (t_start + t_end) / 2

            influence_weight = segment_influence_weights[t]['weight']
            normalized_influence_weight = influence_weight / max_influence_weight if max_influence_weight > 0 else 0

            # 透明度映射
            max_alpha = 0.8
            min_alpha = 0
            alpha = min_alpha + (max_alpha - min_alpha) * (normalized_influence_weight ** 2)
            influence_color.setAlphaF(alpha)

            # 半径映射
            max_radius = self.outline_width * 0.25
            min_radius = 0
            radius = min_radius + (max_radius - min_radius) * (normalized_influence_weight ** 2)

            painter.setBrush(QBrush(influence_color))
            painter.setPen(Qt.NoPen)
            point_mid = self.calculate_bezier_point(t_mid, self.control_points)
            painter.drawEllipse(point_mid, radius, radius)

    def get_insert_position(self, pos):
        """根据鼠标位置判断插入起点还是终点，返回插入索引"""
        if len(self.control_points) < 2:
            return None  # 不足两个点时不插入
        start_point = self.control_points[0]
        end_point = self.control_points[-1]
        dist_to_start = self.distance(pos, start_point)
        dist_to_end = self.distance(pos, end_point)
        return 0 if dist_to_start < dist_to_end else len(self.control_points)

    def update_preview_slider(self, event):
        """更新预览滑条效果，根据 Alt + Ctrl 或 Alt 键触发不同功能"""
        if len(self.control_points) < 2:
            self.is_preview_enabled = False
            self.preview_point = None
            self.preview_slider_points = None
            self.preview_offsets = None
            self.preview_segment_index = -1
            self.highlighted_segment_index = None
            return

        # 优先检查 Alt + Ctrl 组合：添加头尾锚点
        if self.is_alt_pressed and self.is_ctrl_pressed:
            # Alt + Ctrl：添加起点或终点锚点
            insert_index = self.get_insert_position(event.pos())
            if insert_index is not None:
                if insert_index == 0:
                    self.preview_segment_index = 0
                else:
                    self.preview_segment_index = len(self.control_points) - 1

                self.preview_point = event.pos()
                self.is_preview_enabled = True
                self.highlighted_segment_index = None

                # 计算预览曲线
                preview_control_points = self.control_points[:]
                preview_control_points.insert(insert_index, self.preview_point)
                self.preview_slider_points = []
                self.preview_offsets = []
                for t in range(0, self.curve_segments + 1):
                    t_normalized = t / self.curve_segments
                    point = self.calculate_bezier_point(t_normalized, preview_control_points)
                    self.preview_slider_points.append(point)
                    if self.cached_curve_points and len(self.cached_curve_points) > t:
                        orig_point = self.cached_curve_points[t]
                        offset = self.distance(point, orig_point)
                    else:
                        offset = 0
                    self.preview_offsets.append(offset)
            else:
                self.is_preview_enabled = False
                self.preview_point = None
                self.preview_slider_points = None
                self.preview_offsets = None
                self.preview_segment_index = -1
                self.highlighted_segment_index = None

        # 仅 Alt 键：添加中间锚点或删除预选锚点
        elif self.is_alt_pressed:
            min_distance = float('inf')
            insert_segment_index = -1
            distance_threshold = self.rect_height_large * 0.11 if self.rect_height_large > 0 else 50
            
            for i in range(len(self.control_points) - 1):
                start_point = self.control_points[i]
                end_point = self.control_points[i + 1]
                distance = self.point_to_line_distance(event.pos(), start_point, end_point)
                if distance < min_distance:
                    min_distance = distance
                    insert_segment_index = i

            if self.pre_selected_point_index is not None and len(self.control_points) > 2:
                # 预览删除预选锚点
                self.highlighted_segment_index = None
                self.preview_point = None
                self.is_preview_enabled = True
                self.preview_segment_index = -1
                
                preview_control_points = self.control_points[:]
                preview_control_points.pop(self.pre_selected_point_index)
                
                self.preview_slider_points = []
                self.preview_offsets = []
                for t in range(0, self.curve_segments + 1):
                    t_normalized = t / self.curve_segments
                    point = self.calculate_bezier_point(t_normalized, preview_control_points)
                    self.preview_slider_points.append(point)
                    if self.cached_curve_points and len(self.cached_curve_points) > t:
                        orig_point = self.cached_curve_points[t]
                        offset = self.distance(point, orig_point)
                    else:
                        offset = 0
                    self.preview_offsets.append(offset)
            elif insert_segment_index is not None and min_distance < distance_threshold and insert_segment_index + 1 < len(self.control_points):
                # 预览添加中间锚点
                self.highlighted_segment_index = insert_segment_index
                self.preview_point = event.pos()
                self.is_preview_enabled = True
                self.preview_segment_index = insert_segment_index + 1
                
                preview_control_points = self.control_points[:]
                preview_control_points.insert(self.preview_segment_index, self.preview_point)
                self.preview_slider_points = []
                self.preview_offsets = []
                for t in range(0, self.curve_segments + 1):
                    t_normalized = t / self.curve_segments
                    point = self.calculate_bezier_point(t_normalized, preview_control_points)
                    self.preview_slider_points.append(point)
                    if self.cached_curve_points and len(self.cached_curve_points) > t:
                        orig_point = self.cached_curve_points[t]
                        offset = self.distance(point, orig_point)
                    else:
                        offset = 0
                    self.preview_offsets.append(offset)
            else:
                self.highlighted_segment_index = None
                self.preview_point = None
                self.is_preview_enabled = False
                self.preview_segment_index = -1
                self.preview_slider_points = None
                self.preview_offsets = None

        else:
            # 无修饰键时清除预览
            self.highlighted_segment_index = None
            self.preview_point = None
            self.is_preview_enabled = False
            self.preview_segment_index = -1
            self.preview_slider_points = None
            self.preview_offsets = None

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
        import copy  # 确保导入 copy 模块
        if len(self.history) >= self.max_history_size:
            self.history.pop(0)
        state_to_save = copy.deepcopy(self.control_points)  # 使用深拷贝避免引用问题
        self.history.append((state_to_save,))              # 保存为元组
        self.future.clear()
        
        self.backup_counter += 1 # 更新计数器并检查是否备份
        if self.backup_counter >= self.backup_threshold:
            self.auto_backup()
            self.backup_counter = 0  # 重置计数器

    def auto_backup(self):
        """自动备份当前状态"""
        backup_data = {
            'control_points': self.control_points,
            'history': self.history,
            'future': self.future
        }
        try:
            with open(self.backup_file, 'wb') as f:
                pickle.dump(backup_data, f)
            # 可选：print(f"Auto backup saved to {self.backup_file}")
        except Exception as e:
            print(f"Failed to save backup: {e}")

    def restore_backup_on_startup(self):
        """启动时检查并恢复备份"""
        if os.path.exists(self.backup_file):
            reply = QMessageBox.question(
                self, self.msg_title_backup, self.msg_restore_backup,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    with open(self.backup_file, 'rb') as f:
                        backup_data = pickle.load(f)
                    self.control_points = backup_data.get('control_points', [])
                    self.history = backup_data.get('history', [])
                    self.future = backup_data.get('future', [])
                    self.update_curve_cache()
                    self.update()
                except Exception as e:
                    QMessageBox.warning(self, self.msg_title_backup2, self.msg_restore_backup2.format(error=str(e)))

    def closeEvent(self, event):
        """窗口关闭时提示保存并清理备份"""
        reply = QMessageBox.question(
            self, self.msg_close_title, self.msg_close_prompt,
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            # 保存当前工作（调用导出功能）
            if len(self.control_points) >= 2:
                file_name, _ = QFileDialog.getSaveFileName(self, "Save Control Points", "", "Text Files (*.txt)")
                if file_name:
                    self.export_points()  # 假设 export_points 已处理保存逻辑
            # 清理备份并退出
            if os.path.exists(self.backup_file):
                try:
                    os.remove(self.backup_file)
                except Exception as e:
                    print(f"Failed to remove backup: {e}")
            event.accept()
        elif reply == QMessageBox.No:
            # 不保存，直接清理备份并退出
            if os.path.exists(self.backup_file):
                try:
                    os.remove(self.backup_file)
                except Exception as e:
                    print(f"Failed to remove backup: {e}")
            event.accept()
        else:  # Cancel
            event.ignore()  # 取消关闭

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
        self.update_curve_cache()  # 刷新缓存
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

        self.update_curve_cache()  # 刷新缓存
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

    def save_control_points_to_file(self, file_name):
        """将控制点保存到指定文件"""
        if len(self.control_points) < 2:
            return False  # 少于 2 个点时不保存，返回 False 表示失败

        try:
            with open(file_name, "w") as file:
                # 计算窗口中心和矩形边界
                center_x = self.width() // 2
                center_y = self.height() // 2
                rect_width = int(self.width() * self.rect_scale)
                rect_height = int(rect_width * 3 / 4)
                rect_x = center_x - rect_width // 2
                rect_y = center_y - rect_height // 2
                rect_bottom_left_current_x = rect_x
                rect_bottom_left_current_y = rect_y + rect_height
                rect_top_right_current_x = rect_x + rect_width
                rect_top_right_current_y = rect_y

                # 保存第一个控制点
                first_point = self.control_points[0]
                remapped_first_point = self.remap_coordinates(
                    first_point,
                    rect_bottom_left_current_x, rect_bottom_left_current_y,
                    rect_top_right_current_x, rect_top_right_current_y
                )
                file.write(
                    f"{int(remapped_first_point.x())},{int(remapped_first_point.y())},1000,2,0,B"
                )

                # 保存后续控制点
                for point in self.control_points[1:]:
                    remapped_point = self.remap_coordinates(
                        point,
                        rect_bottom_left_current_x, rect_bottom_left_current_y,
                        rect_top_right_current_x, rect_top_right_current_y
                    )
                    file.write(f"|{int(remapped_point.x())}:{int(remapped_point.y())}")

                # 写入滑条参数
                file.write(",1,100\n")
            return True  # 保存成功返回 True
        except Exception as e:
            print(f"Save control points failed: {e}")  # 可选错误日志
            return False  # 保存失败返回 False

    def quick_save(self):
        """快捷键 Ctrl + S 快速保存到程序目录"""
        # 生成文件名
        current_time = datetime.datetime.now().strftime("curve_%Y_%m_%d_%H_%M_%S")
        file_name = os.path.join(os.getcwd(), f"{current_time}.txt")

        # 保存控制点
        if self.save_control_points_to_file(file_name):
            # 显示保存成功提示并启动渐隐动画
            label_width = self.save_label.sizeHint().width()
            label_height = self.save_label.sizeHint().height()
            self.save_label.move((self.width() - label_width) // 2, (self.height() - label_height) // 2)
            self.save_label.setVisible(True)
            self.fade_out_save_label()

    def fade_out_save_label(self):
        """渐隐消失保存提示"""
        self.fade_animation = QPropertyAnimation(self.save_label, b"windowOpacity")
        self.fade_animation.setDuration(1000)  # 1 秒动画
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(lambda: self.save_label.setVisible(False))
        self.fade_animation.start()

    def import_slider(self):
        """从文件导入滑条路径"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Slider File", "", "Text Files (*.txt)")
        if file_name:
            try:
                with open(file_name, "r") as file:
                    content = file.read().strip()
                    # 示例格式：x,y,time,type,curve_type,B|...
                    parts = content.split(",")
                    if len(parts) >= 6 and parts[5].startswith("B|"):
                        # 计算窗口中心 (从 export_points 函数中复制 - 确保 rect_bottom_left_current_x 等变量被定义)
                        center_x = self.width() // 2
                        center_y = self.height() // 2
                        rect_width = int(self.width() * self.rect_scale)
                        rect_height = int(rect_width * 3 / 4)
                        rect_x = center_x - rect_width // 2
                        rect_y = center_y - rect_height // 2
                        rect_bottom_left_current_x = rect_x
                        rect_bottom_left_current_y = rect_y + rect_height
                        rect_top_right_current_x = rect_x + rect_width
                        rect_top_right_current_y = rect_y

                        # 第一个滑条点
                        start_x = int(parts[0])
                        start_y = int(parts[1])

                        # 对第一个点也应用 remap_coordinates 反向映射  !!!
                        remapped_first_point = self.remap_coordinates(
                            QPoint(start_x, start_y),
                            rect_bottom_left_current_x, rect_bottom_left_current_y,
                            rect_top_right_current_x, rect_top_right_current_y,
                            reverse=True
                        )
                        self.control_points = [remapped_first_point] # 使用反向映射后的第一个点

                        # 解析剩余的滑条点
                        slider_points = parts[5][2:].split("|")  # 去掉 "B|"
                        remapped_slider_points = [] # 用于存储反向映射后的滑条点
                        for point in slider_points:
                            x, y = point.split(":")
                            new_point_remapped = self.remap_coordinates( # 调用 remap_coordinates 进行反向映射
                                QPoint(int(x), int(y)),
                                rect_bottom_left_current_x, rect_bottom_left_current_y,
                                rect_top_right_current_x, rect_top_right_current_y,
                                reverse=True # 传入 reverse=True 参数，执行反向映射
                            )
                            remapped_slider_points.append(new_point_remapped) # 将反向映射后的点添加到 remapped_slider_points 列表

                        self.control_points.extend(remapped_slider_points) # 将反向映射后的滑条点列表添加到 self.control_points
                        self.save_state()
                        self.update_curve_cache()  # 刷新缓存
                        self.update()
                        
                        # 成功提示
                        # QMessageBox.information(self, self.msg_title_prompt, self.msg_slider_import_success.format(file_name=file_name))
                    else:
                        raise ValueError("Invalid slider file format")
            except Exception as e:
                # 失败提示
                QMessageBox.warning(self, self.msg_title_prompt, self.msg_slider_import_failed.format(error=str(e)))
        else:
            # 未选择文件时不提示
            pass

    def export_points(self):
        """导出控制点，并提示结果"""
        if len(self.control_points) < 2:
            QMessageBox.warning(self, self.msg_title_prompt, self.msg_points_export_min)
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save Control Points", "", "Text Files (*.txt)")
        if file_name:
            if self.save_control_points_to_file(file_name):
                QMessageBox.information(self, self.msg_title_prompt, self.msg_points_export_success.format(file_name=file_name))

    def remap_coordinates(self, point, rect_bottom_left_x, rect_bottom_left_y, rect_top_right_x, rect_top_right_y, reverse=False):
        """
        将点坐标从一个坐标系重新映射到另一个坐标系.
        支持正向映射 (当前坐标系 -> 新坐标系) 和反向映射 (新坐标系 -> 当前坐标系).

        Args:
            point: 要重新映射的 QPoint 对象.
            rect_bottom_left_x: 红色矩形左下角在**当前坐标系**中的 X 坐标.
            rect_bottom_left_y: 红色矩形左下角在**当前坐标系**中的 Y 坐标.
            rect_top_right_x: 红色矩形右上角在**当前坐标系**中的 X 坐标.
            rect_top_right_y: 红色矩形右上角在**当前坐标系**中的 Y 坐标.
            reverse: 如果为 True, 执行**反向映射** (新坐标系 -> 当前坐标系). 默认为 False (正向映射).

        Returns:
            重新映射后的 QPoint 对象.
        """
        current_x = point.x()
        current_y = point.y()

        # 新的坐标系的范围 (已更新)
        new_x_min = -65
        new_x_max = 575
        new_y_min = -56
        new_y_max = 424

        # 当前坐标系中红色矩形的宽度和高度
        rect_width_current = rect_top_right_x - rect_bottom_left_x
        rect_height_current = rect_bottom_left_y - rect_top_right_y

        if rect_width_current == 0 or rect_height_current == 0:
            return QPoint(0, 0)  # 避免除以零

        # 计算 X 和 Y 坐标的比例和偏移
        scale_x = (new_x_max - new_x_min) / rect_width_current
        scale_y = (new_y_max - new_y_min) / rect_height_current
        offset_x = new_x_min - rect_bottom_left_x * scale_x
        offset_y = new_y_max - rect_bottom_left_y * scale_y

        if reverse: # 反向映射 (新坐标系 -> 当前坐标系)
            # 反向计算比例和偏移 (实际上比例不变，只需要反向应用偏移)
            reverse_scale_x = 1.0 / scale_x if scale_x != 0 else 0 # 避免除以零
            reverse_scale_y = 1.0 / scale_y if scale_y != 0 else 0 # 避免除以零
            reverse_offset_x = -offset_x / scale_x if scale_x != 0 else 0
            reverse_offset_y = -offset_y / scale_y if scale_y != 0 else 0


            new_x = reverse_scale_x * (current_x - new_x_min)  + rect_bottom_left_x # 反向映射 X 坐标
            new_y = reverse_scale_y * (current_y - new_y_max) + rect_bottom_left_y # 反向映射 Y 坐标 (注意 Y 轴反转)


        else: # 正向映射 (当前坐标系 -> 新坐标系) - 默认
            new_x = scale_x * current_x + offset_x # 正向映射 X 坐标
            new_y = scale_y * current_y + offset_y # 正向映射 Y 坐标

        return QPoint(int(new_x), int(new_y))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BezierCurveEditor()
    window.show()
    sys.exit(app.exec_())