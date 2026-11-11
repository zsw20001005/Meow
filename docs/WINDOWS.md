# Windows 客户端

源码在 `windows/Meow.Windows`（C# / WPF / .NET 10），通信辅助进程在 `windows/Meow.MailBridge`。Mac Swift 版独立保留，Windows 当前目标为 x64。

Windows 安装向导包及重建方法见 [Windows 安装包](WINDOWS-INSTALLER.md)。安装包包含运行环境，可选择是否安装轻量本地模型，升级和卸载保留本机存档。

## 功能

- 桌面角色张噜噜：黄色毛绒水豚、圆框眼镜、西瓜头、橙色短裤；透明置顶、拖动抛出、呼吸、抚摸、喂西瓜、睡眠和散步。
- 走路、挥手、玩球各有16张连续关键帧；绘制跟随屏幕刷新，相邻帧使用预乘透明度插值。开心、喜欢、生气、委屈、害羞、惊讶、困倦、饥饿、好奇、晕乎乎分别使用独立素材。右键的“互动动作”和“小表情”可直接体验；喂食/玩耍后开心、转圈后晕乎乎、抚摸后亲昵。
- 跳舞、转圈、打滚、挥爪、点头、摇头、伸懒腰、跳跃、过来、回地面、玩耍等显式指令。
- 边缘贴墙与靠近探出、窗口顶部停留及窗口消失后掉落；按所在显示器工作区约束位置。
- 云端流式聊天、取消与历史；DPAPI 加密 API Key。
- 多服务商配置：方舟、GPT、Claude、Gemini、DeepSeek、通义千问、Kimi、GLM、Grok、MiniMax、硅基流动、OpenRouter，以及自定义 OpenAI 兼容接口；每个服务商分别保存地址、模型和加密密钥。
- 手动小本本、自动提取主人资料及原文证据；替换事实保留历史，可删除单条资料。
- 对话创建/修改/完成/取消/列出备忘录；时间或目标不明时追问，十分钟内下一轮可补全。到点云端提醒，失败用本机文案；每半小时判断提前提醒。
- 微博抓取、偏好选题、原始来源、手动刷新及北京时间11/16/19点分享；恢复时只补当前对应小时。
- 主动闲聊、夜间睡眠、自主跳窗开关。
- iroh 1.2.0 信箱：固定身份、双向绑定、已读、待寄重试、保存回执、重复去重、解除绑定取消待寄、未读抱信和报信。
- 本地推理：llama.cpp CPU + Qwen2.5-0.5B-Instruct Q4_K_M，或其他本机OpenAI兼容服务。后台智能功能仍按开关使用云端。

## 使用与数据

运行 `build/Meow-Windows-Lulu/Meow.exe`。升级前先退出正在运行的旧版，否则单实例机制会打开旧进程。双击噜噜聊天，右键打开互动菜单和各功能窗口；有未读信时双击进入信箱。原 Windows 存档、信箱身份和密钥继续使用。可直接说“张噜噜，笑一个吧”“装生气”“打个哈欠”触发表情。

开发预览：`Meow.exe --character-preview` 打开独立的形象和动作对照窗口，不读取账号或存档、不联网；关闭时写出 `preview-performance.txt`，记录渲染回调间隔（并非GPU呈现帧率）。`--rendercheck` 输出透明背景、动作关键帧与页面截图。角色为二维序列帧，非可自由旋转的三维模型；Mac Swift 客户端仍使用原角色。
热点、信箱、主动闲聊、自主跳窗默认关闭；自动记忆、提前提醒、夜间睡眠默认开启，可在设置调整。

信箱需要两端启用且各绑定一次对方设备码。已送达代表对方保存，不代表已读。离线信件约每30秒重试，没有服务器代收。正文不提交模型。解除绑定保留历史并取消待寄。

本地模式：设置的“对话模型”选择“本地模型”，点击“保存模型设置”。点击“启动随附的本地模型”可提前启动；发送第一条消息也会启动随附服务。默认 `http://127.0.0.1:8080/v1`，模型别名 `local`。应用退出会关闭自己启动的服务。轻量模型能力弱于云端，可替换兼容GGUF模型/服务，不复用Mac MLX权重。

备忘录使用本机时区，应用运行时约30秒检查，退出不提醒，恢复后补处理。手动小本本与自动资料独立维护，手动文本在编辑框修改/删除。

存档：`%LOCALAPPDATA%/Meow.Windows/state.json`。密钥与信箱私钥使用当前Windows账号DPAPI加密，其他业务数据为明文。`mail-inbox` 收件记录用于重复投递去重，保留绑定期间勿单独清空。

云端聊天发送最近30条消息与记忆；自动记忆发送当前原文及已有事实；备忘录规划发送请求及备忘录；提醒/热点/闲聊发送相关事项或偏好，会消耗额度。纯离线使用应关闭云端功能和信箱/热点。

## 构建

### 模型 API 设置

多接口版本运行 `build/Meow-Windows-MultiAPI/Meow.exe`（先退出正在运行的旧版）。右键小猫 → 设置 → 云端模型 → 选择模型服务商，填写该账户可用的**文本对话模型 ID**和 API Key，点击“测试连接”，成功后“保存模型设置”。测试只发送一句测试语，不发送历史和记忆；测试成功不会自动保存。新服务商的模型 ID 留空，避免预填已经下线或未授权的型号。

原有存档默认保留为方舟配置。切换下拉框只编辑草稿，保存后才应用；切回服务商可恢复其配置。密钥留空只保留**同服务商、同域名**的已保存密钥，修改接口域名需重新输入密钥。聊天回复进行中不能切换，先结束或停止回复。

| 服务商 | 默认 Base URL | 协议 |
|---|---|---|
| 火山方舟 | `https://ark.cn-beijing.volces.com/api/plan/v3` | Chat Completions + 方舟 thinking |
| OpenAI GPT | `https://api.openai.com/v1` | Chat Completions，使用 max_completion_tokens |
| Anthropic Claude | `https://api.anthropic.com/v1` | 原生 Messages，独立 system 和 x-api-key |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai` | 官方 OpenAI 兼容接口 |
| DeepSeek | `https://api.deepseek.com/v1` | Chat Completions |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Chat Completions |
| Kimi | `https://api.moonshot.cn/v1` | Chat Completions |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | Chat Completions |
| xAI Grok | `https://api.x.ai/v1` | Chat Completions |
| MiniMax | `https://api.minimax.io/v1` | Chat Completions，reasoning_split=true |
| 硅基流动 | `https://api.siliconflow.cn/v1` | Chat Completions |
| OpenRouter | `https://openrouter.ai/api/v1` | Chat Completions |
| 自定义 | 手动填写 HTTPS 地址 | Chat Completions |

地址可填基础路径或完整 `/chat/completions`（Claude 为 `/messages`）端点。地区、套餐、代理或工作空间不同，按自己的服务商文档调整地址。兼容接口只发送通用参数；方舟思考开关仅对方舟有效，其他服务商采用模型默认思考策略。普通云端输出预算为 8192 tokens（推理模型可能将思考计入），达到上限会报错而不把不完整结果当作成功。

聊天、自动记忆、智能备忘、提醒文案、热点和主动闲聊均使用已保存的云端服务商。本地聊天仍保留本机 llama.cpp 接口，后台云端功能行为不变。这里接入的是文本对话能力，不包含图像生成、语音、视频、厂商托管工具或仅支持 Responses 的模型。Mac Swift 客户端此次未改动。

验证包含请求地址/鉴权/载荷、两类 SSE、错误/截断/取消、旧存档兼容、密钥隔离和设置界面切换；没有各服务商真实密钥的情况下，不宣称已全部联网实测。

协议参考：[OpenAI](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、[Claude](https://platform.claude.com/docs/en/api/messages/create)、[Gemini](https://ai.google.dev/gemini-api/docs/openai)、[DeepSeek](https://api-docs.deepseek.com/)、[百炼](https://help.aliyun.com/en/model-studio/base-url)、[MiniMax](https://platform.minimax.io/docs/api-reference/text-openai-api)。其余服务商入口在设置页“服务商文档”。

### 构建命令

需要 .NET 10 SDK、Node.js 20.3+、PowerShell 7。

```powershell
./scripts/prepare_windows_mail.ps1
dotnet build windows/Meow.Windows/Meow.Windows.csproj -c Release -r win-x64
./scripts/package_windows.ps1 -SelfContained
```

包括本地引擎和约491MB模型：

```powershell
./scripts/prepare_windows_local.ps1
./scripts/package_windows.ps1 -SelfContained -IncludeLocalModel
```

输出 `build/Meow-Windows-x64`，分发整个目录。`-SelfContained` 包含.NET运行时。项目内SDK可传 `-Dotnet ./.build-tools/dotnet/dotnet.exe`。下载验证官方哈希，许可在 `mailbridge/licenses`、`local-engine`。

## 验证

使用输出目录的exe；PowerShell用 `Start-Process -Wait` 等待，或用 `dotnet Meow.dll`：

- `--selftest`：离线检查，包含多服务商请求、SSE、地址、指令、DPAPI、配置隔离及存档。
- `--mailcheck`：临时身份与回环地址真实双向QUIC、保存回执、去重及重启身份，不访问公网中继或真实联系人。
- `--cloudcheck`：当前配置的短连接测试，不发送个人资料，消耗少量额度。
- `--featurecheck`：当前云端配置、隔离存档测试备忘录、追问、记忆及热点，消耗额度但不写用户业务数据。
- `--localcheck`：随附CPU模型流式回复，不联网。
- `--rendercheck`：隔离示例存档、六个窗口的 1x/2x PNG、21 种猫咪状态、动作帧、左右贴墙和抱信快照，输出到 `visual-checks`。在仓库内运行时额外检查站立猫的前景轮廓与 `assets/pet-states.png` 的重合率。
- `--visual-preview`：独立的示例 UI 预览，不读取正式存档；用于手工检查交互，不能替代正常启动。

仓库内还可以运行 `build/Meow-Windows-MacUI/mailbridge/node.exe scripts/test_windows_mail_network.mjs`，用两个临时身份检查正式 N0 设备发现、双向收信及保存回执；启动后的设备发现尚未就绪时最多重试两次，结果保存到 `build/mail-network-results.json`。`scripts/probe_windows_mail_network.mjs` 单独检查公网中继连接。这些检查不读取真实绑定或寄给联系人，但两个测试端都在同一台电脑上，不能证明两台不同网络的电脑已互通。

结果在执行文件旁的 `*-results.txt`。编译和基础集成测试已通过，以实际结果文件为准。

## Mac 界面复刻

`PetDrawing.cs` 使用 `PetView.swift` 的原始 200×200 矢量路径、色值、身体变换和动作时长，常规窗口为 230×230；贴墙使用 `WallDock.swift` 的裁切坐标。气泡独立悬浮，脚底位置按原版 170/200 计算。

聊天恢复 320×420；设置 410×660、小本本 540×660、备忘录 600×700、热点 560×700、信箱 700×680，使用独立窗口、圆角卡片、粉色开关及原版布局。信箱的绑定和写信也独立打开。旧有聊天、密钥、信箱与本地推理后端保留。

Windows 使用本机中文字体和彩色 Segoe UI Emoji，未分发 Apple 字体。两平台的字体度量、Emoji 图案、抗锯齿、原生日期输入和系统弹窗仍不同；随机粒子与物理交互也不能据静态图宣称逐帧一致。本次检查了仓库参考图、窗口渲染和 Windows 实际交互，未在 macOS 上运行两端 UI 做逐像素验收，因此不声称所有画面像素完全相同。

仍需实机验收：Windows 与 Mac 跨网络互寄、混合 DPI 多屏、休眠恢复、不同应用窗口遮挡。模型规划可能理解有误，可在页面核对修正。微博接口受登录与站点限制影响，失败提示并退避重试。安装器、签名和自动更新尚未配置。
