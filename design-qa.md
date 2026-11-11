# 张噜噜设计验收

final result: blocked

视觉依据：`windows/Meow.Windows/Assets/Lulu/reference.png`，用户选中的第一版毛绒角色。

实现截图：`build/Meow-Windows-Lulu/visual-checks/design-comparison.png`、`pet-states.png`、`walk-16frames.png`、`walk-interpolation.png`。

比较画布：1200×600，WPF 96dpi（非浏览器）；左侧原图1024×1536按比例展示，右侧渲染角色570×570并按足底对齐。动作检查单格230×230。此前已在同一比较图中检查原图与运行时渲染。

## 阻塞问题与迭代记录

1. P1：四帧动作不连续；多数情绪共用一张脸。用户现场反馈。已生成16帧主要动作及独立情绪素材，改成屏幕刷新回调。
2. P1：新图集仍存在头身位置/姿态漂移；稀疏帧混合产生双眼镜、手臂残影。截图 `pet-states.png` 可见。用户再次否定流畅性和动作自然度。单纯提高刷新率或淡入淡出无法通过验收。
3. 关节部件方案已进入源码试验，尚未完成视觉验收，未更新用户原启动目录。用户随后要求使用AI视频工具；当前主路线转为 `docs/LULU-VIDEO-BRIEF.md`。
4. 电脑自动操作已由用户按Esc停止，不继续操作窗口。当前仍未通过真实窗口动画验收。

## 视觉检查面

- 字体：沿用原Windows界面字体；参考角色图没有文字。
- 布局：静态形象保留大头短身，动画姿态稳定性未通过。
- 颜色：黄毛绒、橙鼻口/短裤、黑西瓜头、棕圆眼镜已保留。
- 图片：静态透明边缘在浅/深背景可用；动态重影和形变仍是阻塞项。
- 文案：Windows角色名和人格为张噜噜；Mac源代码未修改。

## 下一步

已转用用户明确授权的 Hugging Face 免费 Wan 视频服务，并实际生成挥手、原地走路、打瞌睡。最新 `build/lulu-video-free/lulu-actions-preview.gif` 是9.5秒专项动作衔接预览：统一待机图、每段末尾0.5秒运动补偿过渡，编码后首尾像素一致。视觉检查证据是 `walk/transition-review.png` 和 `sleep/transition-review.png`，检查了过渡中头部/眼镜/嘴型与主体边缘。视频预览可供用户评价，但仍带背景；透明素材处理、正式程序接入与桌面验收尚未完成，因此整个桌宠交付仍 blocked。
