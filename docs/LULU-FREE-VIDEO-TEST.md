# 免费视频试生成：已成功

## 新增专项动作与衔接预览

按用户要求，继续在同一已授权免费服务上生成了原地走路、打瞌睡两段，每段实际3.56秒、560×832、16fps。未使用账号、API Key或付费凭据。

- 原片：`build/lulu-video-free/walk/lulu-walk.mp4`、`sleep/lulu-sleep.mp4`。
- 衔接版：`build/lulu-video-free/lulu-actions-preview.gif` 与同名MP4，9.5秒；播放顺序为待机→走路→回到待机→打瞌睡→回到待机。
- 原片结束姿态未完全匹配参考图，因此未直接硬切循环。每段结束加入0.5秒运动补偿过渡，回到同一待机图；保留16fps原始动作节奏。
- 接缝每步平均像素变化：走路由硬切6.437降至最大1.520；打瞌睡由5.975降至最大1.612。该数值仅辅助筛查，已同时查看 `transition-review.png` 的头部、眼镜、嘴型及身体边缘。
- GIF直接由无损内存帧编码，使用统一调色板；解码后验证首尾图像像素完全一致。MP4有正常有损编码差异。
- 限制：打瞌睡片包含模型自行增加的小哈欠；走路有轻微身体转向。仍带米色背景/地面阴影，尚未完成透明桌宠素材或更新运行程序。

每段的 `request.json`、`job.json`、`events.txt` 保存生成参数和成功结果；衔接统计在 `build/lulu-video-free/transition-report.json`。

用户明确批准只上传选中的角色参考图后，匿名调用已成功。没有使用账号、API Key或付费凭据。

输出：`build/lulu-video-free/lulu-wave.mp4`，H.264，560×832，实际3.56秒、16fps；`lulu-wave.gif` 为保持原时间节奏的循环预览，`video-review.png` 为按每秒3张抽取的检查图。模型源码注释提到24fps，但实际文件为16fps，以文件解码结果为准。

抽帧检查：保持单一角色及完整身体，包含眨眼、抬手、挥动、放手；中途出现双手参与而非严格单手。仍带米色背景和地面阴影，尚未完成透明处理/无缝循环，也未替换桌面程序。

已检查的服务：Hugging Face 上 `zerogpu-aoti/wan2-2-fp8da-aoti-faster`，公开API状态为 RUNNING。服务地址：<https://huggingface.co/spaces/zerogpu-aoti/wan2-2-fp8da-aoti-faster>。

## 具体试片

- 唯一上传文件：`windows/Meow.Windows/Assets/Lulu/reference.png`，用户选中的第一版张噜噜角色图。
- 目标：固定镜头、自然站立、轻轻挥手、回到站姿。
- 时长：3.5秒；推理步数：6；两段guidance均1；种子42。
- 不使用账号、API Key或付费凭据；若要求登录/额度不足/付费则停止，不能保证匿名额度足够完成生成。
- 不上传源代码、聊天记录、设置、密钥或其他文件。

Prompt:

> Locked-off frontal camera, full body. The same plush yellow capybara with dark bowl haircut, round brown glasses and orange shorts stands in one fixed place. It gently raises one paw, makes two small relaxed waves, then lowers the paw back to the starting pose. Both feet remain firmly planted. Preserve the exact head and body proportions, fur texture, outfit and lighting throughout. Subtle natural breathing. Smooth continuous movement, plain clean background, no camera movement.

Negative prompt:

> camera movement, cuts, zoom, hopping, extra limbs, stretched arms, changing face, changing head size, melting, morphing, jitter, duplicate body, ghosting, text, watermark, new props

## 已确认的限制

- 本机只有 AMD Radeon 840M 核显及24GiB系统内存；不能把系统内存当作CUDA独显显存。官方Wan2.2 TI2V-5B示例要求至少24GB GPU显存，因此不在本机贸然下载部署。
- ZeroGPU存在每日配额和排队，免费演示不是稳定、无限量的免费API。实际能否生成需提交后确认。
- 最初上传被自动审批阻止；用户随后明确同意了具体图片与服务目的地，已在该授权范围内完成上传和试生成。
