# Bezier-Curve-Editor-for-osu-
Bezier Curve Editor for osu! 

![logo](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/icon.png)

一个简单的曲线绘制工具，用于绘制纯白点osu!滑条  
可无限拉大窗口或缩小曲线，方便移动较远的锚点  
A simple curve drawing tool for drawing pure white dot osu! sliders  
You can infinitely enlarge the window or shrink the curve, making it convenient to move distant anchor points  

**左键** - 新增尾部锚点  
**右键** - 拖动已有锚点  
**中键** - 拖动曲线  
**滚轮** - 整体缩放/平移曲线  
**alt+左键** - 在曲线中间增加锚点（算法有些问题，如果添加位置不对请换个位置再试试）  
**alt+右键** - 删除锚点（对空白处按住时，高亮显示最近的锚点连线）  
**CTRL+中键** - 同时拖动曲线和图片  

注意调整**Playfirld Boundary**的大小  
导出时会根据这个框的大小对曲线坐标重新映射  
**灰色实线**是编辑器边界 **灰色虚线是**是4:3分辨率下的游戏边界  

**Left Click** - Add tail anchor point  
**Right Click** - Drag existing anchor point  
**Middle Click** - Drag curve  
**Mouse Wheel** - Overall scale/pan curve  
**Alt + Left Click** - Add anchor point in the middle of the curve (algorithm has some issues, if the addition position is incorrect, please try another position)  
**Alt + Right Click** - Delete anchor point (when holding over an empty area, highlight the nearest anchor point connection)  
**CTRL + Middle Click** - Drag curve and image simultaneously  

Please adjust the **Playfield Boundary** size when exporting.  
The curve coordinates will be remapped according to the size of this box during export.  
**The gray solid line** is the editor boundary, and **the gray dashed line** is the game boundary at 4:3 resolution.  

可直接读取/导出osu!滑条格式的代码  
The code in osu! slider format can be read/exported directly  

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/v2.9.png)
v2.9

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/v2.8.png)
v2.8

![预览图](https://github.com/Scatola-desu/Bezier-Curve-Editor-for-osu-/blob/main/images/v2.4.png)
v2.4
