from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QSlider, QLabel, QMessageBox, QShortcut
)

# 自定义按钮类，用于处理鼠标悬停事件
class HoverButton(QPushButton):
    def __init__(self, parent=None):
        super(HoverButton, self).__init__(parent)
        self.detail_text = ""  # 按钮的详细说明文本
        self.parent_widget = None  # 父窗口引用
        
    def enterEvent(self, event):
        """鼠标进入按钮区域时触发"""
        if hasattr(self, 'parent_widget') and self.parent_widget and hasattr(self, 'detail_text'):
            # 只在帮助标签可见时更新内容
            if hasattr(self.parent_widget, 'help_visible') and self.parent_widget.help_visible:
                # 保存当前帮助文本，以便在鼠标离开时恢复
                if not hasattr(self.parent_widget, 'current_help_text'):
                    if hasattr(self.parent_widget, 'help_label') and self.parent_widget.help_label.isVisible():
                        self.parent_widget.current_help_text = self.parent_widget.help_label.text()
                
                # 更新帮助标签显示按钮的详细说明
                if hasattr(self.parent_widget, 'help_label'):
                    self.parent_widget.help_label.setText(self.detail_text)
                    self.parent_widget.help_label.adjustSize()
                    self.parent_widget.update_help_position()
        
        super(HoverButton, self).enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开按钮区域时触发"""
        if hasattr(self, 'parent_widget') and self.parent_widget:
            # 只在帮助标签可见时恢复文本
            if hasattr(self.parent_widget, 'help_visible') and self.parent_widget.help_visible:
                # 恢复原始帮助文本
                if hasattr(self.parent_widget, 'current_help_text') and hasattr(self.parent_widget, 'help_label'):
                    self.parent_widget.help_label.setText(self.parent_widget.help_label_text_full)
                    self.parent_widget.help_label.adjustSize()
                    self.parent_widget.update_help_position()
        
        super(HoverButton, self).leaveEvent(event)
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QPixmap, QBrush, QVector2D, QIcon
from PyQt5.QtCore import Qt, QPoint, QLocale, QLineF, QPropertyAnimation, QSize
import sys
import math
import pickle
import os
import clr
import datetime
import json

# 获取 DLL 绝对路径
dll_path = os.path.abspath("EditorReader.dll")
# 确保 DLL 存在
if not os.path.exists(dll_path):
    raise FileNotFoundError(f"找不到 DLL: {dll_path}")
sys.path.append(dll_path)
clr.AddReference("EditorReader")
# 导入 EditorReader 类
from Editor_Reader import EditorReader
# 创建 EditorReader 实例
reader = EditorReader()

class BezierCurveEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True) 
        self.setWindowTitle("Bezier Curve Editor for osu!")
        self.setGeometry(100, 100, 1600, 900)
        self.control_points = []  # 存储控制点
        self.red_anchors = set()  # 存储红色锚点的索引
        self.history = []  # 操作历史
        self.future = []  # 撤销后的操作
        self.max_history_size = 20  # 设置最大历史记录长度
        self.dragging_point = None  # 当前拖动的控制点索引
        self.image = None  # 导入的图片
        self.image_scale = 1.0  # 图片缩放比例
        self.image_opacity = 0.7  # 图片透明度
        self.image_sliders_visible = False  # 控制图片相关滑块的可见性
        self.curve_segments = 100  # 曲线绘制段数
        self.config_file = "config.json"  # 配置文件路径
        self.osu_songs_path = self.load_config()  # 加载配置
        self.allow_save2osu = False

        self.dragging_curve_only = False  # 是否正在单独拖动曲线 (新增)
        self.dragging_curve_and_image = False  # 是否正在拖动曲线和图片 (新增)
        self.is_ctrl_right_dragging = False  # 是否正在拖动曲线的局部
        self.is_ctrl_dragging_deformation = False
        self.last_mouse_pos = QPoint()  # 上次鼠标位置
        self.drag_start_pos = None
        self.locked_closest_point = None
        self.locked_t = None # 保存拖动开始时的 t 值

        self.curve_scale = 1.0  # 曲线整体缩放比例
        self.outline_width = 4  # 描边粗细 (初始值，之后会被计算的值覆盖)
        self.outline_opacity = 0.85  # 描边透明度
        self.rect_scale = 0.75  # 矩形默认大小为窗口的 65%
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
        self.is_left_button_pressed = False
        self.cached_curve_points = None  # 初始化缓存为空
        self.update_curve_cache()  # 初始调用，计算缓存
        self.initial_slider_length = 0  # 初始滑条长度
        self.current_slider_length = 0  # 当前滑条长度
        self.get_button_texts()

        self.is_ctrl_pressed = False  # 跟踪 Ctrl 键状态
        self.is_shift_pressed = False  # 跟踪 Shift 键状态
        self.is_alt_pressed = False    # 跟踪 Alt 键状态
        self.closest_curve_point = None  # 最近曲线点
        self.anchor_influences = []  # 锚点影响力列表

        self.rotation_pivot_point = None  # 旋转基准点 (QPoint)
        self.has_rotation_pivot = False   # 是否已设置旋转基准点 (bool)
        self.is_rotating_curve = False    # 是否正在旋转曲线 (bool)
        self.rotation_start_pos = None    # 旋转开始时的鼠标位置 (QPoint)

        # 初始化自动备份
        self.backup_file = "bezier_Curve_backup.pkl"
        self.backup_counter = 0  # 历史记录更新计数器
        self.backup_threshold = 5  # 每 5 次历史记录更新触发备份
        self.restore_backup_on_startup() # 检查并恢复备份
        
        # 检查osu_songs_path是否有效
        self.is_osu_path_valid = self.check_osu_path_valid()

        # 绑定 Ctrl + S 快捷键
        self.save_shortcut = QShortcut(Qt.Key_S | Qt.ControlModifier, self)
        self.save_shortcut.activated.connect(self.quick_save)

        self.init_ui()

        # 在 init_ui() 之后，通过 sliders 字典访问 circle_size 滑块
        initial_circle_size_value = self.sliders["circle_size"].value() # 获取 Circle size 滑块的初始值
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
            self.button_text_show_help = "帮助"
            self.button_text_load_selected_slider = "加载选中滑条"
            self.button_text_export_to_osu = "导出到osu!"
            self.button_text_osu_path = "设置"
            self.button_text_visualizations = "可视化效果"
            self.button_text_sliders = "参数滑块"
            self.button_text_clear_canvas = "清空画布"
            self.button_text_redo = "重做"
            self.button_text_undo = "撤销"

            self.delete_control_point_msg = "锚点数量已达最小值（2 个），无法继续删除！"
            self.msg_slider_import_success = "滑条已成功从 {file_name} 导入！"
            self.msg_slider_import_failed = "导入滑条失败：{error}"
            self.msg_points_export_min = "至少需要两个控制点才能导出！"
            self.msg_points_export_success = "控制点已成功导出到 {file_name}！"
            self.msg_title_prompt = "提示"
            self.msg_title_success = "成功" 
            self.msg_title_error = "错误" 
            self.msg_restore_backup = "检测到上次未保存的备份数据，是否恢复？"
            self.msg_title_backup = "恢复备份"
            self.msg_restore_backup2 = "无法恢复备份数据：{error}"
            self.msg_title_backup2 = "恢复失败"
            self.msg_close_prompt = "是否保存当前工作并退出？"
            self.msg_close_title = "退出程序"
            self.msg_quick_save_success = "快速保存成功"
            self.msg_success_export_osu = "滑条数据已成功写入 .osu 文件！"
            self.msg_error_save_slider = "保存滑条数据失败！<br>如需导出滑条到osu!，需要先从osu!导入滑条。<br>错误代码：{error}，"
            self.msg_error_osu_file_not_found = "找不到谱面文件: {osu_file_path}"
            self.msg_error_import_first_osu = "如需导出滑条到osu!，需要先从osu!导入滑条！"
            self.msg_error_load_selected_slider = "加载选中滑条失败：{error}"
            self.msg_success_load_selected_slider = "已成功加载选中的滑条！"
            self.msg_error_not_slider_or_unsupported = "选中的对象不是滑条或非受支持的类型！"
            self.msg_error_no_slider_selected = "未检测到选中的滑条！"
            self.msg_set_osu_path = "请先设置Songs文件夹路径！"
            self.msg_set_osu_path_success = "osu! Songs文件夹路径设置成功！"
            self.msg_set_osu_path_title = "设置osu!歌曲文件夹"
            self.msg_set_osu_path_prompt = "是否选择osu!歌曲文件夹路径？"
            self.msg_set_osu_path_dialog = "选择osu!/Songs文件夹"
            self.msg_prompt_restart_program = "确认要清空画布吗？"
            self.msg_slider_length_ratio = "滑条长度比值"


            self.help_label_text_full = """
                <b>基础操作：</b><br>
                ▪ <span style="color:#FF8A9B">左键</span> 新增锚点 / 拖动锚点<br>
                ▪ <span style="color:#FF8A9B">滚轮</span> 缩放/平移<br>
                ▪ <span style="color:#FF8A9B">右键</span> 曲线旋转<br>
                &nbsp;&nbsp;└（点击锚点时）切换红白锚点<br>
                <br>

                <b>组合键操作：</b><br>
                ▪ <span style="color:#FF8A9B">ALT</span> <span style="color:#FF8A9B">左键</span> 增删中间锚点<br>
                &nbsp;&nbsp;└ <span style="color:#FF8A9B">+ CTRL</span> 增加头尾锚点<br>
                ▪ <span style="color:#FF8A9B">ALT</span> <span style="color:#FF8A9B">右键</span> 设置旋转基准点<br>
                ▪ <span style="color:#FF8A9B">CTRL</span> <span style="color:#FF8A9B">中键</span> 拖动曲线和底图<br>
                ▪ <span style="color:#FF8A9B">CTRL</span> <span style="color:#FF8A9B">左键</span> 曲线变形<br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> <span style="color:#FF8A9B">左键</span><br>
                &nbsp;&nbsp;└（普通锚点）锁定方向拖动锚点<br>
                &nbsp;&nbsp;└（红锚点）相邻锚点投影至切线<br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> <span style="color:#FF8A9B">右键</span> 平衡化红锚点
                """
            self.help_label_text_ctrl = """
                <b>ctrl修饰键说明：</b><br>
                ▪ <span style="color:#FF8A9B">CTRL</span> <span style="color:#FF8A9B">中键</span> 拖动曲线和底图<br>
                ▪ <span style="color:#FF8A9B">CTRL</span> <span style="color:#FF8A9B">左键</span> 曲线变形<br>
                
                <b>文件操作：</b><br>
                ▪ <span style="color:#FF8A9B">CTRL+S</span> 快速保存<br>
                ▪ <span style="color:#FF8A9B">CTRL+Z</span> 撤销操作<br>
                ▪ <span style="color:#FF8A9B">CTRL+Y</span> 重做操作
                """
            self.help_label_text_shift = """
                <b>shift修饰键说明：</b><br>
                <span style="color:#FF8A9B">以下功能仅在存在红锚点时生效</span><br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> <span style="color:#FF8A9B">左键</span><br>
                &nbsp;&nbsp;└（普通锚点）锁定方向拖动锚点<br>
                &nbsp;&nbsp;└（红锚点）相邻锚点投影至切线<br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> <span style="color:#FF8A9B">右键</span> 平衡化红锚点
                """
            self.help_label_text_alt = """
                <b>alt修饰键说明：</b><br>
                ▪ <span style="color:#FF8A9B">ALT</span> <span style="color:#FF8A9B">左键</span> 增删中间锚点<br>
                &nbsp;&nbsp;└ <span style="color:#FF8A9B">+ CTRL</span> 增加头尾锚点<br>
                ▪ <span style="color:#FF8A9B">ALT</span> <span style="color:#FF8A9B">右键</span> 设置旋转基准点
                """

        else:
            self.button_text_export_control_points = "Exp to txt"
            self.button_text_import_image = "Imp Image"
            self.button_text_image_scale = "Image Scale"
            self.button_text_image_opacity = "Image Opacity"
            self.button_text_curve_segments = "Curve Segments"
            self.button_text_circle_size = "Circle Size"
            self.button_text_outline_opacity = "Slider Opacity"
            self.button_text_playfield_boundary = "Playfield Boundary"
            self.button_text_import_slider = "Imp from txt"
            self.button_text_show_help = "Help"
            self.button_text_load_selected_slider = "Imp from osu!"
            self.button_text_export_to_osu = "Exp to osu!"
            self.button_text_osu_path = "Set Path"
            self.button_text_visualizations = "Viz"
            self.button_text_sliders = "Parameters"
            self.button_text_clear_canvas = "Clear Canvas"
            self.button_text_redo = "Redo"
            self.button_text_undo = "Undo"

            self.delete_control_point_msg = "The number of anchor points has reached the minimum (2) and cannot be deleted further!"
            self.msg_slider_import_success = "Slider imported successfully from {file_name}!"
            self.msg_slider_import_failed = "Failed to import slider: {error}"
            self.msg_points_export_min = "At least two control points are required to export!"
            self.msg_points_export_success = "Control points exported successfully to {file_name}!"
            self.msg_title_prompt = "Prompt"
            self.msg_title_success = "Success"
            self.msg_title_error = "Error"
            
            self.msg_restore_backup = "Detected unsaved backup data from the last session. Do you want to restore it?"
            self.msg_title_backup = "Restore Backup"
            self.msg_restore_backup2 = "Unable to restore backup data: {error}"
            self.msg_title_backup2 = "Restore Failed"
            self.msg_close_prompt = "Do you want to save your current work and exit?"
            self.msg_close_title = "Exit Program"
            self.msg_quick_save_success = "Quick Save Successful"
            self.msg_success_export_osu = "Slider data successfully written to .osu file!"
            self.msg_error_save_slider = "Failed to save slider data!<br>To export slider to osu!, you need to import slider from osu! first.<br>Error code: {error},"
            self.msg_error_osu_file_not_found = "Cannot find beatmap file: {osu_file_path}"
            self.msg_error_import_first_osu = "To export slider to osu!, you need to import slider from osu! first!"
            self.msg_error_load_selected_slider = "Failed to load selected slider: {error}"
            self.msg_success_load_selected_slider = "Successfully loaded the selected slider!"
            self.msg_error_not_slider_or_unsupported = "The selected object is not a slider or an unsupported type!"
            self.msg_error_no_slider_selected = "No slider selected!"
            self.msg_set_osu_path = "Please set the Songs folder path!"
            self.msg_set_osu_path_success = "osu! Songs folder path set successfully!"
            self.msg_set_osu_path_title = "Set osu! Songs Folder"
            self.msg_set_osu_path_prompt = "Do you want to set the osu! Songs folder path?"
            self.msg_set_osu_path_dialog = "Select osu!/Songs folder"
            self.msg_prompt_restart_program = "Confirm to clear the canvas?"
            self.msg_slider_length_ratio = "Slider Length Ratio"

            self.help_label_text_full = """
                <b>Basic Operations:</b><br>
                ▪ <span style="color:#FF8A9B">Left Click</span> Add Anchor Point / Drag Anchor Point<br>
                ▪ <span style="color:#FF8A9B">Scroll Wheel</span> Zoom/Pan<br>
                ▪ <span style="color:#FF8A9B">Right Click</span> Rotate Curve<br>
                &nbsp;&nbsp;└ (When clicking an anchor point) Toggle Red/White Anchor Point<br>
                <br>

                <b>Combination Key Operations:</b><br>
                ▪ <span style="color:#FF8A9B">ALT</span> + <span style="color:#FF8A9B">Left Click</span> Add/Remove Middle Anchor Point<br>
                &nbsp;&nbsp;└ + <span style="color:#FF8A9B">CTRL</span> Add Head/Tail Anchor Point<br>
                ▪ <span style="color:#FF8A9B">ALT</span> + <span style="color:#FF8A9B">Right Click</span> Set Rotation Pivot<br>
                ▪ <span style="color:#FF8A9B">CTRL</span> + <span style="color:#FF8A9B">Middle Click</span> Drag Curve and Background<br>
                ▪ <span style="color:#FF8A9B">CTRL</span> + <span style="color:#FF8A9B">Left Click</span> Deform Curve<br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> + <span style="color:#FF8A9B">Left Click</span><br>
                &nbsp;&nbsp;└ (normal anchor point) Lock Direction to Drag Anchor Point<br>
                &nbsp;&nbsp;└ (red anchor point) Project Adjacent Anchor Points to Tangent<br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> + <span style="color:#FF8A9B">Right Click</span> Balance Anchor Points
                """
            self.help_label_text_ctrl = """
                <b>CTRL Modifier Key Explanation:</b><br>
                ▪ <span style="color:#FF8A9B">CTRL</span> + <span style="color:#FF8A9B">Middle Click</span> Drag Curve and Background<br>
                ▪ <span style="color:#FF8A9B">CTRL</span> + <span style="color:#FF8A9B">Left Click</span> Deform Curve<br>

                <b>File Operations:</b><br>
                ▪ <span style="color:#FF8A9B">CTRL+S</span> Quick Save<br>
                ▪ <span style="color:#FF8A9B">CTRL+Z</span> Undo Operation<br>
                ▪ <span style="color:#FF8A9B">CTRL+Y</span> Redo Operation
                """
            self.help_label_text_shift = """
                <b>SHIFT Modifier Key Explanation:</b><br>
                <span style="color:#FF8A9B">The following features only take effect when there are red anchor points</span><br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> + <span style="color:#FF8A9B">Left Click</span><br>
                &nbsp;&nbsp;└ (normal anchor point) Lock Direction to Drag Anchor Point<br>
                &nbsp;&nbsp;└ (red anchor point) Project Adjacent Anchor Points to Tangent<br>
                ▪ <span style="color:#FF8A9B">SHIFT</span> + <span style="color:#FF8A9B">Right Click</span> Balance Red Anchor Points
                """
            self.help_label_text_alt = """
                <b>ALT Modifier Key Explanation:</b><br>
                ▪ <span style="color:#FF8A9B">ALT</span> + <span style="color:#FF8A9B">Left Click</span> Add/Remove Middle Anchor Point<br>
                &nbsp;&nbsp;└ + <span style="color:#FF8A9B">CTRL</span> Add Head/Tail Anchor Point<br>
                ▪ <span style="color:#FF8A9B">ALT</span> + <span style="color:#FF8A9B">Right Click</span> Set Rotation Pivot
                """

    def reset_initial_length(self):
        """重设初始长度为当前长度"""
        if self.cached_curve_points and len(self.cached_curve_points) > 1:
            self.initial_slider_length = self.calculate_curve_length()
            self.update()
    
    def scale_to_initial_length(self):
        """缩放曲线使当前长度等于初始长度，以起始锚点为中心进行缩放"""
        if self.cached_curve_points and len(self.cached_curve_points) > 1 and self.initial_slider_length > 0:
            current_length = self.calculate_curve_length()
            if current_length > 0:
                scale_factor = self.initial_slider_length / current_length
                # 以起始锚点为中心进行缩放
                center_x = self.control_points[0].x()  # 起始锚点的x坐标
                center_y = self.control_points[0].y()  # 起始锚点的y坐标
                
                # 从第二个点开始缩放，保持起始锚点不变
                for point in self.control_points[1:]:
                    dx = point.x() - center_x
                    dy = point.y() - center_y
                    new_x = center_x + dx * scale_factor
                    new_y = center_y + dy * scale_factor
                    point.setX(int(new_x))
                    point.setY(int(new_y))
                
                self.update_curve_cache()
                self.update()
                self.save_state()
    
    def calculate_curve_length(self):
        """计算当前贝塞尔曲线的长度"""
        if not self.cached_curve_points or len(self.cached_curve_points) < 2:
            return 0
        
        total_length = 0
        for i in range(len(self.cached_curve_points) - 1):
            p1 = self.cached_curve_points[i]
            p2 = self.cached_curve_points[i + 1]
            total_length += math.sqrt((p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2)
        
        return total_length

    def load_selected_slider(self):
        """从 EditorReader 读取选中的滑条信息"""
        """
        reader.SetProcess()
        reader.FetchAll()
        # print(f"ContainingFolder: {reader.ContainingFolder}")
        # print(f"objectRadius: {reader.objectRadius}")
        # print(f"stackOffset: {reader.stackOffset}")
        # print(f"HPDrainRate: {reader.HPDrainRate}")
        # print(f"CircleSize: {reader.CircleSize}")
        # print(f"ApproachRate: {reader.ApproachRate}")
        # print(f"OverallDifficulty: {reader.OverallDifficulty}")
        # print(f"SliderMultiplier: {reader.SliderMultiplier}")
        # print(f"SliderTickRate: {reader.SliderTickRate}")
        # print(f"ComposeTool: {reader.ComposeTool()}")
        # print(f"GridSize: {reader.GridSize()}")
        # print(f"BeatDivisor: {reader.BeatDivisor()}")
        # print(f"TimelineZoom: {reader.TimelineZoom}")
        # print(f"DistanceSpacing: {reader.DistanceSpacing}")

        # print(f"Current Time:")
        # print(f"{reader.EditorTime()}")
        
        # print(f"Timing Points:")
        # for controlPoint in reader.controlPoints:
        #     print(f"{controlPoint.ToString()}")
        
        # print(f"Bookmarks:")
        # for bookmark in reader.bookmarks:
        #     print(f"{bookmark}")
        # pos = reader.SnapPosition()
        # print(f"SnapPosition?: {pos.ToString()}")

        reader.FetchSelected()
        for selectedObject in reader.selectedObjects:
            print(f"{selectedObject.ToString()}")
            print(f"SpatialLength: {selectedObject.SpatialLength}")
            print(f"StartTime: {selectedObject.StartTime}")
            print(f"EndTime: {selectedObject.EndTime}")
            print(f"Type: {selectedObject.Type}")
            print(f"SoundType: {selectedObject.SoundType}")
            print(f"SegmentCount: {selectedObject.SegmentCount}")
            print(f"X: {selectedObject.X}")
            print(f"Y: {selectedObject.Y}")
            print(f"BaseX: {selectedObject.BaseX}")
            print(f"BaseY: {selectedObject.BaseY}")
            print(f"SampleFile: {selectedObject.SampleFile}")
            print(f"SampleVolume: {selectedObject.SampleVolume}")
            print(f"SampleSet: {selectedObject.SampleSet}")
            print(f"SampleSetAdditions: {selectedObject.SampleSetAdditions}")
            print(f"CustomSampleSet: {selectedObject.CustomSampleSet}")
            print(f"IsSelected: {selectedObject.IsSelected}")
            print(f"unifiedSoundAddition: {selectedObject.unifiedSoundAddition}")
            print(f"CurveType: {selectedObject.CurveType}")
            print(f"X2: {selectedObject.X2}")
            print(f"Y2: {selectedObject.Y2}")
            print(f"curveLength: {selectedObject.curveLength}")
            # other properties...
            for sliderCurvePoint in selectedObject.sliderCurvePoints:
                print(f"sliderCurvePoint: {sliderCurvePoint}")
        """
        try:
            # 绑定 osu! 进程并获取选中的物件
            reader.SetProcess()
            reader.FetchAll()
            reader.FetchSelected()

            if not reader.selectedObjects:
                QMessageBox.warning(self, self.msg_title_error, self.msg_error_no_slider_selected)
                return

            # 只加载第一个选中的滑条
            selectedObject = reader.selectedObjects[0]
            slider_data = selectedObject.ToString()

            # 解析 osu! 滑条格式
            parts = slider_data.split(",")
            start_x, start_y = int(parts[0]), int(parts[1])
            self.start_time = int(parts[2])  # 保存滑条开始时间
            self.object_type = parts[3]      # 定义物件属性
            self.hit_sound = parts[4]        # hitsound
            self.repeats = int(parts[6])     # 保存滑条重复次数
            self.length = float(parts[7])    # 保存滑条长度
            curve_data = parts[5]  # 形如 "B|83:188|129:149|110:95"

            # 确保是滑条（B| 或 C| 开头）
            if not (curve_data.startswith("B|") or curve_data.startswith("P|") or curve_data.startswith("L|")):
                QMessageBox.warning(self, self.msg_title_error, self.msg_error_not_slider_or_unsupported)
                return

            # 获取当前视图的边界
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

            # 清空当前控制点
            self.control_points = []
            self.red_anchors = set()

            # 添加起始点（转换坐标）
            remapped_start = self.remap_coordinates(
                QPoint(start_x, start_y),
                rect_bottom_left_current_x, rect_bottom_left_current_y,
                rect_top_right_current_x, rect_top_right_current_y,
                reverse=True
            )
            self.control_points.append(remapped_start)

            # 解析滑条锚点
            control_points_str = curve_data[2:].split("|")  # 去掉 "B|" 或 "C|"
            remapped_slider_points = [] # 用于存储反向映射后的滑条点
            prev_point = None # 用于存储前一个点，检测连续相同点
            
            for pt in control_points_str:
                x, y = map(int, pt.split(":"))
                current_point = QPoint(int(x), int(y))
                
                # 检查是否与前一个点坐标相同（红锚点标记）
                if prev_point is not None and prev_point.x() == current_point.x() and prev_point.y() == current_point.y():
                    # 如果与前一个点坐标相同，则跳过此点（因为已经添加过了）
                    # 并将前一个点的索引添加到红锚点集合中
                    self.red_anchors.add(len(self.control_points) + len(remapped_slider_points) - 1)
                    prev_point = None # 重置前一个点，避免连续三个相同点的情况
                    continue
                
                # 正常处理点坐标
                new_point_remapped = self.remap_coordinates( # 调用 remap_coordinates 进行反向映射
                    current_point,
                    rect_bottom_left_current_x, rect_bottom_left_current_y,
                    rect_top_right_current_x, rect_top_right_current_y,
                    reverse=True # 传入 reverse=True 参数，执行反向映射
                )
                remapped_slider_points.append(new_point_remapped) # 将反向映射后的点添加到 remapped_slider_points 列表
                prev_point = current_point # 更新前一个点
            
            self.control_points.extend(remapped_slider_points) # 将反向映射后的滑条点列表添加到 self.control_points
            self.allow_save2osu = True
            # 更新曲线显示
            self.update_curve_cache()
            # 计算并存储初始滑条长度
            self.initial_slider_length = self.calculate_curve_length()
            self.current_slider_length = self.initial_slider_length
            self.update()

            QMessageBox.information(self, self.msg_title_success, self.msg_success_load_selected_slider)

        except Exception as e:
            QMessageBox.warning(self, self.msg_title_error, self.msg_error_load_selected_slider.format(error=str(e)))

    def save_slider_data(self):
        """将修改后的滑条数据写回 .osu 文件"""
        if self.allow_save2osu:
            try:
                if not self.osu_songs_path:
                    QMessageBox.warning(self, self.msg_title_error, self.msg_set_osu_path)
                    return

                reader.SetProcess()
                reader.FetchAll()
                reader.FetchSelected()

                if any(val is None for val in [self.start_time, self.object_type, self.hit_sound, self.repeats, self.length]):
                    QMessageBox.warning(self, self.msg_title_error, self.msg_error_import_first_osu)
                    return

                # 获取 osu! 文件路径
                beatmap_folder = reader.ContainingFolder
                process_title = reader.ProcessTitle()  # "osu!  - artist - title (mapper) [diff name].osu"
                if " - " in process_title:
                    osu_filename = process_title.split("osu!  - ", 1)[-1].strip()  # 提取 " - " 后面的部分
                else:
                    osu_filename = process_title.strip()  # 以防万一
                osu_file_path = os.path.join(self.osu_songs_path, beatmap_folder, osu_filename)

                if not os.path.exists(osu_file_path):
                    QMessageBox.warning(self, self.msg_title_error, self.msg_error_osu_file_not_found.format(osu_file_path=osu_file_path))
                    return

                # 读取 .osu 文件
                with open(osu_file_path, "r", encoding="utf-8") as f:
                    osu_data = f.readlines()

                # 读取原滑条数据
                selectedObject = reader.selectedObjects[0]
                original_slider = selectedObject.ToString()

                # 获取当前视图的边界
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

                # 反向转换坐标（BezierCurveEditor → osu!）
                first_mapped_point = self.remap_coordinates(
                    self.control_points[0],
                    rect_bottom_left_current_x, rect_bottom_left_current_y,
                    rect_top_right_current_x, rect_top_right_current_y,
                    reverse=False  # 导出时反向映射
                )

                # ✅ 生成修改后的滑条数据（去掉第一个点）
                new_control_points = []
                for i, pt in enumerate(self.control_points[1:], 1):  # 🚀 从索引 `1` 开始，去掉第一个点
                    osu_point = self.remap_coordinates(
                        pt,
                        rect_bottom_left_current_x, rect_bottom_left_current_y,
                        rect_top_right_current_x, rect_top_right_current_y,
                        reverse=False
                    )
                    new_control_points.append(f"{osu_point.x()}:{osu_point.y()}")
                    
                    # 如果当前点是红色锚点，则重复添加该点（红锚点在osu!中表示为连续两个相同的点）
                    if i in self.red_anchors:
                        new_control_points.append(f"{osu_point.x()}:{osu_point.y()}") 

                new_curve_data = "B|" + "|".join(new_control_points)

                # 重新拼接 osu! 滑条字符串
                new_slider = f"{first_mapped_point.x()},{first_mapped_point.y()},{self.start_time},{self.object_type},{self.hit_sound},{new_curve_data},{self.repeats},{self.length}"

                # 替换 osu! 文件内容
                osu_data = [line.replace(original_slider, new_slider) for line in osu_data]

                # 写回 .osu 文件
                with open(osu_file_path, "w", encoding="utf-8") as f:
                    f.writelines(osu_data)

                QMessageBox.information(self, self.msg_title_success, self.msg_success_export_osu) 
                self.allow_save2osu = False

            except Exception as e:
                QMessageBox.warning(self, self.msg_title_error, self.msg_error_save_slider.format(error=e)) 
                self.allow_save2osu = False
        else:
            QMessageBox.warning(self, self.msg_title_error, "请从osu!重新导入滑条")
            self.allow_save2osu = False

            
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
        # 确保icons目录存在
        icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        if not os.path.exists(icons_dir):
            os.makedirs(icons_dir)

        # 创建左侧按钮区域背景
        self.left_panel = QWidget(self)
        self.left_panel.setGeometry(0, 0, 80, self.height())
        self.left_panel.setStyleSheet("background-color: #262626;")

        # 按钮样式 - 左侧图标按钮
        self.sidebar_button_style = """
            QPushButton {
                background-color: #262626;
                color: white;
                border: 1px solid #262626;
                border-radius: 2px;
                padding: 5px;
                font-size: 7px;
            }
            QPushButton:hover {
                background-color: #1F1F1F;
            }
        """

        # 创建左侧按钮
        self.create_sidebar_buttons()

        # 操作提示标签
        self.help_label = QLabel(self.help_label_text_full, self) 
        self.help_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 150);
                color: white;
                padding: 10px;
                border-radius: 10px;
                font-size: 12px;
            }
        """)
        self.help_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.help_label.setWordWrap(False)
        self.help_label.adjustSize()
        self.update_help_position()

        # 默认显示帮助和滑块
        self.help_visible = True
        self.sliders_visible = True
        
        # 创建滑块控件（放在右侧区域）
        self.create_sliders()
        
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
        
        # 根据路径有效性显示/隐藏按钮
        self.update_buttons_visibility()

    def toggle_visualization_display(self):
        """
        切换可视化效果的显示状态 (槽函数，连接到开关按钮的 clicked 信号)
        """
        self.is_visualization_enabled = not self.is_visualization_enabled
        # 更新可视化按钮的图标颜色
        for button in self.sidebar_buttons:
            if button.toolTip() == self.button_text_visualizations:
                self.update_button_icon_color(button, self.is_visualization_enabled)
                break
        self.update()

    def toggle_help_visibility(self):
        """切换帮助的可见性"""
        self.help_visible = not self.help_visible
        self.help_label.setVisible(self.help_visible)
        # 更新帮助按钮的图标颜色
        for button in self.sidebar_buttons:
            if button.toolTip() == self.button_text_show_help:
                self.update_button_icon_color(button, self.help_visible)
                break
                
    def restart_program(self):
        """重启程序"""
        # 显示确认对话框
        reply = QMessageBox.question(self, self.msg_title_prompt, self.msg_prompt_restart_program,
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 清空当前数据
            self.control_points = []
            self.red_anchors = set() # 清理红锚点数据

            self.rotation_pivot_point = None  # 旋转基准点 (QPoint)
            self.has_rotation_pivot = False   # 是否已设置旋转基准点 (bool)
            self.initial_slider_length = 0  # 初始滑条长度
            self.current_slider_length = 0  # 当前滑条长度
            self.image = None
            self.dragging_point = None
            self.preview_point = None
            self.is_preview_enabled = False
            self.preview_segment_index = -1
            self.highlighted_segment_index = None
            self.is_dragging_control_point = False
            self.pre_selected_point_index = None
            self.cached_curve_points = None
            self.update_curve_cache()
            self.update()

    def toggle_sliders_visibility(self):
        """切换滑块面板的可见性"""
        self.sliders_visible = not self.sliders_visible
        self.sliders_panel.setVisible(self.sliders_visible)
        # 更新滑块按钮的图标颜色
        for button in self.sidebar_buttons:
            if button.toolTip() == self.button_text_sliders:
                self.update_button_icon_color(button, self.sliders_visible)
                break
                
    def update_button_icon_color(self, button, is_active):
        """更新按钮图标颜色"""
        if hasattr(button, 'icon_path') and os.path.exists(button.icon_path):
            with open(button.icon_path, 'r') as f:
                svg_content = f.read()
            
            # 根据激活状态设置颜色
            color = "#FF8A9B" if is_active else "white"
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            
            # 创建临时文件用于设置图标
            temp_svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_normal_{id(button)}.svg")
            with open(temp_svg_path, 'w') as f:
                f.write(svg_content)
            
            formatted_path = temp_svg_path.replace('\\', '/')
            # 更新按钮样式，保留文本位置和样式
            button.setStyleSheet(self.sidebar_button_style + f"""
                QPushButton {{                    
                    background-image: url({formatted_path});
                    background-position: center 0px;
                    background-repeat: no-repeat;
                    text-align: center;
                    padding-top: 45px;
                    font-size: 10px;
                    color: {color};
                    border: 1px solid {"#FF8A9B" if is_active else "#474747"};
                }}
            """) 
            
    def load_config(self):
        """加载配置文件，获取osu! Songs文件夹路径"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get("osu_songs_path")
            else:
                # 如果配置文件不存在，弹出提示框
                system_locale_name = QLocale.system().name()
                is_chinese_system = system_locale_name.startswith("zh")
                if is_chinese_system:
                    self.msg_set_osu_path_title = "设置osu!歌曲文件夹"
                    self.msg_set_osu_path_prompt = "是否选择osu!歌曲文件夹路径？"
                    self.msg_set_osu_path_dialog = "选择osu!/Songs文件夹"
                else:
                    self.msg_set_osu_path_title = "Set osu! Songs Folder"
                    self.msg_set_osu_path_prompt = "Do you want to set the osu! Songs folder path?"
                    self.msg_set_osu_path_dialog = "Select osu!/Songs folder"

                msg = QMessageBox()
                msg.setWindowTitle(self.msg_set_osu_path_title)
                msg.setText(self.msg_set_osu_path_prompt)
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                
                if msg.exec_() == QMessageBox.Yes:
                    # 用户点击确认，打开文件夹选择对话框
                    folder_path = QFileDialog.getExistingDirectory(None, self.msg_set_osu_path_dialog)
                    if folder_path:
                        # 保存用户选择的路径
                        with open(self.config_file, 'w') as f:
                            json.dump({"osu_songs_path": folder_path, "skip_prompt": False}, f, indent=4)
                        return folder_path
                else:
                    # 用户点击跳过，记录并不再提示
                    with open(self.config_file, 'w') as f:
                        json.dump({"osu_songs_path": None, "skip_prompt": True}, f, indent=4)
                    return None
                    
                # 如果用户取消选择，返回None
                with open(self.config_file, 'w') as f:
                    json.dump({"osu_songs_path": None, "skip_prompt": False}, f, indent=4)
                return None
                
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return None
            
    def save_config(self, osu_songs_path):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({"osu_songs_path": osu_songs_path}, f, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
            
    def check_osu_path_valid(self):
        """检查osu! Songs文件夹路径是否有效"""
        if self.osu_songs_path is None:
            return False
        return os.path.exists(self.osu_songs_path) and os.path.isdir(self.osu_songs_path)
        
    def set_osu_path(self):
        """设置osu! Songs文件夹路径"""
        folder_path = QFileDialog.getExistingDirectory(self, self.msg_set_osu_path, self.osu_songs_path)
        if folder_path:
            # 检查选择的路径是否有效
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                self.osu_songs_path = folder_path
                self.save_config(folder_path)
                self.is_osu_path_valid = True
                QMessageBox.information(self, self.msg_title_success, self.msg_set_osu_path_success)
                self.update_buttons_visibility()
            else:
                QMessageBox.warning(self, self.msg_title_error, self.msg_set_osu_path_error)
                
    def update_buttons_visibility(self):
        """根据osu路径有效性更新按钮显示状态"""
        # 在新的UI设计中，我们不再使用单独的按钮来控制可见性
        # 而是通过侧边栏按钮来处理所有功能
        pass 

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

    def create_sidebar_buttons(self):
        """创建左侧垂直排列的按钮"""
        # 按钮配置 - 每个按钮的图标、提示文本、回调方法和详细说明
        system_locale_name = QLocale.system().name()
        is_chinese_system = system_locale_name.startswith("zh")
        
        # 根据系统语言选择按钮详细说明文本
        if is_chinese_system:
            button_details = {
                "import_slider": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">从osu!编辑器中加载当前选中的滑条</span><br>需要先在osu!编辑器中选择一个滑条，然后点击此按钮进行导入。",
                "export_slider": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">将当前编辑的滑条导出回osu!编辑器</span><br>需要先从osu!编辑器导入滑条后才能使用此功能，并且要有选中的滑条。",
                "import_image": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">导入背景图片作为参考</span><br>支持常见图片格式如PNG、JPG等。",
                "import_text": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">从文本文件导入滑条控制点数据</span><br>可以导入之前导出的控制点数据。",
                "export_text": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">将当前滑条的控制点数据导出为文本文件</span><br>导出的数据可以稍后再导入或分享给他人。",
                "slider_toggle": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">显示/隐藏参数调整滑块面板</span><br>可以调整图像缩放、透明度、曲线段数等参数。",
                "help": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">显示/隐藏帮助信息</span><br>包含各种快捷键和操作说明。",
                "settings": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">设置osu!歌曲文件夹路径</span><br>需要正确设置才能与osu!编辑器交互。",
                "visualization": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">开启/关闭可视化效果</span><br>包括锚点影响范围、曲线分段等视觉辅助功能，关闭可节约性能开销。"
            }
        else:
            button_details = {
                "import_slider": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Load the currently selected slider from the osu! editor</span><br>You need to select a slider in the osu! editor first, then click this button to import it.",
                "export_slider": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Export the currently edited slider back to the osu! editor</span><br>You must first import a slider from the osu! editor to use this feature, and a slider must be selected.",
                "import_image": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Import a background image as a reference</span><br>Supports common image formats such as PNG, JPG, etc.",
                "import_text": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Import slider control points from a text file</span><br>You can import previously exported control point data.",
                "export_text": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Export the current slider's control points as a text file</span><br>The exported data can be imported later or shared with others.",
                "slider_toggle": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Show/Hide the parameter adjustment slider panel</span><br>You can adjust parameters such as image scaling, transparency, curve segments, etc.",
                "help": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Show/Hide help information</span><br>Includes various shortcuts and operation instructions.",
                "settings": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Set the osu! song folder path</span><br>This must be set correctly to interact with the osu! editor.",
                "visualization": "<span style=\"font-size: 14px; font-weight: bold; color: #ff8a9b\">Enable/Disable visualization effects</span><br>Includes visual aids such as anchor influence range and curve segmentation. Disabling this can save performance overhead."
            }
        
        button_configs = [
            {"icon": "icons/import_slider.svg", "tooltip": self.button_text_load_selected_slider, "callback": self.load_selected_slider, "detail": button_details["import_slider"]},
            {"icon": "icons/export_slider.svg", "tooltip": self.button_text_export_to_osu, "callback": self.save_slider_data, "detail": button_details["export_slider"]},
            {"icon": "icons/import_image.svg", "tooltip": self.button_text_import_image, "callback": self.import_image, "detail": button_details["import_image"]},
            {"icon": "icons/import_text.svg", "tooltip": self.button_text_import_slider, "callback": self.import_slider, "detail": button_details["import_text"]},
            {"icon": "icons/export_text.svg", "tooltip": self.button_text_export_control_points, "callback": self.export_points, "detail": button_details["export_text"]},
            {"icon": "icons/slider_toggle.svg", "tooltip": self.button_text_sliders, "callback": self.toggle_sliders_visibility, "active": True, "detail": button_details["slider_toggle"]},
            {"icon": "icons/help.svg", "tooltip": self.button_text_show_help, "callback": self.toggle_help_visibility, "active": True, "detail": button_details["help"]},
            {"icon": "icons/settings.svg", "tooltip": self.button_text_osu_path, "callback": self.set_osu_path, "detail": button_details["settings"]},
            {"icon": "icons/visualization.svg", "tooltip": self.button_text_visualizations, "callback": self.toggle_visualization_display, "active": True, "detail": button_details["visualization"]}
        ]
        
        # 创建按钮
        self.sidebar_buttons = []
        button_height = 75  # 增加高度以容纳文字
        button_width = 75   
        button_margin = 8   
        
        # 计算底部按钮的起始位置
        bottom_buttons = ["slider_toggle", "help", "settings", "visualization"]
        bottom_start = self.height() - (len(bottom_buttons) * (button_height + button_margin)) - button_margin
        
        # 保存当前帮助文本，用于鼠标离开按钮时恢复
        self.original_help_text = self.help_label_text_full
        
        for i, config in enumerate(button_configs):
            button = HoverButton(self)
            button.setStyleSheet(self.sidebar_button_style)
            button.setFixedSize(button_width, button_height)
            
            # 判断是否为底部按钮
            icon_name = config["icon"].split("/")[-1].split(".")[0]
            if icon_name in bottom_buttons:
                bottom_index = bottom_buttons.index(icon_name)
                y_pos = bottom_start + bottom_index * (button_height + button_margin)
            else:
                y_pos = i * (button_height + button_margin) + 2
            
            button.move(2, y_pos)
            button.clicked.connect(config["callback"])
            button.setToolTip(config["tooltip"])
            
            # 设置SVG图标
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config["icon"])
            button.icon_path = icon_path  # 保存icon_path到按钮对象
            with open(icon_path, 'r') as f:
                svg_content = f.read()
            
            # 替换SVG中的颜色
            active_color = "#FF8A9B" if config.get("active", False) else "white"
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{active_color}"')
            
            # 创建临时文件用于设置图标
            temp_svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_{i}.svg")
            with open(temp_svg_path, 'w') as f:
                f.write(svg_content)
            
            # 设置图标和文字
            button.setText(config["tooltip"])
            formatted_path = temp_svg_path.replace('\\', '/')
            button.setStyleSheet(self.sidebar_button_style + f"""
                QPushButton {{                    
                    background-image: url({formatted_path});
                    background-position: center 0px;
                    background-repeat: no-repeat;
                    text-align: center;
                    padding-top: 45px;
                    font-size: 10px;
                    border: 1px solid {"#FF8A9B" if config.get("active", False) else "#474747"};
                    color: {active_color};
                }}
            """)
            
            # 设置按钮的详细说明文本
            button.detail_text = config["detail"]
            button.parent_widget = self  # 保存父窗口引用，用于在悬停事件中访问help_label
            
            self.sidebar_buttons.append(button)
    
    def create_sliders(self):
        """创建滑块控件"""
        # 创建半透明面板
        self.sliders_panel = QWidget(self)
        self.sliders_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 150);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        # 滑块样式
        slider_style = """
            QSlider {
                background: transparent;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #444444, stop:1 #555555);
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF8A9B, stop:1 #FF647A);
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
                border: none;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FF647A, stop:1 #FF4A64);
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:disabled {
                background: #555555;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
                opacity: 0.5;
            }
            QSlider::groove:horizontal:disabled {
                background: #333333;
                opacity: 0.3;
            }
        """
        
        # 标签样式
        label_style = "color: #FFFFFF; font-size: 12px; font-weight: 500; letter-spacing: 0.5px; background: transparent;"
        
        # 滑块配置
        slider_configs = [
            {"name": "scale", "label": self.button_text_image_scale, "min": 10, "max": 200, "value": 100, "callback": self.update_image_scale},
            {"name": "opacity", "label": self.button_text_image_opacity, "min": 0, "max": 100, "value": 70, "callback": self.update_image_opacity},
            {"name": "segments", "label": self.button_text_curve_segments, "min": 10, "max": 500, "value": 100, "callback": self.update_curve_segments},
            {"name": "circle_size", "label": self.button_text_circle_size, "min": 0, "max": 10, "value": 4, "callback": self.update_circle_size},
            {"name": "outline_opacity", "label": self.button_text_outline_opacity, "min": 0, "max": 90, "value": 85, "callback": self.update_outline_opacity},
            {"name": "rect_scale", "label": self.button_text_playfield_boundary, "min": 10, "max": 100, "value": int(self.rect_scale * 100), "callback": self.update_rect_scale}
        ]
        
        # 创建滑块控件
        self.sliders = {}
        self.slider_labels = []
        slider_width = 150
        slider_height = 20
        label_height = 20
        slider_margin = 10
        start_x = 10
        start_y = 10
        panel_padding = 10
        
        for i, config in enumerate(slider_configs):
            # 创建标签
            label = QLabel(config["label"], self.sliders_panel)
            label.setStyleSheet(label_style)
            label.move(start_x, start_y + i * (slider_height + label_height + slider_margin))
            self.slider_labels.append(label)
            
            # 创建滑块
            slider = QSlider(Qt.Horizontal, self.sliders_panel)
            slider.setStyleSheet(slider_style)
            slider.setMinimum(config["min"])
            slider.setMaximum(config["max"])
            slider.setValue(config["value"])
            slider.setFixedWidth(slider_width)
            slider.move(start_x, start_y + i * (slider_height + label_height + slider_margin) + label_height)
            slider.valueChanged.connect(config["callback"])
            
            # 保存滑块引用
            self.sliders[config["name"]] = slider
            
            # 为circle_size滑块添加值标签
            if config["name"] == "circle_size":
                self.circle_size_value_label = QLabel(str(slider.value()), self.sliders_panel)
                self.circle_size_value_label.setStyleSheet(label_style)
                label_width = label.sizeHint().width()
                self.circle_size_value_label.move(start_x + label_width + 5, start_y + i * (slider_height + label_height + slider_margin))
                self.slider_labels.append(self.circle_size_value_label)
                slider.valueChanged.connect(self.update_circle_size_label)
            
            # 设置图片相关滑块的初始状态
            if config["name"] in ["scale", "opacity"]:
                slider.setEnabled(False)
                # 设置初始透明度
                slider.setWindowOpacity(0.3)
                label.setWindowOpacity(0.3)
        
        # 创建圆形按钮样式
        circle_button_style = """
            QPushButton {
                background-color: #ff8a9b;
                border-radius: 17px;
                width: 18px;
                height: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #8a42ad;
            }
            QPushButton:pressed {
                background-color: #181D28;
            }
        """
        
        # 计算按钮位置
        button_y = start_y + len(slider_configs) * (slider_height + label_height + slider_margin) + 20
        button_spacing = 50
        
        # 创建撤销按钮
        self.undo_button = QPushButton(self.sliders_panel)
        self.undo_button.setStyleSheet(circle_button_style)
        self.undo_button.move(start_x + 10, button_y)
        self.undo_button.clicked.connect(self.undo)
        self.undo_button.setToolTip(self.button_text_undo)
        self.undo_button.setIcon(QIcon("icons/undo.svg"))
        self.undo_button.setIconSize(QSize(24, 24))
        
        # 创建重做按钮
        self.redo_button = QPushButton(self.sliders_panel)
        self.redo_button.setStyleSheet(circle_button_style)
        self.redo_button.move(start_x + 10 + button_spacing, button_y)
        self.redo_button.clicked.connect(self.redo)
        self.redo_button.setToolTip(self.button_text_redo)
        self.redo_button.setIcon(QIcon("icons/redo.svg"))
        self.redo_button.setIconSize(QSize(24, 24))
        
        # 创建清空画布按钮
        self.clear_button = QPushButton(self.sliders_panel)
        self.clear_button.setStyleSheet(circle_button_style)
        self.clear_button.move(start_x + 10 + button_spacing * 2, button_y)
        self.clear_button.clicked.connect(self.restart_program)
        self.clear_button.setToolTip(self.button_text_clear_canvas)
        self.clear_button.setIcon(QIcon("icons/clear.svg"))
        self.clear_button.setIconSize(QSize(24, 24))
        
        # 设置面板大小和位置
        panel_width = slider_width + 50
        panel_height = (len(slider_configs) * (slider_height + label_height + slider_margin)) + panel_padding * 2 + 80
        self.sliders_panel.setGeometry(90, 10, panel_width, panel_height)
        self.sliders_panel.show()
    
    def resizeEvent(self, event):
        """窗口大小变化时更新帮助位置"""
        super().resizeEvent(event)
        
        # 更新左侧面板和绘图区域大小
        if hasattr(self, 'left_panel'):
            self.left_panel.setGeometry(0, 0, 80, self.height())
        if hasattr(self, 'drawing_area'):
            self.drawing_area.setGeometry(80, 0, self.width() - 80, self.height())
            
        # 更新帮助标签位置
        if hasattr(self, 'help_label'):
            self.update_help_position()  # 更新帮助标签位置
        if hasattr(self, 'save_label'):
            # 更新保存提示位置为屏幕中心
            label_width = self.save_label.sizeHint().width()
            label_height = self.save_label.sizeHint().height()
            self.save_label.move((self.width() - label_width) // 2, (self.height() - label_height) // 2)
        # 更新底部按钮位置
        if hasattr(self, 'sidebar_buttons'):
            button_height = 75
            button_margin = 8
            bottom_buttons = ["slider_toggle", "help", "settings", "visualization"]
            bottom_start = self.height() - (len(bottom_buttons) * (button_height + button_margin)) - button_margin
            
            for button in self.sidebar_buttons:
                icon_name = button.icon_path.split("/")[-1].split(".")[0]
                if icon_name in bottom_buttons:
                    bottom_index = bottom_buttons.index(icon_name)
                    y_pos = bottom_start + bottom_index * (button_height + button_margin)
                    button.move(2, y_pos)
                    
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
        # 跟踪Shift键状态
        elif event.key() == Qt.Key_Shift:
            self.is_shift_pressed = True
            # 更新帮助内容为Shift相关
            self.help_label.setText(self.help_label_text_shift)
            self.help_label.adjustSize()
            self.update_help_position()
            self.update()
        # 跟踪Alt键状态
        elif event.key() == Qt.Key_Alt:
            self.is_alt_pressed = True
            # 更新帮助内容为Alt相关
            self.help_label.setText(self.help_label_text_alt)
            self.help_label.adjustSize()
            self.update_help_position()
            self.update()

        # 跟踪Ctrl键状态
        elif event.key() == Qt.Key_Control:
            self.is_ctrl_pressed = True
            # 更新帮助内容为Ctrl相关
            if self.is_alt_pressed:
                self.help_label.setText(self.help_label_text_alt)
            else:
                self.help_label.setText(self.help_label_text_ctrl)
            self.help_label.adjustSize()
            self.update_help_position()
            self.update()

    def undo(self):
        if self.history:
            self.future.append((self.control_points.copy(), self.red_anchors.copy()))  # 保存当前状态到 future
            last_state = self.history.pop()  # 恢复上一个状态
            self.control_points = last_state[0]
            # 恢复红色锚点信息
            if len(last_state) > 1:
                self.red_anchors = last_state[1]
            else:
                self.red_anchors = set()  # 兼容旧版本保存的状态
            self.pre_selected_point_index = None
            self.update_curve_cache()
            self.update()
        else:
            print("No history to undo")

    def redo(self):
        if self.future:
            # 将当前状态保存到 history
            self.history.append((self.control_points.copy(), self.red_anchors.copy()))
            # 恢复到下一个状态
            next_state = self.future.pop()
            self.control_points = next_state[0]
            # 恢复红色锚点信息
            if len(next_state) > 1:
                self.red_anchors = next_state[1]
            else:
                self.red_anchors = set()  # 兼容旧版本保存的状态
            self.update_curve_cache()  # 刷新缓存
            self.update()
            
    def keyReleaseEvent(self, event):
        # 释放Shift键时更新状态
        if event.key() == Qt.Key_Shift:
            self.is_shift_pressed = False
            # 恢复完整帮助内容
            self.help_label.setText(self.help_label_text_full)
            self.help_label.adjustSize()
            self.update_help_position()
            self.update()
        # 释放Ctrl键时更新状态
        elif event.key() == Qt.Key_Control:
            self.is_ctrl_pressed = False
            # 恢复完整帮助内容
            self.help_label.setText(self.help_label_text_full)
            self.help_label.adjustSize()
            self.update_help_position()
            self.update()
        # 释放Alt键时更新状态
        elif event.key() == Qt.Key_Alt:
            self.is_alt_pressed = False
            # 恢复完整帮助内容
            self.help_label.setText(self.help_label_text_full)
            self.help_label.adjustSize()
            self.update_help_position()
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if event.modifiers() == Qt.ControlModifier:
                # Ctrl + 鼠标中键：开始拖动曲线和图片 (保持不变)
                self.dragging_curve_and_image = True
                self.dragging_curve_only = False
            else:
                # 鼠标中键：开始单独拖动曲线 (保持不变)
                self.dragging_curve_only = True
                self.dragging_curve_and_image = False
            self.last_mouse_pos = event.pos()
        elif event.button() == Qt.LeftButton:
            self.is_left_button_pressed = True
            # 1. alt+左键且存在预选中锚点时：删除锚点 (保持不变)
            if event.modifiers() == Qt.AltModifier and self.pre_selected_point_index is not None:
                if self.pre_selected_point_index is not None: # 再次检查预选中锚点索引是否有效
                    self.delete_control_point_by_index(self.pre_selected_point_index)
                    self.pre_selected_point_index = None  # 删除后清除预选
                    self.update()
                    return  # 提前返回，避免执行后续的左键添加锚点逻辑
            # 2. 存在预选中锚点时 左键拖动锚点 (保持不变)
            elif self.pre_selected_point_index is not None:
                current_idx = self.pre_selected_point_index
                # 如果点击的是红色锚点，计算切线并投影相邻点
                if current_idx in self.red_anchors and self.is_shift_pressed:
                    self.save_state()
                    # 计算红色锚点的切线方向
                    tangent_dir = self.calculate_tangent_line(current_idx)
                    if tangent_dir:
                        # 获取相邻的两个锚点
                        prev_idx = current_idx - 1 if current_idx > 0 else None
                        next_idx = current_idx + 1 if current_idx < len(self.control_points) - 1 else None
                        
                        # 将相邻点投影到切线上
                        if prev_idx is not None:
                            projected_point = self.project_point_to_line(
                                self.control_points[prev_idx],
                                self.control_points[current_idx],
                                tangent_dir
                            )
                            if projected_point:
                                self.control_points[prev_idx] = projected_point
                        
                        if next_idx is not None:
                            projected_point = self.project_point_to_line(
                                self.control_points[next_idx],
                                self.control_points[current_idx],
                                tangent_dir
                            )
                            if projected_point:
                                self.control_points[next_idx] = projected_point
                        self.update_curve_cache()
                        self.update()
                        return
                # 如果是普通锚点，保持原有的拖动逻辑
                self.dragging_point = current_idx
                self.is_dragging_control_point = True
                self.drag_start_point = event.pos()
                
                # 保存拖动开始时的状态，用于shift+左键拖动时计算
                self.save_state() # 保存状态，以便可以撤销
                
                # 锁定与相邻红色锚点形成的直线 - 仅在按下Shift键时锁定
                if not current_idx in self.red_anchors and event.modifiers() == Qt.ShiftModifier:  # 只对白色锚点执行锁定，且仅在按下Shift键时
                    # 检查前一个点是否为红色锚点
                    self.locked_line_direction = None
                    self.locked_line_point = None
                    
                    # 检查前一个点
                    prev_red_idx = None
                    if current_idx > 0 and (current_idx - 1) in self.red_anchors:
                        prev_red_idx = current_idx - 1
                    
                    # 检查后一个点
                    next_red_idx = None
                    if current_idx < len(self.control_points) - 1 and (current_idx + 1) in self.red_anchors:
                        next_red_idx = current_idx + 1
                    
                    # 如果有相邻的红色锚点，锁定直线
                    if prev_red_idx is not None or next_red_idx is not None:
                        red_idx = prev_red_idx if prev_red_idx is not None else next_red_idx
                        red_point = self.control_points[red_idx]
                        
                        # 计算从红色锚点到当前锚点的方向向量
                        dx = self.control_points[current_idx].x() - red_point.x()
                        dy = self.control_points[current_idx].y() - red_point.y()
                        length = math.sqrt(dx * dx + dy * dy)
                        
                        if length > 0:
                            # 归一化方向向量并保存
                            self.locked_line_direction = (dx/length, dy/length)
                            self.locked_line_point = red_point
                else:
                    # 无修饰键时，不锁定直线方向
                    self.locked_line_direction = None
                    self.locked_line_point = None
                
                if event.modifiers() == Qt.ShiftModifier:
                    # 记录初始锚点坐标和鼠标位置
                    self.initial_anchor_pos = self.control_points[self.dragging_point]
                    self.shift_drag_start_pos = event.pos()
                    return

                # Shift+拖动时基于初始坐标计算位移
                if event.modifiers() == Qt.ShiftModifier and hasattr(self, 'initial_anchor_pos'):
                    delta = event.pos() - self.shift_drag_start_pos
                    new_x = self.initial_anchor_pos.x() + delta.x()
                    new_y = self.initial_anchor_pos.y() + delta.y()
                    self.control_points[self.dragging_point] = QPoint(int(new_x), int(new_y))
                    self.update_curve_cache()
                    self.update()
                    return
                
                return  # 提前返回，避免执行后续的左键添加锚点逻辑
            # 3. 仅在无预选中锚点和无修饰键时 左键加添锚点 (保持不变)
            elif self.pre_selected_point_index is None and event.modifiers() == Qt.NoModifier: # 确保没有预选中点和没有修饰键
                self.save_state()
                self.control_points.append(event.pos())
                # 添加到末尾不需要更新红色锚点索引
                self.update_curve_cache()
                self.update()
            # Alt + Ctrl：添加头尾锚点 (保持不变) - 但只有在没有预选点时才触发，避免冲突
            elif event.modifiers() & Qt.AltModifier and event.modifiers() & Qt.ControlModifier and len(self.control_points) >= 2 and self.pre_selected_point_index is None:
                self.save_state()
                insert_index = self.get_insert_position(event.pos())
                if insert_index is not None:
                    if insert_index == 0:
                        # 更新红色锚点索引，考虑在头部插入新点后的索引变化
                        updated_red_anchors = set()
                        for idx in self.red_anchors:
                            updated_red_anchors.add(idx + 1)  # 所有红色锚点索引+1
                        self.red_anchors = updated_red_anchors
                        
                        self.control_points.insert(0, event.pos())
                    else:
                        # 添加到末尾不需要更新红色锚点索引
                        self.control_points.append(event.pos())
                    self.update_curve_cache()
                    self.update()
            # 仅 Alt：添加中间锚点 (保持不变) - 但只有在没有预选点时才触发，避免冲突
            elif event.modifiers() == Qt.AltModifier and self.pre_selected_point_index is None:
                self.insert_control_point(event.pos())
            elif event.modifiers() == Qt.ControlModifier and self.closest_curve_point is not None:
                # Ctrl + 左键：开始拖动曲线变形 (保持不变)
                self.save_state()
                self.is_ctrl_dragging_deformation = True
                self.drag_start_pos = event.pos()
                self.locked_closest_point = self.closest_curve_point
                # 计算并锁定 t 值 (保持不变)
                min_distance = float('inf')
                closest_idx = -1
                for i, point in enumerate(self.cached_curve_points):
                    distance = self.distance(self.locked_closest_point, point)
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i
                self.locked_t = closest_idx / self.curve_segments if self.curve_segments > 0 else 0


        elif event.button() == Qt.RightButton:
            self.is_right_button_pressed = True # 记录右键按下

            # 【新增：Shift + 右键点击红锚点时，保持红锚点位置不变，将前一个、后一个锚点处于一条直线上】
            if event.modifiers() == Qt.ShiftModifier and self.pre_selected_point_index is not None:
                # 检查是否点击的是红色锚点
                if self.pre_selected_point_index in self.red_anchors:
                    self.save_state()
                    # 获取当前红色锚点的索引和位置
                    red_idx = self.pre_selected_point_index
                    red_point = self.control_points[red_idx]
                    
                    # 检查是否有前一个锚点
                    if red_idx > 0:
                        prev_idx = red_idx - 1
                        # 检查是否有后一个锚点
                        if red_idx < len(self.control_points) - 1:
                            next_idx = red_idx + 1
                            # 计算直线方向向量
                            # 使用红色锚点作为基准点，计算直线方向
                            # 将前一个点和后一个点放在同一条直线上
                            # 保持前一个点到红色锚点的距离不变
                            prev_point = self.control_points[prev_idx]
                            next_point = self.control_points[next_idx]
                            
                            # 计算前一个点到红色锚点的距离
                            prev_distance = math.sqrt((prev_point.x() - red_point.x())**2 + (prev_point.y() - red_point.y())**2)
                            
                            # 计算方向向量（从红色锚点指向前一个点）
                            direction_x = prev_point.x() - red_point.x()
                            direction_y = prev_point.y() - red_point.y()
                            
                            # 归一化方向向量
                            length = math.sqrt(direction_x**2 + direction_y**2)
                            if length > 0:
                                direction_x /= length
                                direction_y /= length
                            
                            # 计算后一个点的新位置（与前一个点在同一直线上，但在红色锚点的另一侧）
                            # 使用与前一个点相同的距离
                            new_next_x = red_point.x() - direction_x * prev_distance
                            new_next_y = red_point.y() - direction_y * prev_distance
                            
                            # 更新后一个点的位置
                            self.control_points[next_idx] = QPoint(int(new_next_x), int(new_next_y))
                            self.update_curve_cache()
                            self.update()
                    
            # 【新增：Alt + 右键设置旋转基准点】
            elif event.modifiers() == Qt.AltModifier:
                self.rotation_pivot_point = event.pos() # 设置旋转基准点为当前鼠标位置
                self.has_rotation_pivot = True # 标记已设置基准点
            # 无修饰符的右键：如果有预选中锚点则切换红色锚点，否则如果有旋转基准点则开始旋转
            elif event.modifiers() == Qt.NoModifier:
                if self.pre_selected_point_index is not None:
                    self.save_state()
                    # 如果锚点已经是红色，则转为白色；如果是白色，则转为红色
                    if self.pre_selected_point_index in self.red_anchors:
                        self.red_anchors.remove(self.pre_selected_point_index)
                    else:
                        self.red_anchors.add(self.pre_selected_point_index)
                    self.update_curve_cache()
                    self.update()
                elif self.has_rotation_pivot: # 确保已设置基准点
                    self.is_rotating_curve = True # 标记开始旋转
                    self.save_state()
                    self.rotation_start_pos = event.pos() # 记录旋转开始时的鼠标位置


        self.update()


    def mouseMoveEvent(self, event):
        self.pre_selected_point_index = None
        min_distance_pre_select = float('inf')
        pre_select_threshold = 10

        if not self.is_ctrl_pressed:
            for i, point in enumerate(self.control_points):
                distance = self.distance(point, event.pos())
                if distance < pre_select_threshold:
                    if distance < min_distance_pre_select:
                        min_distance_pre_select = distance
                        self.pre_selected_point_index = i

        # 2. 存在预选中锚点时 左键拖动锚点 (移动逻辑)
        if self.is_dragging_control_point:
            if self.dragging_point is not None:
                current_idx = self.dragging_point
                
                # 如果拖动的是红色锚点，直接更新位置，不进行投影
                if current_idx in self.red_anchors:
                    self.control_points[current_idx] = event.pos()
                # 如果拖动的是普通锚点
                else:
                    # 无修饰键时，直接更新位置，实现无限制拖动
                    if event.modifiers() == Qt.NoModifier:
                        self.control_points[current_idx] = event.pos()
                    # 如果没有锁定的直线，则使用Shift键的逻辑
                    elif event.modifiers() == Qt.ShiftModifier:
                        # 检查前一个点
                        prev_red_idx = None
                        if current_idx > 0 and (current_idx - 1) in self.red_anchors:
                            prev_red_idx = current_idx - 1

                        # 检查后一个点
                        next_red_idx = None
                        if current_idx < len(self.control_points) - 1 and (current_idx + 1) in self.red_anchors:
                            next_red_idx = current_idx + 1

                        # 如果前后都有红色锚点
                        if prev_red_idx is not None and next_red_idx is not None:
                            # 计算N-2到N-1和N+2到N+1的直线方向向量
                            prev_dir = None
                            next_dir = None
                            
                            # 计算前一条直线方向向量 (N-2到N-1)
                            if prev_red_idx > 0:  # 确保N-2存在
                                prev_dir = self.calculate_direction_vector(prev_red_idx-1, prev_red_idx)
                            else:
                                # 如果N-2不存在，使用N-1的切线方向
                                prev_dir = self.calculate_tangent_line(prev_red_idx)
                                
                            # 计算后一条直线方向向量 (N+2到N+1)
                            if next_red_idx < len(self.control_points) - 1:  # 确保N+2存在
                                next_dir = self.calculate_direction_vector(next_red_idx+1, next_red_idx)
                            else:
                                # 如果N+2不存在，使用N+1的切线方向
                                next_dir = self.calculate_tangent_line(next_red_idx)
                            
                            if prev_dir and next_dir:
                                # 计算两条直线的交点
                                intersection = self.calculate_line_intersection(
                                    self.control_points[prev_red_idx],
                                    prev_dir,
                                    self.control_points[next_red_idx],
                                    next_dir
                                )
                                if intersection:
                                    self.control_points[current_idx] = intersection
                        
                        # 如果只有一个相邻的红色锚点
                        elif (prev_red_idx is not None) != (next_red_idx is not None):
                            red_idx = prev_red_idx if prev_red_idx is not None else next_red_idx
                            # 获取用于确定直线的另一个点
                            projected_point = self.project_point_to_line(
                                event.pos(),
                                self.locked_line_point,
                                self.locked_line_direction
                            )
                            if projected_point:
                                self.control_points[current_idx] = projected_point
                        else:
                            # 如果没有相邻的红色锚点，直接更新位置
                            self.control_points[current_idx] = event.pos()
                    else:
                        # 普通拖动模式，直接更新位置
                        self.control_points[self.dragging_point] = event.pos()
            self.update_curve_cache() # 刷新曲线缓存
            self.update() # 触发重绘

        if self.is_ctrl_dragging_deformation and self.closest_curve_point is not None:
            # Ctrl + 左键拖动：变形曲线 (修改为支持红色锚点分段)
            current_pos = event.pos()
            delta = current_pos - self.drag_start_pos

            t = self.locked_t
            
            # 如果没有红色锚点，按原方式计算整条曲线的影响力
            if not self.red_anchors:
                curve_order = len(self.control_points) - 1
                for i in range(len(self.control_points)):
                    influence = self.bernstein_basis_polynomial(curve_order, i, t)
                    move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                    self.control_points[i] = self.control_points[i] + move_vector
            else:
                # 找出鼠标最近点所在的曲线分段
                min_distance = float('inf')
                closest_idx = -1
                for i, point in enumerate(self.cached_curve_points):
                    distance = self.distance(self.closest_curve_point, point)
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i
                
                # 计算每个分段的曲线点范围
                segments = []
                start_idx = 0
                segment_ranges = []
                start_point_idx = 0
                
                # 按索引排序红色锚点
                sorted_red_anchors = sorted(self.red_anchors)
                
                # 处理所有分段
                for red_idx in sorted_red_anchors:
                    if red_idx > start_idx:  # 确保有足够的点形成一段
                        segments.append((start_idx, red_idx))
                        segment_points = self.control_points[start_idx:red_idx+1]
                        if len(segment_points) >= 2:  # 确保分段至少有两个点
                            segment_point_count = self.curve_segments + 1
                            segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
                            start_point_idx += segment_point_count - 1  # 减1是因为相邻分段的端点重合
                    start_idx = red_idx
                
                # 处理最后一段（最后一个红色锚点到结束）
                if start_idx < len(self.control_points) - 1:
                    segments.append((start_idx, len(self.control_points) - 1))
                    segment_points = self.control_points[start_idx:]
                    if len(segment_points) >= 2:  # 确保分段至少有两个点
                        segment_point_count = self.curve_segments + 1
                        segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
                
                # 根据closest_idx找出所在分段
                current_segment = None
                segment_t = t  # 默认使用全局t值
                
                for i, (start_range, end_range) in enumerate(segment_ranges):
                    if start_range <= closest_idx <= end_range:
                        current_segment = segments[i]
                        # 计算分段内的相对t值
                        segment_length = end_range - start_range
                        if segment_length > 0:
                            segment_t = (closest_idx - start_range) / segment_length
                        break
                
                # 如果找到了所在分段，只计算该分段内锚点的影响力
                if current_segment:
                    segment_start, segment_end = current_segment
                    segment_points = self.control_points[segment_start:segment_end+1]
                    segment_curve_order = len(segment_points) - 1
                    
                    # 只计算当前分段内锚点的影响力并应用变形
                    for i in range(segment_start, segment_end + 1):
                        local_idx = i - segment_start  # 在分段内的索引
                        influence = self.bernstein_basis_polynomial(segment_curve_order, local_idx, segment_t)
                        move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                        self.control_points[i] = self.control_points[i] + move_vector
                else:
                    # 如果找不到所在分段，使用全局方式计算（兜底方案）
                    curve_order = len(self.control_points) - 1
                    for i in range(len(self.control_points)):
                        influence = self.bernstein_basis_polynomial(curve_order, i, t)
                        move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                        self.control_points[i] = self.control_points[i] + move_vector

            self.drag_start_pos = current_pos
            self.update_curve_cache()
            self.update()
            return
        if self.dragging_curve_and_image:
            # Ctrl + 鼠标中键拖动：整体平移曲线和图片 (保持不变)
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()

            for i in range(len(self.control_points)):
                self.control_points[i] += delta

            self.image_offset_x += delta.x()
            self.image_offset_y += delta.y()

            self.update_curve_cache()
            self.update()
            return
        elif self.dragging_curve_only:
            # 鼠标中键拖动：单独平移曲线 (保持不变)
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()

            for i in range(len(self.control_points)):
                self.control_points[i] += delta

            self.update_curve_cache()
            self.update()
            return
        elif self.is_ctrl_dragging_deformation and self.locked_closest_point is not None:
            current_pos = event.pos()
            delta = current_pos - self.drag_start_pos
            t = self.locked_t
            
            # 如果没有红色锚点，按原方式计算整条曲线的影响力
            if not self.red_anchors:
                curve_order = len(self.control_points) - 1
                for i in range(len(self.control_points)):
                    influence = self.bernstein_basis_polynomial(curve_order, i, t)
                    move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                    self.control_points[i] = self.control_points[i] + move_vector
            else:
                # 找出鼠标最近点所在的曲线分段
                min_distance = float('inf')
                closest_idx = -1
                for i, point in enumerate(self.cached_curve_points):
                    distance = self.distance(self.locked_closest_point, point)
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i
                
                # 计算每个分段的曲线点范围
                segments = []
                start_idx = 0
                segment_ranges = []
                start_point_idx = 0
                
                # 按索引排序红色锚点
                sorted_red_anchors = sorted(self.red_anchors)
                
                # 处理所有分段
                for red_idx in sorted_red_anchors:
                    if red_idx > start_idx:  # 确保有足够的点形成一段
                        segments.append((start_idx, red_idx))
                        segment_points = self.control_points[start_idx:red_idx+1]
                        if len(segment_points) >= 2:  # 确保分段至少有两个点
                            segment_point_count = self.curve_segments + 1
                            segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
                            start_point_idx += segment_point_count - 1  # 减1是因为相邻分段的端点重合
                    start_idx = red_idx
                
                # 处理最后一段（最后一个红色锚点到结束）
                if start_idx < len(self.control_points) - 1:
                    segments.append((start_idx, len(self.control_points) - 1))
                    segment_points = self.control_points[start_idx:]
                    if len(segment_points) >= 2:  # 确保分段至少有两个点
                        segment_point_count = self.curve_segments + 1
                        segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
                
                # 根据closest_idx找出所在分段
                current_segment = None
                segment_t = t  # 默认使用全局t值
                
                for i, (start_range, end_range) in enumerate(segment_ranges):
                    if start_range <= closest_idx <= end_range:
                        current_segment = segments[i]
                        # 计算分段内的相对t值
                        segment_length = end_range - start_range
                        if segment_length > 0:
                            segment_t = (closest_idx - start_range) / segment_length
                        break
                
                # 如果找到了所在分段，只计算该分段内锚点的影响力
                if current_segment:
                    segment_start, segment_end = current_segment
                    segment_points = self.control_points[segment_start:segment_end+1]
                    segment_curve_order = len(segment_points) - 1
                    
                    # 只计算当前分段内锚点的影响力并应用变形
                    for i in range(segment_start, segment_end + 1):
                        local_idx = i - segment_start  # 在分段内的索引
                        influence = self.bernstein_basis_polynomial(segment_curve_order, local_idx, segment_t)
                        move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                        self.control_points[i] = self.control_points[i] + move_vector
                else:
                    # 如果找不到所在分段，使用全局方式计算（兜底方案）
                    curve_order = len(self.control_points) - 1
                    for i in range(len(self.control_points)):
                        influence = self.bernstein_basis_polynomial(curve_order, i, t)
                        move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                        self.control_points[i] = self.control_points[i] + move_vector
            
            self.drag_start_pos = current_pos
            self.update_curve_cache()

        # 【新增：曲线旋转的移动逻辑 -  更换为基于拖动距离计算角度, 动态速度】
        if self.is_rotating_curve and self.rotation_pivot_point is not None:
            current_pos = event.pos()
            delta = current_pos - self.rotation_start_pos  # 鼠标拖动向量

            distance = math.sqrt(delta.x()**2 + delta.y()**2) # 计算鼠标拖动距离 (直线距离)
            # 使用 self.rect_height_large 动态设置旋转速度：移动这个距离旋转 360° (2*pi 弧度)
            if self.rect_height_large > 0:
                rotation_angle = (distance / (2 * self.rect_height_large)) * (math.pi)
            else:
                rotation_angle = 0.0 # 避免除以零，如果 rect_height_large 无效则不旋转

            # 判断旋转方向 (根据水平拖动分量决定大致方向)
            if delta.x() < 0:
                rotation_angle = -rotation_angle #  向左拖动时，逆时针旋转 (负角度)

            # 旋转所有控制点 (保持不变)
            rotated_control_points = []
            for point in self.control_points:
                rotated_point = self.rotate_point(point, self.rotation_pivot_point, rotation_angle) # 调用旋转函数
                rotated_control_points.append(rotated_point)
            self.control_points = rotated_control_points # 更新控制点

            self.update_curve_cache() # 刷新曲线缓存
            self.update() # 触发重绘
            return # 旋转时提前返回，避免执行其他移动逻辑

        self.is_ctrl_pressed = bool(event.modifiers() & Qt.ControlModifier)
        self.is_alt_pressed = bool(event.modifiers() & Qt.AltModifier)
        self.is_shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)  # 新增：跟踪 Shift 键状态
        self.update_preview_slider(event)

        ctrl_highlight_threshold = self.outline_width * 0.9 if self.outline_width > 0 else 50
        self.update_ctrl_highlight(event, ctrl_highlight_threshold)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # 停止拖动曲线和图片/或单独拖动曲线 (保持不变)
            self.dragging_curve_only = False
            self.dragging_curve_and_image = False
        elif event.button() == Qt.LeftButton:
            self.is_left_button_pressed = False # 释放左键时，更新状态
            # 2. 存在预选中锚点时 左键拖动锚点 (释放逻辑) (保持不变)
            if self.is_dragging_control_point:
                self.is_dragging_control_point = False
                self.dragging_point = None # 清除拖动锚点索引
                self.update() # 释放鼠标后更新视图
                return # 提前返回，不执行其他释放逻辑
            elif self.is_ctrl_dragging_deformation:
                self.is_ctrl_dragging_deformation = False # 停止 曲线变形 拖动
                self.drag_start_pos = None # 清空拖动起始位置
                self.locked_closest_point = None
                self.locked_t = None  # 清理 locked_t
                self.update()
                return # 提前返回，避免执行其他释放逻辑

        elif event.button() == Qt.RightButton:
            self.is_right_button_pressed = False # 释放右键时，更新状态
            # 【新增：停止曲线旋转】
            self.is_rotating_curve = False # 停止旋转
            self.rotation_start_pos = None # 清空旋转起始位置

            self.dragging_point = None
            self.is_dragging_control_point = False
            self.is_ctrl_dragging_deformation = False
            self.drag_start_pos = None
            self.locked_closest_point = None
            self.locked_t = None
            self.update()

    def rotate_point(self, point, pivot, angle_radians):
        """绕基准点旋转点的函数"""
        dx = point.x() - pivot.x()
        dy = point.y() - pivot.y()
        rotated_x = dx * math.cos(angle_radians) - dy * math.sin(angle_radians) + pivot.x()
        rotated_y = dx * math.sin(angle_radians) + dy * math.cos(angle_radians) + pivot.y()
        return QPoint(int(rotated_x), int(rotated_y))
        
    def calculate_point_on_line(self, line_point1, line_point2, distance_from_point1):
        """计算直线上距离起点特定距离的点"""
        if line_point1 == line_point2:  # 避免除以零错误
            return QPoint(line_point1)
            
        # 计算方向向量
        direction = QPoint(line_point2.x() - line_point1.x(), line_point2.y() - line_point1.y())
        
        # 计算向量长度
        length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
        
        # 归一化方向向量
        if length > 0:
            normalized_direction = QPoint(int(direction.x() / length), int(direction.y() / length))
        else:
            return QPoint(line_point1)  # 避免除以零
        
        # 计算目标点坐标
        result_x = line_point1.x() + normalized_direction.x() * distance_from_point1
        result_y = line_point1.y() + normalized_direction.y() * distance_from_point1
        
        return QPoint(int(result_x), int(result_y))

    def delete_control_point_by_index(self, index):
        if 0 <= index < len(self.control_points):
            if len(self.control_points) <= 2:
                # 弹出提示窗口
                msg = QMessageBox(self)
                msg.setWindowTitle(self.msg_title_prompt)
                msg.setText(self.delete_control_point_msg)
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                return  # 禁止删除，直接返回
                
            self.save_state()
            
            # 删除红色锚点（如果当前点是红色锚点）
            if index in self.red_anchors:
                self.red_anchors.remove(index)
            
            # 更新其他红色锚点的索引
            updated_red_anchors = set()
            for idx in self.red_anchors:
                if idx > index:
                    updated_red_anchors.add(idx - 1)  # 删除点后的红色锚点索引-1
                elif idx < index:
                    updated_red_anchors.add(idx)  # 删除点前的红色锚点索引不变
            self.red_anchors = updated_red_anchors
            
            del self.control_points[index]
            
            # 同步更新高亮索引
            if self.highlighted_segment_index is not None and self.highlighted_segment_index >= index:
                if self.highlighted_segment_index > 0:
                    self.highlighted_segment_index -= 1
                else:
                    self.highlighted_segment_index = None
            if self.pre_selected_point_index is not None:
                if index < self.pre_selected_point_index:
                    self.pre_selected_point_index -= 1
                elif index == self.pre_selected_point_index:
                    self.pre_selected_point_index = None
                    
            self.update_curve_cache()
            self.update()

    def delete_control_point(self, pos):
        point_to_delete_index = None
        min_distance = float('inf')
        delete_threshold = 10

        for i, point in enumerate(self.control_points):
            distance = self.distance(point, pos)
            if distance < delete_threshold and distance < min_distance:
                min_distance = distance
                point_to_delete_index = i

        if point_to_delete_index is not None:
            self.save_state()
            del self.control_points[point_to_delete_index]
            self.update_curve_cache()
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
        """刷新贝塞尔曲线缓存，支持红色锚点和曲线分段"""
        if len(self.control_points) >= 2:
            self.cached_curve_points = []
            
            # 如果没有红色锚点，按原方式计算整条曲线
            if not self.red_anchors:
                for t in range(0, self.curve_segments + 1):
                    t_normalized = t / self.curve_segments
                    point = self.calculate_bezier_point(t_normalized, self.control_points)
                    self.cached_curve_points.append(point)
            else:
                # 按照红色锚点分段计算曲线
                # 首先将控制点按照红色锚点分段
                segments = []
                start_idx = 0
                
                # 按索引排序红色锚点
                sorted_red_anchors = sorted(self.red_anchors)
                
                # 处理所有分段
                for red_idx in sorted_red_anchors:
                    if red_idx > start_idx:  # 确保有足够的点形成一段
                        segments.append(self.control_points[start_idx:red_idx+1])
                    start_idx = red_idx
                
                # 处理最后一段（最后一个红色锚点到结束）
                if start_idx < len(self.control_points) - 1:
                    segments.append(self.control_points[start_idx:])
                
                # 为每个分段计算贝塞尔曲线点
                for segment in segments:
                    if len(segment) >= 2:  # 确保分段至少有两个点
                        # 计算当前分段的曲线点
                        segment_points = []
                        for t in range(0, self.curve_segments + 1):
                            t_normalized = t / self.curve_segments
                            point = self.calculate_bezier_point(t_normalized, segment)
                            segment_points.append(point)
                        
                        # 如果不是第一段，移除第一个点以避免重复
                        if self.cached_curve_points and segment_points:
                            segment_points = segment_points[1:]
                            
                        # 将当前分段的点添加到缓存中
                        self.cached_curve_points.extend(segment_points)
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
            
            # 更新红色锚点索引，考虑插入新点后的索引变化
            updated_red_anchors = set()
            for idx in self.red_anchors:
                if idx >= insert_segment_index:
                    updated_red_anchors.add(idx + 1)  # 插入点后的红色锚点索引+1
                else:
                    updated_red_anchors.add(idx)  # 插入点前的红色锚点索引不变
            self.red_anchors = updated_red_anchors
            
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
                
                # 删除红色锚点（如果当前点是红色锚点）
                if i in self.red_anchors:
                    self.red_anchors.remove(i)
                
                # 更新其他红色锚点的索引
                updated_red_anchors = set()
                for idx in self.red_anchors:
                    if idx > i:
                        updated_red_anchors.add(idx - 1)  # 删除点后的红色锚点索引-1
                    elif idx < i:
                        updated_red_anchors.add(idx)  # 删除点前的红色锚点索引不变
                self.red_anchors = updated_red_anchors
                
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
        """更新 Ctrl 键高亮功能：计算最近点和锚点影响力，支持红色锚点分段"""
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
                
                # 如果没有红色锚点，按原方式计算影响力
                if not self.red_anchors:
                    curve_order = len(self.control_points) - 1
                    for i in range(len(self.control_points)):
                        influence = self.bernstein_basis_polynomial(curve_order, i, t)
                        self.anchor_influences.append(influence)
                else:
                    # 按照红色锚点分段计算影响力
                    # 首先找出鼠标所在的曲线分段
                    segments = []
                    start_idx = 0
                    
                    # 按索引排序红色锚点
                    sorted_red_anchors = sorted(self.red_anchors)
                    
                    # 处理所有分段
                    for red_idx in sorted_red_anchors:
                        if red_idx > start_idx:  # 确保有足够的点形成一段
                            segments.append((start_idx, red_idx))
                        start_idx = red_idx
                    
                    # 处理最后一段（最后一个红色锚点到结束）
                    if start_idx < len(self.control_points) - 1:
                        segments.append((start_idx, len(self.control_points) - 1))
                    
                    # 找出鼠标最近点所在的分段
                    current_segment = None
                    segment_t = t  # 默认使用全局t值
                    
                    # 计算每个分段的曲线点范围
                    segment_ranges = []
                    start_point_idx = 0
                    
                    for segment_start, segment_end in segments:
                        segment_points = self.control_points[segment_start:segment_end+1]
                        if len(segment_points) >= 2:  # 确保分段至少有两个点
                            segment_point_count = self.curve_segments + 1
                            segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
                            start_point_idx += segment_point_count - 1  # 减1是因为相邻分段的端点重合
                    
                    # 根据closest_idx找出所在分段
                    for i, (start_range, end_range) in enumerate(segment_ranges):
                        if start_range <= closest_idx <= end_range:
                            current_segment = segments[i]
                            # 计算分段内的相对t值
                            segment_length = end_range - start_range
                            if segment_length > 0:
                                segment_t = (closest_idx - start_range) / segment_length
                            break
                    
                    # 初始化所有锚点的影响力为0
                    self.anchor_influences = [0.0] * len(self.control_points)
                    
                    # 如果找到了所在分段，计算该分段内锚点的影响力
                    if current_segment:
                        segment_start, segment_end = current_segment
                        segment_points = self.control_points[segment_start:segment_end+1]
                        segment_curve_order = len(segment_points) - 1
                        
                        # 只计算当前分段内锚点的影响力
                        for i in range(segment_start, segment_end + 1):
                            local_idx = i - segment_start  # 在分段内的索引
                            influence = self.bernstein_basis_polynomial(segment_curve_order, local_idx, segment_t)
                            self.anchor_influences[i] = influence
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
                max_influence = max(self.anchor_influences) if self.anchor_influences and max(self.anchor_influences) > 0 else 1.0
                
                # 安全地获取最大影响力点的索引
                try:
                    max_influence_idx = self.anchor_influences.index(max_influence)  # 最大影响力点的索引
                except ValueError:
                    # 如果找不到最大影响力值（可能在红色锚点分段计算中出现），使用默认值
                    max_influence_idx = 0
                
                # 存储筛选出的锚点信息
                anchor_data = []

                for i, influence in enumerate(self.anchor_influences):
                    if i < len(self.control_points):  # 确保索引在有效范围内
                        normalized_influence = influence / max_influence if max_influence > 0 else 0
                        radius = 4 + 9 * (normalized_influence) ** 3  # 半径 4-12
                        alpha = normalized_influence  # 透明度 0.2-1.0
                        pen_width = 6 * normalized_influence  # 描边粗细 1-3
                    
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
        
        # 绘制左侧面板背景
        painter.fillRect(0, 0, 80, self.height(), QColor("#262626"))
        
        # 不再绘制右侧绘图区域背景，避免覆盖曲线
        painter.fillRect(80, 0, self.width() - 80, self.height(), QColor("#202020"))

        # 计算窗口中心 - 考虑左侧面板的宽度
        # center_x = (self.width() - 80) // 2 + 80
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

        # 绘制控制线
        painter.setOpacity(0.1 if self.is_alt_pressed or self.is_ctrl_pressed or self.is_left_button_pressed or self.pre_selected_point_index is not None else 0.6)
        painter.setPen(QPen(QColor("#FFFFFF"), 1, Qt.DashLine))
        for i in range(len(self.control_points) - 1):
            painter.drawLine(self.control_points[i], self.control_points[i + 1])
        painter.setOpacity(1.0) # 恢复透明度
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

        # 绘制控制点
        painter.setOpacity(1.0)
        for i, point in enumerate(self.control_points):
            # 根据锚点类型设置颜色（红色锚点或白色锚点）
            if i in self.red_anchors:
                painter.setPen(QPen(QColor("#FF0000"), 4))  # 红色锚点
                painter.drawEllipse(point, 4, 4)
                
                # 当Shift按下且鼠标悬停在红锚点上时，显示切线方向
                if self.is_shift_pressed and i == self.pre_selected_point_index:
                    tangent_dir = self.calculate_tangent_line(i)
                    if tangent_dir:
                        # 绘制长度为20的绿色线段表示切线方向
                        line_length = 200
                        start_x = point.x() - tangent_dir[0] * line_length
                        start_y = point.y() - tangent_dir[1] * line_length
                        end_x = point.x() + tangent_dir[0] * line_length
                        end_y = point.y() + tangent_dir[1] * line_length
                        painter.setPen(QPen(QColor("#00FF00"), 3, Qt.DashLine))  # 绿色线段
                        painter.drawLine(QPoint(int(start_x), int(start_y)), QPoint(int(end_x), int(end_y)))
            else:
                painter.setPen(QPen(QColor("#FFFFFF"), 5))  # 白色锚点
                
                # 当Shift按下且鼠标悬停在白锚点上时，显示可移动直线
                if self.is_shift_pressed and i == self.pre_selected_point_index:
                    # 使用统一的函数计算并绘制锚点直线
                    self.calculate_and_draw_anchor_lines(painter, i, point)
            
            painter.drawPoint(point)
            if i == self.pre_selected_point_index:
                painter.save()  # 保存当前画笔状态
                # 根据不同状态设置预选圆圈颜色
                if self.is_shift_pressed:
                    ring_color = QColor("#00FF00")  # Shift按下时为绿色
                elif self.is_alt_pressed:
                    ring_color = QColor("#FF0000")  # Alt按下时为红色
                else:
                    ring_color = QColor("#FFFF00")  # 默认为黄色
                    
                pre_select_ring_pen = QPen(ring_color, 3) # 线宽为 3
                painter.setPen(pre_select_ring_pen)
                painter.setBrush(Qt.NoBrush) # 空心圆环
                ring_inner_radius = 4 # 内径为 4
                ring_outer_radius = 8 # 外径为 8
                painter.drawEllipse(point, ring_outer_radius, ring_outer_radius) # 绘制外圆
                painter.drawEllipse(point, ring_inner_radius, ring_inner_radius) # 绘制内圆 (覆盖中心区域，形成空心)
                painter.restore()  # 恢复画笔状态

        # 绘制全局贝塞尔曲线（蓝色实线）
        if self.cached_curve_points:
            path = QPainterPath()
            path.moveTo(self.cached_curve_points[0])
            for point in self.cached_curve_points[1:]:
                path.lineTo(point)
            painter.setPen(QPen(QColor("#0000FF"), 2))
            painter.drawPath(path)

        if self.is_visualization_enabled: #  <--  新增：总开关，控制可视化效果是否绘制
            if not self.is_alt_pressed and not self.is_ctrl_pressed and not self.is_shift_pressed: # 非 Alt 状态下
                # 绘制影响力权重染色
                painter.setOpacity(0.1 if self.is_left_button_pressed else 0.5) # 设置染色层的整体透明度
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

        # 【新增：绘制旋转基准点】
        if self.has_rotation_pivot and (self.is_alt_pressed or self.is_right_button_pressed): # Alt 或 右键按下时显示
            painter.setPen(QPen(Qt.green, 2)) # 绿色画笔
            pivot_x, pivot_y = self.rotation_pivot_point.x(), self.rotation_pivot_point.y()
            cross_size = 10 # 十字大小
            painter.drawLine(pivot_x - cross_size, pivot_y, pivot_x + cross_size, pivot_y) # 横线
            painter.drawLine(pivot_x, pivot_y - cross_size, pivot_x, pivot_y + cross_size) # 竖线


        # 在窗口底部中间显示滑条长度信息
        if self.cached_curve_points and len(self.cached_curve_points) > 1 and self.initial_slider_length > 0:
            self.current_slider_length = self.calculate_curve_length()
            ratio = int(self.current_slider_length) / int(self.initial_slider_length)
            length_text = f"{ratio:.2f}x"
            
            # 设置字体和计算文本尺寸
            painter.setFont(QApplication.font())
            metrics = painter.fontMetrics()
            title_text = self.msg_slider_length_ratio
            title_width = metrics.width(title_text)
            value_width = metrics.width(length_text)
            text_height = metrics.height()
            padding = 8
            
            # 计算按钮尺寸和样式
            button_size = 34
            circle_button_style = """
                QPushButton {
                    background-color: #ff8a9b;
                    border-radius: 15px;
                    width: 34px;
                    height: 34px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #8a42ad;
                }
                QPushButton:pressed {
                    background-color: #181D28;
                }
            """
            
            # 创建重设初始长度按钮
            if not hasattr(self, 'reset_length_button'):
                self.reset_length_button = QPushButton(self)
                self.reset_length_button.setStyleSheet(circle_button_style)
                self.reset_length_button.setFixedSize(button_size, button_size)
                self.reset_length_button.clicked.connect(self.reset_initial_length)
                self.reset_length_button.setToolTip("重设初始长度")
                self.reset_length_button.setIcon(QIcon("icons/reset_length.svg"))
                self.reset_length_button.setIconSize(QSize(24, 24))
            
            # 创建缩放到初始长度按钮
            if not hasattr(self, 'scale_to_initial_button'):
                self.scale_to_initial_button = QPushButton(self)
                self.scale_to_initial_button.setStyleSheet(circle_button_style)
                self.scale_to_initial_button.setFixedSize(button_size, button_size)
                self.scale_to_initial_button.clicked.connect(self.scale_to_initial_length)
                self.scale_to_initial_button.setToolTip("缩放至初始长度")
                self.scale_to_initial_button.setIcon(QIcon("icons/scale_length.svg"))
                self.scale_to_initial_button.setIconSize(QSize(24, 24))
            
            # 计算背景矩形的尺寸和位置 - 移动到左下角
            rect_x = 90  # 左侧面板宽度为80，稍微偏移一点            
            text_x = rect_x + button_size * 2 + padding * 2  # 文字位置从两个按钮后开始
            total_width = button_size * 2 + padding * 3 + max(title_width, value_width) + 12
            total_height = max(text_height * 2 + padding * 2, button_size + padding * 2)

            rect_y = self.height() - total_height - 10
            
            # 更新按钮位置
            button_y = rect_y + (total_height - button_size) // 2
            self.reset_length_button.move(rect_x + padding, button_y)
            self.scale_to_initial_button.move(rect_x + button_size + padding * 2, button_y)
            
            # 确保按钮可见
            self.reset_length_button.setVisible(True)
            self.scale_to_initial_button.setVisible(True)
            
            # 绘制圆角矩形背景
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(30, 30, 30, 150))
            painter.drawRoundedRect(rect_x, rect_y, total_width, total_height, 10, 10)
            
            # 绘制文本 - 左对齐
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_x + 9, rect_y + padding + text_height + 4, title_text)
            painter.drawText(text_x + 9, rect_y + padding + text_height * 2 + 4, length_text)

        painter.end()

    def draw_influence_weights(self, painter):
        """绘制影响力权重染色（黄色圆圈），支持红色锚点分段"""
        if self.pre_selected_point_index is None:
            return
            
        # 如果所选锚点是第一个、最后一个或红色锚点，不进行权重可视化绘制
        if (self.pre_selected_point_index == 0 or 
            self.pre_selected_point_index == len(self.control_points) - 1 or 
            self.pre_selected_point_index in self.red_anchors):
            return

        influence_color = QColor("#FFFF00")
        dragged_point_index = self.pre_selected_point_index
        
        # 初始化变量，避免引用前未定义的错误
        current_segment = None
        current_segment_range = None
        segment_influence_weights = []
        
        # 如果没有红色锚点，按原方式计算影响力权重
        if not self.red_anchors:
            curve_order = len(self.control_points) - 1
            
            # 计算每段影响力权重
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
        else:
            # 按照红色锚点分段计算影响力权重
            segments = []
            start_idx = 0
            segment_ranges = []
            start_point_idx = 0
            
            # 按索引排序红色锚点
            sorted_red_anchors = sorted(self.red_anchors)
            
            # 处理所有分段
            for red_idx in sorted_red_anchors:
                if red_idx > start_idx:  # 确保有足够的点形成一段
                    segments.append((start_idx, red_idx))
                    segment_points = self.control_points[start_idx:red_idx+1]
                    if len(segment_points) >= 2:  # 确保分段至少有两个点
                        segment_point_count = self.curve_segments + 1
                        segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
                        start_point_idx += segment_point_count - 1  # 减1是因为相邻分段的端点重合
                start_idx = red_idx
            
            # 处理最后一段（最后一个红色锚点到结束）
            if start_idx < len(self.control_points) - 1:
                segments.append((start_idx, len(self.control_points) - 1))
                segment_points = self.control_points[start_idx:]
                if len(segment_points) >= 2:  # 确保分段至少有两个点
                    segment_point_count = self.curve_segments + 1
                    segment_ranges.append((start_point_idx, start_point_idx + segment_point_count - 1))
            
            # 初始化影响力权重列表，与缓存曲线点数量一致
            total_points = len(self.cached_curve_points) if self.cached_curve_points else self.curve_segments
            for t in range(0, total_points):
                segment_influence_weights.append({'index': t, 'weight': 0.0})
            
            # 找出拖动点所在的分段
            found_segment = False
            for i, (start, end) in enumerate(segments):
                if start <= dragged_point_index <= end:
                    current_segment = (start, end)
                    if i < len(segment_ranges):
                        current_segment_range = segment_ranges[i]
                    found_segment = True
                    break
            
            # 如果找到了拖动点所在的分段，计算该分段的影响力权重
            if found_segment and current_segment and current_segment_range:
                segment_start, segment_end = current_segment
                range_start, range_end = current_segment_range
                segment_points = self.control_points[segment_start:segment_end+1]
                segment_curve_order = len(segment_points) - 1
                segment_dragged_index = dragged_point_index - segment_start
                
                # 只计算当前分段内的曲线点的影响力权重
                for t in range(0, total_points):
                    # 检查当前点是否在当前分段范围内
                    if range_start <= t <= range_end:
                        local_t = (t - range_start) / (range_end - range_start) if range_end > range_start else 0
                        
                        if segment_dragged_index == 0:
                            t_value_for_weight = local_t * 0.1  # 靠近起点
                        elif segment_dragged_index == len(segment_points) - 1:
                            t_value_for_weight = 0.9 + local_t * 0.1  # 靠近终点
                        else:
                            t_value_for_weight = local_t
                        
                        # 只计算当前分段内的影响力权重
                        if 0 <= segment_dragged_index <= segment_curve_order:
                            influence_weight = self.bernstein_basis_polynomial(segment_curve_order, segment_dragged_index, t_value_for_weight)
                            # 将计算的权重值赋给对应的曲线点
                            segment_influence_weights[t]['weight'] = influence_weight
        
        # 确保segment_influence_weights不为空
        if not segment_influence_weights:
            return
            
        # 找出最大影响力权重，用于归一化
        max_influence_weight = max(segment['weight'] for segment in segment_influence_weights) if segment_influence_weights else 0
        
        # 如果没有有效的影响力权重，直接返回
        if max_influence_weight <= 0:
            return

        # 绘制染色圆圈 - 修改为绘制所有曲线点
        if self.cached_curve_points:
            # 新增：确保绘制所有曲线点，而不仅仅是当前分段
            for t in range(len(self.cached_curve_points)):
                if t < len(segment_influence_weights):
                    influence_weight = segment_influence_weights[t]['weight']
                    normalized_influence_weight = influence_weight / max_influence_weight

                    # 只绘制有影响力的点（优化性能）
                    if normalized_influence_weight > 0.01:
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
                        
                        # 使用缓存的曲线点
                        point_mid = self.cached_curve_points[t]
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
                
                # 如果没有红色锚点，按原方式计算预览曲线
                if not self.red_anchors:
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
                    # 按照红色锚点分段计算预览曲线
                    # 更新红色锚点索引，考虑插入新点后的索引变化
                    preview_red_anchors = set()
                    for idx in self.red_anchors:
                        if idx >= insert_index:
                            preview_red_anchors.add(idx + 1)  # 插入点后的红色锚点索引+1
                        else:
                            preview_red_anchors.add(idx)  # 插入点前的红色锚点索引不变
                    
                    # 首先将控制点按照红色锚点分段
                    segments = []
                    start_idx = 0
                    
                    # 按索引排序红色锚点
                    sorted_red_anchors = sorted(preview_red_anchors)
                    
                    # 处理所有分段
                    for red_idx in sorted_red_anchors:
                        if red_idx > start_idx:  # 确保有足够的点形成一段
                            segments.append(preview_control_points[start_idx:red_idx+1])
                        start_idx = red_idx
                    
                    # 处理最后一段（最后一个红色锚点到结束）
                    if start_idx < len(preview_control_points) - 1:
                        segments.append(preview_control_points[start_idx:])
                    
                    # 为每个分段计算贝塞尔曲线点
                    for segment in segments:
                        if len(segment) >= 2:  # 确保分段至少有两个点
                            # 计算当前分段的曲线点
                            segment_points = []
                            for t in range(0, self.curve_segments + 1):
                                t_normalized = t / self.curve_segments
                                point = self.calculate_bezier_point(t_normalized, segment)
                                segment_points.append(point)
                            
                            # 如果不是第一段，移除第一个点以避免重复
                            if self.preview_slider_points and segment_points:
                                segment_points = segment_points[1:]
                                
                            # 将当前分段的点添加到预览曲线中
                            self.preview_slider_points.extend(segment_points)
                    
                    # 计算与原始曲线的偏移量
                    for i, point in enumerate(self.preview_slider_points):
                        if self.cached_curve_points and i < len(self.cached_curve_points):
                            orig_point = self.cached_curve_points[i]
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
                
                # 更新红色锚点索引，考虑删除点后的索引变化
                preview_red_anchors = set()
                for idx in self.red_anchors:
                    if idx == self.pre_selected_point_index:
                        # 如果删除的是红色锚点，不添加到新集合中
                        continue
                    elif idx > self.pre_selected_point_index:
                        # 删除点后的红色锚点索引-1
                        preview_red_anchors.add(idx - 1)
                    else:
                        # 删除点前的红色锚点索引不变
                        preview_red_anchors.add(idx)
                
                # 删除预选锚点
                preview_control_points.pop(self.pre_selected_point_index)
                
                self.preview_slider_points = []
                self.preview_offsets = []
                
                # 如果没有红色锚点，按原方式计算预览曲线
                if not preview_red_anchors:
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
                    # 按照红色锚点分段计算预览曲线
                    # 首先将控制点按照红色锚点分段
                    segments = []
                    start_idx = 0
                    
                    # 按索引排序红色锚点
                    sorted_red_anchors = sorted(preview_red_anchors)
                    
                    # 处理所有分段
                    for red_idx in sorted_red_anchors:
                        if red_idx > start_idx:  # 确保有足够的点形成一段
                            segments.append(preview_control_points[start_idx:red_idx+1])
                        start_idx = red_idx
                    
                    # 处理最后一段（最后一个红色锚点到结束）
                    if start_idx < len(preview_control_points) - 1:
                        segments.append(preview_control_points[start_idx:])
                    
                    # 为每个分段计算贝塞尔曲线点
                    for segment in segments:
                        if len(segment) >= 2:  # 确保分段至少有两个点
                            # 计算当前分段的曲线点
                            segment_points = []
                            for t in range(0, self.curve_segments + 1):
                                t_normalized = t / self.curve_segments
                                point = self.calculate_bezier_point(t_normalized, segment)
                                segment_points.append(point)
                            
                            # 如果不是第一段，移除第一个点以避免重复
                            if self.preview_slider_points and segment_points:
                                segment_points = segment_points[1:]
                                
                            # 将当前分段的点添加到预览曲线中
                            self.preview_slider_points.extend(segment_points)
                    
                    # 计算与原始曲线的偏移量
                    for i, point in enumerate(self.preview_slider_points):
                        if self.cached_curve_points and i < len(self.cached_curve_points):
                            orig_point = self.cached_curve_points[i]
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
                
                # 如果没有红色锚点，按原方式计算预览曲线
                if not self.red_anchors:
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
                    # 更新红色锚点索引，考虑插入新点后的索引变化
                    preview_red_anchors = set()
                    for idx in self.red_anchors:
                        if idx >= self.preview_segment_index:
                            preview_red_anchors.add(idx + 1)  # 插入点后的红色锚点索引+1
                        else:
                            preview_red_anchors.add(idx)  # 插入点前的红色锚点索引不变
                    
                    # 按照红色锚点分段计算预览曲线
                    # 首先将控制点按照红色锚点分段
                    segments = []
                    start_idx = 0
                    
                    # 按索引排序红色锚点
                    sorted_red_anchors = sorted(preview_red_anchors)
                    
                    # 处理所有分段
                    for red_idx in sorted_red_anchors:
                        if red_idx > start_idx:  # 确保有足够的点形成一段
                            segments.append(preview_control_points[start_idx:red_idx+1])
                        start_idx = red_idx
                    
                    # 处理最后一段（最后一个红色锚点到结束）
                    if start_idx < len(preview_control_points) - 1:
                        segments.append(preview_control_points[start_idx:])
                    
                    # 为每个分段计算贝塞尔曲线点
                    for segment in segments:
                        if len(segment) >= 2:  # 确保分段至少有两个点
                            # 计算当前分段的曲线点
                            segment_points = []
                            for t in range(0, self.curve_segments + 1):
                                t_normalized = t / self.curve_segments
                                point = self.calculate_bezier_point(t_normalized, segment)
                                segment_points.append(point)
                            
                            # 如果不是第一段，移除第一个点以避免重复
                            if self.preview_slider_points and segment_points:
                                segment_points = segment_points[1:]
                                
                            # 将当前分段的点添加到预览曲线中
                            self.preview_slider_points.extend(segment_points)
                    
                    # 计算与原始曲线的偏移量
                    for i, point in enumerate(self.preview_slider_points):
                        if self.cached_curve_points and i < len(self.cached_curve_points):
                            orig_point = self.cached_curve_points[i]
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

    def calculate_tangent_line(self, point_idx):
        """计算指定锚点处的切线方向向量"""
        if point_idx < 0 or point_idx >= len(self.control_points):
            return None
        
        # 如果是端点，使用相邻点确定方向
        if point_idx == 0:
            if len(self.control_points) > 1:
                dx = self.control_points[1].x() - self.control_points[0].x()
                dy = self.control_points[1].y() - self.control_points[0].y()
            else:
                return None
        elif point_idx == len(self.control_points) - 1:
            if len(self.control_points) > 1:
                dx = self.control_points[-1].x() - self.control_points[-2].x()
                dy = self.control_points[-1].y() - self.control_points[-2].y()
            else:
                return None
        else:
            # 对于中间点，使用前后点确定切线方向
            dx = self.control_points[point_idx + 1].x() - self.control_points[point_idx - 1].x()
            dy = self.control_points[point_idx + 1].y() - self.control_points[point_idx - 1].y()
        
        # 归一化方向向量
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            return dx/length, dy/length
        return None
        
    def calculate_direction_vector(self, from_idx, to_idx):
        """计算从from_idx到to_idx的方向向量"""
        if from_idx < 0 or from_idx >= len(self.control_points) or to_idx < 0 or to_idx >= len(self.control_points):
            return None
            
        # 计算方向向量
        dx = self.control_points[to_idx].x() - self.control_points[from_idx].x()
        dy = self.control_points[to_idx].y() - self.control_points[from_idx].y()
        
        # 归一化方向向量
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            return dx/length, dy/length
        return None

    def project_point_to_line(self, point, line_point, line_direction):
        """将点投影到直线上
        point: 要投影的点
        line_point: 直线上的一点
        line_direction: 直线的方向向量(已归一化)"""
        if not line_direction:
            return None
        
        # 计算点到直线上点的向量
        dx = point.x() - line_point.x()
        dy = point.y() - line_point.y()
        
        # 计算投影长度
        proj_length = dx * line_direction[0] + dy * line_direction[1]
        
        # 计算投影点坐标
        proj_x = line_point.x() + proj_length * line_direction[0]
        proj_y = line_point.y() + proj_length * line_direction[1]
        
        return QPoint(int(proj_x), int(proj_y))
        
    def calculate_and_draw_anchor_lines(self, painter, anchor_idx, anchor_point):
        """计算并绘制锚点可移动的直线
        painter: QPainter对象
        anchor_idx: 锚点索引
        anchor_point: 锚点位置"""
        # 检查前后是否有红色锚点
        prev_red_idx = None
        next_red_idx = None
        
        # 仅检查相邻的前一个点是否为红锚点
        if anchor_idx > 0 and (anchor_idx - 1) in self.red_anchors:
            prev_red_idx = anchor_idx - 1
            
        # 仅检查相邻的后一个点是否为红锚点
        if anchor_idx < len(self.control_points) - 1 and (anchor_idx + 1) in self.red_anchors:
            next_red_idx = anchor_idx + 1
        
        # 如果前后都有红色锚点
        if prev_red_idx is not None and next_red_idx is not None:
            # 计算N-2到N-1和N+2到N+1的直线方向向量
            prev_dir = None
            next_dir = None
            
            # 计算前一条直线方向向量 (N-2到N-1)
            if prev_red_idx > 0:  # 确保N-2存在
                prev_dir = self.calculate_direction_vector(prev_red_idx-1, prev_red_idx)
            else:
                # 如果N-2不存在，使用N-1的切线方向
                prev_dir = self.calculate_tangent_line(prev_red_idx)
                
            # 计算后一条直线方向向量 (N+2到N+1)
            if next_red_idx < len(self.control_points) - 1:  # 确保N+2存在
                next_dir = self.calculate_direction_vector(next_red_idx+1, next_red_idx)
            else:
                # 如果N+2不存在，使用N+1的切线方向
                next_dir = self.calculate_tangent_line(next_red_idx)
            
            if prev_dir and next_dir:
                # 计算两个方向向量的夹角（弧度）
                dot_product = prev_dir[0] * next_dir[0] + prev_dir[1] * next_dir[1]
                angle_rad = math.acos(max(-1.0, min(1.0, dot_product)))
                angle_deg = math.degrees(angle_rad)
                
                # 如果夹角大于30度，绘制两条直线的交点
                if angle_deg > 30:
                    # 计算两条直线的交点
                    intersection = self.calculate_line_intersection(
                        self.control_points[prev_red_idx],
                        prev_dir,
                        self.control_points[next_red_idx],
                        next_dir
                    )
                    
                    if intersection:
                        # 绘制从N-1点到焦点的直线
                        painter.setPen(QPen(QColor("#00FF00"), 2, Qt.DashLine))  # 绿色虚线
                        painter.drawLine(self.control_points[prev_red_idx], intersection)
                        
                        # 绘制从N+1点到焦点的直线
                        painter.setPen(QPen(QColor("#00FF00"), 2, Qt.DashLine))  # 绿色虚线
                        painter.drawLine(self.control_points[next_red_idx], intersection)
                        
                        # 绘制交点（小圆点）
                        painter.setPen(QPen(QColor("#00FF00"), 7))  # 绿色点
                        painter.drawPoint(intersection)
                # 如果夹角小于等于30度，不绘制任何内容
                # else:
                #     # 这里不再绘制任何内容
        
        # 如果只有一个相邻的红色锚点
        elif prev_red_idx is not None or next_red_idx is not None:
            red_idx = prev_red_idx if prev_red_idx is not None else next_red_idx
            red_point = self.control_points[red_idx]
            
            # 计算从红色锚点到当前锚点的方向向量
            dx = anchor_point.x() - red_point.x()
            dy = anchor_point.y() - red_point.y()
            length = math.sqrt(dx * dx + dy * dy)
            
            if length > 0:
                # 归一化方向向量
                dir_vector = (dx/length, dy/length)
                
                # 计算足够长的直线长度（窗口对角线长度的2倍）
                window_diagonal = math.sqrt(self.width() * self.width() + self.height() * self.height())
                line_length = window_diagonal * 2
                
                # 计算直线的起点和终点
                start_x = anchor_point.x() - dir_vector[0] * line_length
                start_y = anchor_point.y() - dir_vector[1] * line_length
                end_x = anchor_point.x() + dir_vector[0] * line_length
                end_y = anchor_point.y() + dir_vector[1] * line_length
                
                # 绘制直线
                painter.setPen(QPen(QColor("#00FF00"), 2, Qt.DashLine))  # 绿色虚线
                painter.drawLine(QPoint(int(start_x), int(start_y)), QPoint(int(end_x), int(end_y)))

    def calculate_line_intersection(self, p1, dir1, p2, dir2):
        """计算两条直线的交点
        p1, p2: 两条直线上的点
        dir1, dir2: 两条直线的方向向量(已归一化)"""
        if not dir1 or not dir2:
            return None
            
        # 计算两个方向向量的点积，用于判断夹角
        dot_product = dir1[0]*dir2[0] + dir1[1]*dir2[1]
        # 计算夹角的余弦值，两向量都已归一化，所以点积就是余弦值
        cos_angle = abs(dot_product)
        # 当夹角小于30度时（cos值大于0.866），认为两线几乎平行，避免计算不稳定
        if cos_angle > 0.866:  # cos(30°) ≈ 0.866
            return None
            
        # 使用参数方程求解
        # L1: p1 + t*dir1 = L2: p2 + s*dir2
        denominator = dir1[0]*dir2[1] - dir1[1]*dir2[0]
        if abs(denominator) < 1e-10:  # 平行或重合
            return None
            
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        t = (dx*dir2[1] - dy*dir2[0]) / denominator
        
        # 计算交点
        intersect_x = p1.x() + t * dir1[0]
        intersect_y = p1.y() + t * dir1[1]
        
        return QPoint(int(intersect_x), int(intersect_y))

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
        red_anchors_to_save = copy.deepcopy(self.red_anchors)  # 保存红色锚点信息
        self.history.append((state_to_save, red_anchors_to_save))  # 保存为元组
        self.future.clear()
        
        self.backup_counter += 1 # 更新计数器并检查是否备份
        if self.backup_counter >= self.backup_threshold:
            self.auto_backup()
            self.backup_counter = 0  # 重置计数器

    def auto_backup(self):
        """自动备份当前状态"""
        backup_data = {
            'control_points': self.control_points,
            'red_anchors': self.red_anchors,
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
                    self.red_anchors = backup_data.get('red_anchors', set())  # 恢复红色锚点信息
                    self.history = backup_data.get('history', [])
                    self.future = backup_data.get('future', [])
                    self.update_curve_cache()
                    self.update()
                except Exception as e:
                    QMessageBox.warning(self, self.msg_title_backup2, self.msg_restore_backup2.format(error=str(e)))

    def closeEvent(self, event):
        """窗口关闭时提示保存并清理备份和临时文件"""
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
            # 清理临时SVG文件
            self.clean_temp_svg_files()
            event.accept()
        elif reply == QMessageBox.No:
            # 不保存，直接清理备份并退出
            if os.path.exists(self.backup_file):
                try:
                    os.remove(self.backup_file)
                except Exception as e:
                    print(f"Failed to remove backup: {e}")
            # 清理临时SVG文件
            self.clean_temp_svg_files()
            event.accept()
        else:  # Cancel
            event.ignore()  # 取消关闭

    def clean_temp_svg_files(self):
        """清理程序目录中的临时SVG文件"""
        try:
            # 获取程序目录路径
            app_dir = os.path.dirname(os.path.abspath(__file__))
            # 遍历目录中的所有文件
            for filename in os.listdir(app_dir):
                # 检查是否为临时SVG文件
                if filename.startswith("temp_") and filename.endswith(".svg"):
                    file_path = os.path.join(app_dir, filename)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Failed to remove temporary SVG file {filename}: {e}")
        except Exception as e:
            print(f"Error cleaning temporary SVG files: {e}")
            
    def import_image(self):
        """导入图片"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_name:
            self.image = QPixmap(file_name)
            # 启用图片相关滑块
            self.sliders["scale"].setEnabled(True)
            self.sliders["opacity"].setEnabled(True)
            # 设置滑块状态
            for name in ["scale", "opacity"]:
                slider = self.sliders[name]
                label = [label for label in self.slider_labels if label.text() in [self.button_text_image_scale, self.button_text_image_opacity]][0]
                slider.setWindowOpacity(1.0)
                label.setWindowOpacity(1.0)
            self.update()

    def update_image_scale(self):
        """更新图片缩放比例"""
        self.image_scale = self.sliders["scale"].value() / 100.0
        self.update()

    def update_circle_size_label(self, value):
        """更新 Circle size 滑块旁边的 QLabel 显示的值"""
        self.circle_size_value_label.setText(str(value)) # 将 QLabel 的文本设置为滑块的当前值 (转换为字符串)

    def update_image_opacity(self):
        """更新图片透明度"""
        self.image_opacity = self.sliders["opacity"].value() / 100.0
        self.update()

    def update_curve_segments(self):
        """更新曲线绘制段数"""
        self.curve_segments = self.sliders["segments"].value()
        self.update_curve_cache()  # 刷新缓存
        self.update()

    def update_outline_width(self):
        """更新描边粗细"""
        self.outline_width = self.sliders["circle_size"].value()
        self.update()

    def update_outline_opacity(self):
        """更新描边透明度"""
        self.outline_opacity = self.sliders["outline_opacity"].value() / 100.0
        self.update()

    def update_rect_scale(self):
        """更新矩形的大小，并连带缩放曲线和背景图片"""
        old_rect_scale = self.rect_scale
        self.rect_scale = self.sliders["rect_scale"].value() / 100.0
        scale_factor = self.rect_scale / old_rect_scale if old_rect_scale != 0 else 1.0

        center = QPoint(self.width() // 2, self.height() // 2)

        # 缩放控制点 (保持不变)
        for i in range(len(self.control_points)):
            self.control_points[i] = center + (self.control_points[i] - center) * scale_factor

        self.update_curve_cache()  # 刷新缓存
        self.update_circle_size()  # 更新描边尺寸
        self.update()

    def update_circle_size(self): # 请检查函数名拼写是否完全一致！
        """更新描边粗细 (根据 Circle size 滑块值计算)"""
        circle_size_value = self.sliders["circle_size"].value() # 获取 Circle size 滑块的值 # 修改: 使用sliders字典
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
                for i, point in enumerate(self.control_points[1:], 1):  # 从索引1开始
                    remapped_point = self.remap_coordinates(
                        point,
                        rect_bottom_left_current_x, rect_bottom_left_current_y,
                        rect_top_right_current_x, rect_top_right_current_y
                    )
                    file.write(f"|{int(remapped_point.x())}:{int(remapped_point.y())}")
                    
                    # 如果是红锚点，则重复输出该点坐标
                    if i-1 in self.red_anchors:  # i-1是因为self.control_points[1:]从索引1开始，但red_anchors中的索引从0开始
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
        self.control_points = []
        self.red_anchors = set()
        self.allow_save2osu = False
        
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
                        prev_point = None # 用于存储前一个点，检测连续相同点
                        for i, point in enumerate(slider_points):
                            x, y = point.split(":")
                            current_point = QPoint(int(x), int(y))
                            
                            # 检查是否与前一个点坐标相同（红锚点标记）
                            if prev_point is not None and prev_point.x() == current_point.x() and prev_point.y() == current_point.y():
                                # 如果与前一个点坐标相同，则跳过此点（因为已经添加过了）
                                # 并将前一个点的索引添加到红锚点集合中
                                self.red_anchors.add(len(self.control_points) + len(remapped_slider_points) - 1)
                                prev_point = None # 重置前一个点，避免连续三个相同点的情况
                                continue
                            
                            # 正常处理点坐标
                            new_point_remapped = self.remap_coordinates( # 调用 remap_coordinates 进行反向映射
                                current_point,
                                rect_bottom_left_current_x, rect_bottom_left_current_y,
                                rect_top_right_current_x, rect_top_right_current_y,
                                reverse=True # 传入 reverse=True 参数，执行反向映射
                            )
                            remapped_slider_points.append(new_point_remapped) # 将反向映射后的点添加到 remapped_slider_points 列表
                            prev_point = current_point # 更新前一个点

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

    def inverse_remap_coordinates(self, x, y):
        """将 BezierCurveEditor 坐标转换回 osu! 坐标"""
        osu_x = (x - self.offset_x) / self.scale_factor
        osu_y = (y - self.offset_y) / self.scale_factor
        return int(osu_x), int(osu_y)  # 必须转换回整数，否则 osu! 解析会失败

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BezierCurveEditor()
    window.show()
    sys.exit(app.exec_())