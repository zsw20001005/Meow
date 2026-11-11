# 张噜噜：AI 视频动画制作方案（待连接视频服务）

用户已选择第一版角色，并否定独立生成的4帧/16帧图集：动作不流畅、姿态诡异。新的方向是从同一参考图生成真实连续视频，再制作桌面循环动画。现有逐帧方案和关节试验均未通过用户验收，不应视为最终版。

## 第一条试片

- 参考图：`windows/Meow.Windows/Assets/Lulu/reference.png`。
- 先制作一个站立挥手短片，不批量生成全部动作。
- 固定正面镜头、全身入画、角色与画面中心不移动；无镜头运动、变焦、切镜、字幕、道具或地面阴影。
- 角色保持同一黄色毛绒水豚、橙色大鼻口、黑西瓜头、棕色圆框眼镜、橙色短裤；头身比例全程不变。
- 自然站立 → 一只手缓慢抬起 → 小幅挥动两次 → 放下 → 回到原始站姿。脚始终接地，不上下弹跳、不伸长四肢、不旋转整个人。
- 目标4–5秒，使用视频模型原生帧率，目标至少24fps。循环边界在稳定站立处截取；先检查真实动作，再决定是否需要额外过渡。
- 优先得到可去背景的纯色背景视频。透明输出能力需连接后核实，不把普通MP4宣称为透明动画。

英文动作提示：

> Locked-off frontal camera, full-body view. The exact plush yellow capybara from the reference image stands calmly in one fixed place, wearing the same dark bowl haircut, round brown glasses and orange shorts. Preserve the exact face, fur texture, body proportions, lighting and scale throughout the shot. With both feet planted firmly, the character slowly raises one paw, makes two small relaxed waves, then lowers the paw and returns to the identical relaxed starting pose. Gentle natural breathing only. Continuous physically coherent motion. No hopping, no stretching limbs, no head-size changes, no body morphing, no camera movement, no cuts, no text, no added props. Plain clean background for subject extraction, no floor shadow.

## 接入路径

1. 连接Runway账户；检查图生视频、素材上传、视频去背景、导出工具以及账户额度。
2. 生成首条短片，展示给用户确认动作。
3. 去除背景、检查毛绒边缘与透明通道，截取自然循环。
4. 桌面程序按源视频时间戳播放连续透明PNG帧（或评估支持alpha的动画格式）；GIF可作为分享预览。
5. 挥手通过后，用相同角色参考逐个制作走路、待机、睡觉、吃西瓜等动作。

视频工具未连接前，不声称已生成AI视频，也不继续批量制作独立AI关键帧。
