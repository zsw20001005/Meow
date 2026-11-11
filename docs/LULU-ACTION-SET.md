# 张噜噜专项动作批次

沿用用户选定的 `windows/Meow.Windows/Assets/Lulu/reference.png`。保持黄色毛绒水豚、黑西瓜头、棕色圆眼镜、橙色鼻口和短裤。镜头、画面中心、角色比例与脚底基线固定。

用户约束：各动作分别导出；动作间衔接自然；继续使用免费生成方式。生成成功后检查原片，再制作回到统一待机姿势的独立循环，不能仅凭首尾图片相同就认定动作自然。

| 动作 | 动作设计 | 起止/质量要求 | 本批状态 |
| --- | --- | --- | --- |
| 吃西瓜 | 从身侧取出小西瓜片，双手托住吃一小口，放回身侧 | 食物不能悬空/变大，双手最后放下 | 已尝试，服务拒绝，未生成 |
| 伸懒腰 | 双手缓缓抬高、轻抬下巴、闭眼舒展，然后放下 | 保持四肢长度与身体比例、双脚落地 | 未提交，等待免费额度/授权 |
| 点头 | 两次小幅友好点头，轻眨眼，身体基本不动 | 只转动颈部，不整个人鞠躬 | 已尝试，服务确认额度限制 |
| 开心小舞步 | 小幅左右换重心两次，膝盖轻弯，爪子低位摆动 | 不腾空、不转圈、不夸张甩手 | 未提交，等待免费额度/授权 |

## 实际阻塞

服务：`zerogpu-aoti/wan2-2-fp8da-aoti-faster`。公开状态仍为RUNNING，参考图HTTP 200，参数数量与接口配置一致。

普通 `/call` 返回 `error: null`。通过官方客户端对应的标准队列协议取得明确错误：

> You have exceeded your ZeroGPU runs limit. Authenticate with a Hugging Face token for more quota.

完整回执保存在 `build/lulu-video-free/nod/queue-events.txt`。确认匿名调用次数耗尽后已停止，不更换身份/网络规避限制、不使用付费凭据。

需要用户提供免费的HF账号授权，或等待服务的匿名额度恢复后继续。此批尚无可交付的新动作视频，不能把此前的挥手、走路、打瞌睡当成本批新成果。

## 已准备的流程

- `scripts/generate_lulu_action.ps1`：支持上述四个动作，保存单独的请求与任务记录。
- `scripts/receive_lulu_action.ps1`：收取已创建任务的状态和视频，不自动新建任务。
- `scripts/preview_lulu_video.py`、`scripts/check_lulu_seams.py`：生成逐帧检查图与首尾差异报告。
- `scripts/build_lulu_transition_preview.py --actions eat stretch nod dance`：仅在视频全部存在且人工查看动作后执行，默认分别导出，不再自动拼接。
