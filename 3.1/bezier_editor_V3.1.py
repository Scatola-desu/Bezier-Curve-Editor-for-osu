from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QSlider, QHBoxLayout, QLabel, QMessageBox, QShortcut
)
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPen, QPixmap, QBrush, QVector2D
from PyQt5.QtCore import Qt, QPoint, QLocale, QLineF, QPropertyAnimation
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
        self.history = []  # 操作历史
        self.future = []  # 撤销后的操作
        self.max_history_size = 20  # 设置最大历史记录长度
        self.dragging_point = None  # 当前拖动的控制点索引
        self.image = None  # 导入的图片
        self.image_scale = 1.0  # 图片缩放比例
        self.image_opacity = 1.0  # 图片透明度
        self.curve_segments = 100  # 曲线绘制段数
        self.config_file = "config.json"  # 配置文件路径
        self.osu_songs_path = self.load_config()  # 加载配置

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
        self.cached_curve_points = None  # 初始化缓存为空
        self.update_curve_cache()  # 初始调用，计算缓存
        self.is_alt_pressed = False  # 新增：跟踪 Alt 键状态
        self.get_button_texts()

        self.is_ctrl_pressed = False
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
            self.msg_error_red_anchor_not_supported = "本工具暂不支持含有红色锚点的滑条编辑！"
            self.msg_error_not_slider_or_unsupported = "选中的对象不是滑条或非受支持的类型！"
            self.msg_error_no_slider_selected = "未检测到选中的滑条！"
            self.msg_set_osu_path = "请先设置Songs文件夹路径！"
            self.msg_set_osu_path_success = "osu! Songs文件夹路径设置成功！"
            self.msg_set_osu_path_title = "设置osu!歌曲文件夹"
            self.msg_set_osu_path_prompt = "是否选择osu!歌曲文件夹路径？"
            self.msg_set_osu_path_dialog = "选择osu!/Songs文件夹"


            self.help_label_text = """
                操作提示：<br>
                <b><span style="color:#50B9FE">左键</span></b> 新增锚点<br>
                <b><span style="color:#DCDC8B">滚轮</span></b> 缩放/平移<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#50B9FE">左键</span></b> 增加中间锚点/删除锚点<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#354EEC">CTRL</span>+<span style="color:#50B9FE">左键</span></b> 增加头尾锚点<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#AC9178">右键</span></b> 设置旋转基准点<br>
                <b><span style="color:#AC9178">右键</span></b> 拖动曲线旋转<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#DCDC8B">中键</span></b> 拖动曲线和图片<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#50B9FE">左键</span></b> 拖动曲线变形<br>
                <b><span style="color:#354EEC">CTRL</span>+S</b> 快速保存<br>
                <b><span style="color:#354EEC">CTRL</span>+Z</b> 撤销<br>
                <b><span style="color:#354EEC">CTRL</span>+Y</b> 重做<br>
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
            self.msg_error_red_anchor_not_supported = "This tool does not currently support editing sliders with red anchor points!"
            self.msg_error_not_slider_or_unsupported = "The selected object is not a slider or an unsupported type!"
            self.msg_error_no_slider_selected = "No slider selected!"
            self.msg_set_osu_path = "Please set the Songs folder path!"
            self.msg_set_osu_path_success = "osu! Songs folder path set successfully!"
            self.msg_set_osu_path_title = "Set osu! Songs Folder"
            self.msg_set_osu_path_prompt = "Do you want to set the osu! Songs folder path?"
            self.msg_set_osu_path_dialog = "Select osu!/Songs folder"

            self.help_label_text = """
                Operation Hints:<br>
                <b><span style="color:#50B9FE">Left Click:</span></b> Add Anchor Point<br>
                <b><span style="color:#DCDC8B">Mouse Wheel:</span></b> Zoom/Pan<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#50B9FE">Left Click:</span></b> Add Mid Anchor Point / Delete Anchor Point<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#354EEC">CTRL</span>+<span style="color:#50B9FE">Left Click</span>:</b> Add Start/End Anchor Point<br>
                <b><span style="color:#FEFD02">ALT</span>+<span style="color:#AC9178">Right Click:</span></b> Set Rotation Pivot Point<br>
                <b><span style="color:#AC9178">Right Click:</span></b> Drag Curve Rotation<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#DCDC8B">Middle Click:</span></b> Drag Curve and Image<br>
                <b><span style="color:#354EEC">CTRL</span>+<span style="color:#50B9FE">Left Click:</span></b> Deform Curve<br>
                <b><span style="color:#354EEC">CTRL</span>+S:</b> Quick Save<br>
                <b><span style="color:#354EEC">CTRL</span>+Z:</b> Undo<br>
                <b><span style="color:#354EEC">CTRL</span>+Y:</b> Redo<br>
                """

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
            # print(f"ContainingFolder: {reader.ContainingFolder}")

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
            last_point = None

            for pt in control_points_str:
                x, y = map(int, pt.split(":"))
                mapped_pt = self.remap_coordinates(
                    QPoint(x, y),
                    rect_bottom_left_current_x, rect_bottom_left_current_y,
                    rect_top_right_current_x, rect_top_right_current_y,
                    reverse=True
                )

                # 检查是否有重复锚点
                if last_point and last_point == mapped_pt:
                    self.update_curve_cache()
                    QMessageBox.warning(self, self.msg_title_error, self.msg_error_red_anchor_not_supported)
                    return

                self.control_points.append(mapped_pt)
                last_point = mapped_pt  # 记录最后一个点以便检测重复

            # 更新曲线显示
            self.update_curve_cache()
            self.update()

            QMessageBox.information(self, self.msg_title_success, self.msg_success_load_selected_slider)

        except Exception as e:
            QMessageBox.warning(self, self.msg_title_error, self.msg_error_load_selected_slider.format(error=str(e)))

    def save_slider_data(self):
        """将修改后的滑条数据写回 .osu 文件"""
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
            for pt in self.control_points[1:]:  # 🚀 从索引 `1` 开始，去掉第一个点
                osu_point = self.remap_coordinates(
                    pt,
                    rect_bottom_left_current_x, rect_bottom_left_current_y,
                    rect_top_right_current_x, rect_top_right_current_y,
                    reverse=False
                )
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

        except Exception as e:
            QMessageBox.warning(self, self.msg_title_error, self.msg_error_save_slider.format(error=e)) 

            
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
        #self.setStyleSheet("background-color: #0C0C0C; color: #FFFFFF;")

        # 确保icons目录存在
        icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
        if not os.path.exists(icons_dir):
            os.makedirs(icons_dir)

        # 创建左侧按钮区域背景
        self.left_panel = QWidget(self)
        self.left_panel.setGeometry(0, 0, 80, self.height())
        self.left_panel.setStyleSheet("background-color: #242723;")

        # 右侧绘图区域
        #self.drawing_area = QWidget(self)
        #self.drawing_area.setGeometry(40, 0, self.width() - 40, self.height())
        #self.drawing_area.setStyleSheet("background-color: #202020;")

        # 按钮样式 - 左侧图标按钮
        self.sidebar_button_style = """
            QPushButton {
                background-color: #262626;
                color: white;
                border: 1px solid #4c4c4c;
                border-radius: 2px;
                padding: 5px;
                font-size: 7px;
            }
            QPushButton:hover {
                background-color: #262626;
                color: #e58f9b;
                border: 1px solid #ff8a9b;
            }
        """

        # 创建左侧按钮
        self.create_sidebar_buttons()

        # 操作提示标签
        self.help_label = QLabel(self.help_label_text, self) 
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
        self.help_label.setWordWrap(True)
        self.help_label.adjustSize()
        self.update_help_position()

        # 默认显示帮助和滑块
        self.help_visible = True
        self.sliders_visible = True
        
        # 创建滑块控件（放在右侧区域）
        self.create_sliders()
        
        # 移除右下角的帮助显示/隐藏按钮
        if hasattr(self, 'hide_help_button'):
            self.hide_help_button.deleteLater()
        
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
            color = "#EDAFFF" if is_active else "white"
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            
            # 创建临时文件用于设置图标
            temp_svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_normal_{id(button)}.svg")
            with open(temp_svg_path, 'w') as f:
                f.write(svg_content)
            
            # 更新按钮样式，保留文本位置和样式
            button.setStyleSheet(self.sidebar_button_style + f"""
                QPushButton {{                    
                    background-image: url({temp_svg_path.replace('\\', '/')});
                    background-position: center 0px;
                    background-repeat: no-repeat;
                    text-align: center;
                    padding-top: 45px;
                    font-size: 10px;
                    color: {color};
                    border: 1px solid {"#EDAFFF" if is_active else "#4c4c4c"};
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
        # 按钮配置 - 每个按钮的图标和对应的方法
        button_configs = [
            {"icon": "icons/import_slider.svg", "tooltip": self.button_text_load_selected_slider, "callback": self.load_selected_slider},
            {"icon": "icons/export_slider.svg", "tooltip": self.button_text_export_to_osu, "callback": self.save_slider_data},
            {"icon": "icons/import_image.svg", "tooltip": self.button_text_import_image, "callback": self.import_image},
            {"icon": "icons/import_text.svg", "tooltip": self.button_text_import_slider, "callback": self.import_slider},
            {"icon": "icons/export_text.svg", "tooltip": self.button_text_export_control_points, "callback": self.export_points},
            {"icon": "icons/slider_toggle.svg", "tooltip": self.button_text_sliders, "callback": self.toggle_sliders_visibility, "active": True},
            {"icon": "icons/help.svg", "tooltip": self.button_text_show_help, "callback": self.toggle_help_visibility, "active": True},
            {"icon": "icons/settings.svg", "tooltip": self.button_text_osu_path, "callback": self.set_osu_path},
            {"icon": "icons/visualization.svg", "tooltip": self.button_text_visualizations, "callback": self.toggle_visualization_display, "active": True}
        ]
        
        # 创建按钮
        self.sidebar_buttons = []
        button_height = 75  # 增加高度以容纳文字
        button_width = 75   
        button_margin = 8   
        
        # 计算底部按钮的起始位置
        bottom_buttons = ["slider_toggle", "help", "settings", "visualization"]
        bottom_start = self.height() - (len(bottom_buttons) * (button_height + button_margin)) - button_margin
        
        for i, config in enumerate(button_configs):
            button = QPushButton("", self)
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
            active_color = "#EDAFFF" if config.get("active", False) else "white"
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{active_color}"')
            
            # 创建临时文件用于设置图标
            temp_svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"temp_{i}.svg")
            with open(temp_svg_path, 'w') as f:
                f.write(svg_content)
            
            # 设置图标和文字
            button.setText(config["tooltip"])
            button.setStyleSheet(self.sidebar_button_style + f"""
                QPushButton {{                    
                    background-image: url({temp_svg_path.replace('\\', '/')});
                    background-position: center 0px;
                    background-repeat: no-repeat;
                    text-align: center;
                    padding-top: 45px;
                    font-size: 10px;
                    color: {active_color};
                }}
            """)
            

            
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
                background: transparent; /* 去除控件的默认背景色 */
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #333333;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #FF8A9B;
                border: 1px solid #5C44BE;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #9e49da;
            }
        """
        
        # 标签样式
        label_style = "color: #FFFFFF; font-size: 12px;"
        
        # 滑块配置
        slider_configs = [
            {"name": "scale", "label": self.button_text_image_scale, "min": 10, "max": 200, "value": 100, "callback": self.update_image_scale},
            {"name": "opacity", "label": self.button_text_image_opacity, "min": 0, "max": 100, "value": 100, "callback": self.update_image_opacity},
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
                self.circle_size_value_label.move(start_x + slider_width + 5, start_y + i * (slider_height + label_height + slider_margin) + label_height)
                self.slider_labels.append(self.circle_size_value_label)
                slider.valueChanged.connect(self.update_circle_size_label)
        
        # 设置面板大小和位置
        panel_width = slider_width + 50
        panel_height = (len(slider_configs) * (slider_height + label_height + slider_margin)) + panel_padding * 2
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
                # Ctrl + 鼠标中键：开始拖动曲线和图片 (保持不变)
                self.dragging_curve_and_image = True
                self.dragging_curve_only = False
            else:
                # 鼠标中键：开始单独拖动曲线 (保持不变)
                self.dragging_curve_only = True
                self.dragging_curve_and_image = False
            self.last_mouse_pos = event.pos()
        elif event.button() == Qt.LeftButton:
            # 1. alt+左键且存在预选中锚点时：删除锚点 (保持不变)
            if event.modifiers() == Qt.AltModifier and self.pre_selected_point_index is not None:
                if self.pre_selected_point_index is not None: # 再次检查预选中锚点索引是否有效
                    self.delete_control_point_by_index(self.pre_selected_point_index)
                    self.pre_selected_point_index = None  # 删除后清除预选
                    self.update()
                    return  # 提前返回，避免执行后续的左键添加锚点逻辑
            # 2. 存在预选中锚点时 左键拖动锚点 (保持不变)
            elif self.pre_selected_point_index is not None:
                self.dragging_point = self.pre_selected_point_index #  使用预选中的索引
                self.is_dragging_control_point = True
                self.drag_start_point = event.pos()
                return  # 提前返回，避免执行后续的左键添加锚点逻辑
            # 3. 仅在无预选中锚点和无修饰键时 左键加添锚点 (保持不变)
            elif self.pre_selected_point_index is None and event.modifiers() == Qt.NoModifier: # 确保没有预选中点和没有修饰键
                self.save_state()
                self.control_points.append(event.pos())
                self.update_curve_cache()
                self.update()
            # Alt + Ctrl：添加头尾锚点 (保持不变) - 但只有在没有预选点时才触发，避免冲突
            elif event.modifiers() & Qt.AltModifier and event.modifiers() & Qt.ControlModifier and len(self.control_points) >= 2 and self.pre_selected_point_index is None:
                self.save_state()
                insert_index = self.get_insert_position(event.pos())
                if insert_index is not None:
                    if insert_index == 0:
                        self.control_points.insert(0, event.pos())
                    else:
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

            # 【新增：Alt + 右键设置旋转基准点】
            if event.modifiers() == Qt.AltModifier:
                self.rotation_pivot_point = event.pos() # 设置旋转基准点为当前鼠标位置
                self.has_rotation_pivot = True # 标记已设置基准点
            # 【新增：无修饰符的右键开始曲线旋转】
            elif event.modifiers() == Qt.NoModifier and self.has_rotation_pivot: # 确保已设置基准点
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

        # 2. 存在预选中锚点时 左键拖动锚点 (移动逻辑) (保持不变)
        if self.is_dragging_control_point:
            if self.dragging_point is not None:
                self.control_points[self.dragging_point] = event.pos()
                self.update_curve_cache()
                self.update()
                return # 拖动锚点时提前返回，不执行其他移动逻辑


        if self.is_ctrl_dragging_deformation and self.closest_curve_point is not None:
            # Ctrl + 左键拖动：变形曲线 (保持不变)
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
            curve_order = len(self.control_points) - 1
            for i in range(len(self.control_points)):
                influence = self.bernstein_basis_polynomial(curve_order, i, t)
                move_vector = QPoint(int(delta.x() * influence * 2), int(delta.y() * influence * 2))
                self.control_points[i] = self.control_points[i] + move_vector
            self.drag_start_pos = current_pos
            self.update_curve_cache()
            self.update()
            return

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

    def delete_control_point_by_index(self, index):
        if 0 <= index < len(self.control_points):
            self.save_state()
            del self.control_points[index]
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
        
        # 绘制左侧面板背景
        painter.fillRect(0, 0, 80, self.height(), QColor("#242723"))
        
        # 不再绘制右侧绘图区域背景，避免覆盖曲线
        painter.fillRect(80, 0, self.width() - 80, self.height(), QColor("#202020"))

        # 计算窗口中心 - 考虑左侧面板的宽度
        center_x = (self.width() - 80) // 2 + 80
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

        # 【新增：绘制旋转基准点】
        if self.has_rotation_pivot and (self.is_alt_pressed or self.is_right_button_pressed): # Alt 或 右键按下时显示
            painter.setPen(QPen(Qt.green, 2)) # 绿色画笔
            pivot_x, pivot_y = self.rotation_pivot_point.x(), self.rotation_pivot_point.y()
            cross_size = 10 # 十字大小
            painter.drawLine(pivot_x - cross_size, pivot_y, pivot_x + cross_size, pivot_y) # 横线
            painter.drawLine(pivot_x, pivot_y - cross_size, pivot_x, pivot_y + cross_size) # 竖线


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