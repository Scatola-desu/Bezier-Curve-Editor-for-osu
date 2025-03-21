# 🎨 osu! 滑条曲线编辑器 / Bezier Curve Editor for osu!

![v3.5](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu/blob/main/images/v3.5.gif)

一个简单的曲线绘制工具，用于绘制纯白点 osu! 滑条。  
重新定义滑条设计，从这里开始！

*A simple curve drawing tool for drawing white dot only osu! sliders.  
Redefine slider design—starting now!*

---

## ✨ 主要功能 / Features  
- ✅ **无限缩放窗口，自由调整画布大小**，让曲线编辑更加灵活  
  *Infinitely scalable window and adjustable canvas for flexible curve editing.*  
- ✅ **用超乎想象的操作方式重新定义 Bezier 曲线设计**，全新的锚点操作逻辑等你探索  
  *Redefine Bezier curve design with innovative controls—discover a whole new anchor point logic!*  
- ✅ **实时可视化操作，修改效果一目了然**，提升效率，减少反复调整  
  *Real-time visual feedback—instantly preview modifications for a more efficient workflow.*  
- ✅ **全面的快捷键支持与自动备份**，放手创作，无需担心数据丢失  
  *Comprehensive shortcut support and automatic backups—focus on your creativity without worries!*  
- ✅ **直接读取与导出 osu! 滑条格式**，减少导入 osu! 编辑器后的额外调整  
  *Directly read and export osu! slider format for seamless integration and minimal in-game adjustments.*  

---

## 🎮 操作方式 / Controls  

| 操作 / Action | 快捷键 / Shortcut |
|--------------|----------------|
| **新增锚点 / Add Anchor Point** | `左键 / Left Click` |
| **拖动锚点 / Move Anchor Point** | `左键拖动 / Drag with Left Click` |
| **切换红白锚点 / Toggle Red/Normal Anchor** | `右键 / Right Click` |
| **缩放 & 平移 / Zoom & Pan** | `滚轮 / Mouse Wheel` |
| **增加中间锚点 / Add Mid Anchor Point** | `ALT + 左键 / ALT + Left Click` |
| **增加头尾锚点 / Add Start/End Anchor Point** | `ALT + CTRL + 左键 / ALT + CTRL + Left Click` |
| **删除锚点 / Delete Anchor Point** | `在锚点上 ALT + 左键 / ALT + Left Click on Anchor` |
| **拖动曲线和图片 / Drag Curve and Image** | `CTRL + 中键 / CTRL + Middle Click` |
| **拖动曲线变形 / Deform Curve** | `CTRL + 左键拖动 / Drag with CTRL + Left Click` |
| **旋转滑条 / Rotate Slider** | `右键拖动 / Drag with Right Click` |
| **设置旋转基准点 / Set Rotation Pivot** | `ALT + 右键 / ALT + Right Click` |
| **锁定方向拖动锚点 / Lock Direction Drag** | `SHIFT + 左键 / SHIFT + Left Click` |
| **平衡化红锚点 / Balance Red Anchors** | `SHIFT + 右键 / SHIFT + Right Click` |
| **快速保存 / Quick Save** | `CTRL + S` |
| **撤销 / Undo** | `CTRL + Z` |
| **重做 / Redo** | `CTRL + Y` |

### 👁️ 可视化操作 / Visual Feedback  
- **鼠标悬停于控制点** 时，预览该控制点的影响范围  
  *Hover over a control point to preview its area of influence.*  
- **按住 `ALT`** 预览加减点效果，新曲线会根据与原曲线的距离变化颜色，使调整幅度较大的区域更加明显  
  *Hold `ALT` to preview the effect of adding or removing points. The new curve will change color based on its distance from the original, making significant changes more visible.*  
- **按住 `CTRL`** 在曲线上查找对应的控制点  
  *Hold `CTRL` to locate the corresponding control point on the curve.*
- **按住 `SHIFT` + 左键** 锁定方向拖动锚点/切线投影  
  *Hold `SHIFT` + Left Click to lock direction drag anchor/tangent projection.*
- **按住 `SHIFT` + 右键** 平衡化红锚点  
  *Hold `SHIFT` + Right Click to balance red anchors.*  
- **操作时，受影响的区域会高亮，其他部分自动减淡，让你专注于修改**  
  *When making adjustments, the affected area will be highlighted while non-essential parts fade out, helping you focus on your edits.*  

### 💾 文件管理 / File Management  
| 操作 / Action | 快捷键 / Shortcut |
|--------------|----------------|
| **快速保存 / Quick Save** | `CTRL + S` |
| **撤销 / Undo** | `CTRL + Z` |
| **重做 / Redo** | `CTRL + Y` |

---

## 📏 重要提示 / Important Notes  
- **请调整 Playfield Boundary（游戏区域边界）大小**，导出时曲线坐标会根据该边界重新映射。  
  *Please adjust the Playfield Boundary size when exporting. The curve coordinates will be remapped according to the size of this box during export.*  
- **灰色实线是编辑器边界**，**灰色虚线是 4:3 分辨率下的游戏边界**。  
  *The gray solid line is the editor boundary, and the gray dashed line is the game boundary at 4:3 resolution.*  
- **支持直接读取 / 导出 osu! 滑条格式的代码**。  
  *The code in osu! slider format can be read/exported directly.*  
- **自动保存机制可防止程序意外崩溃带来的数据丢失**，所有操作都会定期备份，确保你的工作安全。  
  *The auto-save mechanism prevents data loss in case of unexpected crashes. All operations are periodically backed up to ensure your work is safe.*  
---

🚀 **Enjoy your mapping! 🎵**  
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/A0A51C773P)

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu/blob/main/images/v3.1.png)
v3.1

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/Curve_Deformation.gif)   
v3.0  

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/v2.9.png)  
v2.9  

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/v2.8.png)  
v2.8  

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/v2.4.png)  
v2.4
