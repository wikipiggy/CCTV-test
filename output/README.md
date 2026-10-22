# CCTV Headquarters 外观重建

基于本次对话提供的两张剖面图、F41 平面图、总平面图及四张实景照片进行参数化外观重建。不是施工 BIM、测绘模型或逐根结构复原。没有办公室、内部楼板与机电结构。

## 文件与运行

- `CCTV_Headquarters.blend`：米制场景，建筑、幕墙、悬挑底面、道路、城市环境、相机、日光和独立幕墙样板。
- `build_cctv.py`：从零生成场景的 bpy 脚本，固定随机种子 17。
- `render_views.py`：直接使用已保存的场景生成进度图、样板和最终图，不必重建。
- `geometry_validation.json`：逐立面二维玻璃/槽带面积、相交面积和凹入深度检查。
- `progress_*.png`：正交、平面及整体预览。
- `sample_recess_*mm.png`：20 / 30 / 40 mm 转角幕墙样板。
- `render_01.png` 至 `render_04.png`：正式外观视角。

环境：Blender 4.3.2（本环境内置 Python 3.13），Cycles CPU，5 线程。Shapely 2.1.2 用于槽带多边形求并与裁剪。渲染已有 `.blend` 不需要 Shapely。

```bash
# 安装与 Blender Python 匹配的几何库；若 Blender Python 版本不同，请相应修改版本参数。
python -m pip install --target /workspace/cctv-blender-python --python-version 3.13 --only-binary=:all: shapely==2.1.2
# 在仓库根目录运行
blender --python-exit-code 1 -b -t 5 --python output/build_cctv.py -- --stage model
blender --python-exit-code 1 -b output/CCTV_Headquarters.blend -t 5 --python output/render_views.py -- --mode preview
blender --python-exit-code 1 -b output/CCTV_Headquarters.blend -t 5 --python output/render_views.py -- --mode sample
blender --python-exit-code 1 -b output/CCTV_Headquarters.blend -t 5 --python output/render_views.py -- --mode final
```

可通过 `CCTV_GEOMETRY_PATH` 覆盖第三方库目录；路径中不能包含私密凭证。每个云任务已有隔离工作区，使用现有 checkout，无需创建 Git worktree。

## 几何依据与估算范围

坐标 X 东、Y 北、Z 上，单位米，地面 Z=0。Tower 1 位于西北，Tower 2 位于东南。两塔下段的截面中心由地面向 Z=161m 线性平移，连接单一凹 L 形上部体量；上部侧面采用双线性参数映射。

主体屋顶最高 234m；最低屋顶边缘 213.90m；悬挑底面 161m。较低塔楼屋顶由连续斜屋顶控制，并非全屋顶恒定 210m。屋顶设备属于外部附属物，主体高度与设备高度分开理解。

平面跨度、塔楼截面宽度、倾斜平移量、裙房尺寸、道路宽度和景观位置是按图片比例推定，未获得完整带尺寸建筑图。主楼周边为平坦城市环境；道路方位参考总平面图。周边建筑、车辆、树木和 TVCC 均为简化环境体量。

网格包含两组斜线及局部加密，模拟照片可见的疏密变化，不声称逐条对应实楼。玻璃为不透明的反射型外壳材质，避免没有内部模型时出现不真实的透视；不代表实测玻璃光学参数。

## 凹槽实现

1. 在每个立面的局部二维坐标中生成斜向带状多边形。
2. 对带状多边形先求并集，再裁剪至幕墙边界。
3. 玻璃区域 = 立面区域减去槽带并集，玻璃不存在于槽带位置。
4. 槽底沿外法线反方向凹入；主楼采用 30 mm，样板比较 20 / 30 / 40 mm。这些是试验参数，不是实楼测量值。
5. 从槽带边界生成槽壁，交叉处按并集融合，边界收口没有突出杆端；几何边缘设置 3 mm 小倒角。
6. 细分格横竖框裁剪至剩余玻璃区域，凸出量 4 mm。

场景的 `Recess samples` 集合放置于远离主楼的 X=1100m 附近，可单独查看。薄壳面片不用于体积或结构分析，不保证整个场景为单一水密实体。

## 质量边界

这是依据有限参考图的可编辑、可复现重建。没有完整尺寸和高清全立面网格图，不能承诺测绘级比例或施工级节点。图像使用物理日光与 Cycles 路径追踪（本 Blender 构建没有 OpenImageDenoise，因此使用较高采样与自适应采样，不启用降噪）；城市背景与植被简化，写实程度需结合最终图判断。
