# Windows 安装包

## 模块化安装（0.3.0）

运行 `./scripts/package_windows_extensions.ps1` 生成 `build/installers/modular-0.3.0/` 下五个独立安装文件。它使用最新的低内存帧缓存播放器，不降低动画分辨率或帧率。所有原始形象素材（包括之前的高喵喵）、源代码及历史安装包保留；仅在新发布负载中按清单选择运行所需图集，被高清图集替代的文件仍留在原项目和构建 staging 中。

| 文件后缀 | 内容 |
| --- | --- |
| `core-Setup.exe` | 必装：自包含运行库、云端聊天、小本本/备忘录、现有噜噜形象及待机/走路/聊天/挥手/开心/思考/拖动/下落/落地/跳跃/基础睡觉/贴边 |
| `motion-Setup.exe` | 可选：吃瓜、玩球、转圈、跳舞、打滚等其余动作表情 |
| `bed-Setup.exe` | 可选：走到床边、上床、盖被、睡眠呼吸、叫醒、离床 |
| `mail-Setup.exe` | 可选：Node/iroh 信箱通信，不影响本地已有信件和草稿 |
| `model-Setup.exe` | 可选：Qwen 本地模型及推理引擎；云端 API 用户不需要 |

先安装主包，再将需要的扩展安装到同一目录。安装器尝试从主程序卸载登记中定位目录，同时校验动画清单兼容标识。无主程序或标识不匹配时，包括静默安装在内都会拒绝写入扩展。安装前退出噜噜，安装后重启；不支持运行中热替换。设置顶部显示扩展状态，缺少动作时明确提示安装动作表情包，缺少床铺时沿用基础睡觉动画。

各包拥有不重叠的文件清单、独立的卸载身份及 `uninstall-{pack}` 目录，可在 Windows“已安装的应用”中分别卸载。主包与旧安装使用同一身份，升级不会主动删除旧版本已有资源；因此覆盖完整版本后，磁盘占用不会自动变成基础包大小。要回收旧资源空间可先卸载旧程序，再选择性安装。个人存档目录仍在 `%LOCALAPPDATA%\Meow.Windows`，不属于任何包的卸载范围。

每包提供 SHA256、逐文件清单和汇总 `build-report.json`。`-SkipLocalModel` 可跳过本地模型包构建。运行 `./scripts/check_windows_extensions.ps1` 检查文件归属与哈希、基础/完整资源下的实际渲染、缺包提示、安装前置条件、补装、扩展单独卸载及基础包重装。测试使用同一 Inno 模板的隔离模式：不登记到 Windows 应用列表、不创建快捷方式、不启动真实账号，使用单独互斥量；实际发行包的注册项与快捷方式不在该隔离测试中创建。

```powershell
./scripts/package_windows_extensions.ps1 -Version 0.3.0
./scripts/check_windows_extensions.ps1 -Report build/installers/modular-0.3.0/build-report.json
```

0.3.0 最终文件大小：基础包 223,908,522 字节（213.5 MiB），动作表情包 193,332,319 字节（184.4 MiB），床铺包 207,611,605 字节（198.0 MiB），信箱包 30,232,669 字节（28.8 MiB），本地模型包 496,323,860 字节（473.3 MiB）。基础包相较之前约 786 MiB 的独立精简包减少约 73%；安装全部扩展仍需下载各包总和，拆包本身不意味着全部素材变小。具体文件哈希和隔离验证记录以输出目录中的报告为准。

安装包输出：`build/installers/Meow-0.1.0-Windows-x64-Setup.exe`。构建时保留对应 `.sha256` 和 `build-report.json`；版本号与输出路径由打包脚本控制。

当前独立精简版为 `build/installers/Meow-0.1.2-Windows-x64-Lite-Setup.exe`，已使用噜噜图标及带版本号的图标路径，不带 GGUF 权重和 llama.cpp 本地引擎，保留全部动画、云端聊天、信箱与运行库。它是单独文件，不覆盖已交付的完整版；新的构建报告与检查报告以对应安装包名称命名。重建命令为 `./scripts/package_windows_installer.ps1 -Version 0.1.2`，不传 `-IncludeLocalModel`。与完整版共用安装身份、存档和安装目录，覆盖旧完整版不会自动清除已有模型；需要回收旧模型空间时应先卸载再安装精简版，卸载仍保留用户存档。

默认按当前用户安装到 `%LOCALAPPDATA%\Programs\Meow`，支持中文向导、桌面/开始菜单快捷方式及 Windows 应用列表卸载。程序使用独立的 `%LOCALAPPDATA%\Meow.Windows` 存档，升级复用、卸载保留。不要将存档目录手动复制进发布目录。

完整安装包含 .NET 自包含运行环境、当前角色动画、Node/iroh 信箱组件，以及 Qwen2.5-0.5B-Instruct Q4_K_M 本地模型；精简安装不安装本地模型。缺少 VC++ v14.50 或更新的 x64 运行库时，向导调用随附微软官方安装程序，此一步会请求管理员权限。安装前应从角色右键菜单退出旧版；安装程序通过应用互斥量拦截运行中的版本，防止误以为启动了新版。

## 重建

准备 Inno Setup 7（ISCC.exe）、.NET 10 SDK、微软 VC++ x64 Redistributable、应用图标 ICO。默认工具路径见 `scripts/package_windows_installer.ps1`，均可通过参数覆盖。下载入口：[Inno Setup 官方网站](https://jrsoftware.org/isdl.php)、[微软运行库](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)。编译工具与运行库均应验证 Authenticode 签名；本打包脚本会拒绝没有有效微软签名的 VC++ 安装程序。

图标通过 `scripts/build_lulu_icon.py` 从当前普通待机的正面噜噜导出，保持现有形象及透明底，包含 16、24、32、48、64、128、256 像素。产物为 `windows/Meow.Windows/Assets/Lulu.ico`，同时嵌入程序 EXE，并用于安装包、卸载入口及快捷方式。此前已交付的完整版保持原文件，之后重建会使用噜噜图标。OpenCvSharp 与 OpenCV 的上游许可证放在 `build/installer-dependencies` 的 `OpenCvSharp-LICENSE.txt` 和 `OpenCV-LICENSE.txt`；本地模型与运行时预先通过 `scripts/prepare_windows_local.ps1` 准备，并将 llama.cpp 对应版本 LICENSE 保存为 `build/local-engine/LICENSE-llama.cpp.txt`。

```powershell
./scripts/package_windows_installer.ps1 -Version 0.1.0 -IncludeLocalModel
```

脚本每次在新的 staging 目录发布，不直接封装运行目录。它拒绝存档、私钥容器、快捷方式和调试文件，保留逐文件哈希清单，校验本地模型哈希。构建不会读取用户的云端密钥、对话或信箱数据。PNG 图集播放不需要 OpenCV 附带的 FFmpeg 视频 I/O 插件，安装负载不包含该可选 DLL；OpenCV 本体仍用于动作光流过渡。

当前安装包未配置代码签名证书；官方依赖签名不等于本应用安装包已签名。需要对外正式发行时，应为最终 EXE 配置自己的签名证书。

## 本次验证（2026-11-11）

0.1.0 安装包大小 1,324,503,329 字节。在独立目录完成完整安装、覆盖安装及卸载；813 个安装文件的 SHA256 与构建清单一致。桌面/开始菜单快捷方式和卸载注册项均验证创建与移除。已安装程序的 `--selftest`、`--edgecheck`、`--bed-entrycheck`、`--localcheck` 全部通过，随附 Node/iroh 原生模块加载通过。安装、检查、升级、卸载前后的真实用户存档哈希一致，测试结束恢复原 EdgeBright 桌面版本。

记录在 `build/installers/verification.txt`。测试脚本为 `scripts/check_windows_installer.ps1`，运行前需要指定当前程序路径，且会拒绝覆盖已存在的正式安装注册项与快捷方式。本机已有 VC++ 运行库，因此缺少运行库时的管理员安装分支未在全新 Windows 虚拟机实测；精简组件选择也尚未单独安装验证。

0.1.1 独立精简包大小 824,148,487 字节，较原完整包减少 500,354,842 字节（约 37.8%）。已检查无 `local-engine` 目录和 GGUF 文件，打包的 ICO 与源图标哈希一致，并从程序 EXE 与最终安装包实际提取图标确认均为噜噜。独立负载副本通过 `--selftest`、`--edgecheck`、`--bed-entrycheck` 以及 Node/iroh 加载检查。用户此时已在运行 `D:\Software\Meow\Meow.exe`，本次未执行会影响其安装注册项的安装/卸载烟雾测试，当前应用保持运行。精简版安装向导沿用之前验证过的安装流程，使用单一精简组件，不展示本地模型选项。

0.1.2 修复升级后的桌面旧图标缓存：已安装的 0.1.1 EXE 与 ICO 哈希均与发布负载一致，但快捷方式继续使用旧版同名的 `Meow.ico` 路径。新包改用 `Lulu-0.1.2.ico`，桌面、开始菜单、卸载入口同时引用版本化图标文件；之后升级也使用对应版本路径。本机已有快捷方式已改指向内容相同的新路径 `D:\Software\Meow\Lulu-0.1.1.ico`，变更前快捷方式备份在 `build/icon-cache-check`，未重启角色或资源管理器。检查脚本新增实际快捷方式图标文件存在且为版本化路径的验证。
