# Windows 安装包

安装包输出：`build/installers/Meow-0.1.0-Windows-x64-Setup.exe`。构建时保留对应 `.sha256` 和 `build-report.json`；版本号与输出路径由打包脚本控制。

默认按当前用户安装到 `%LOCALAPPDATA%\Programs\Meow`，支持中文向导、桌面/开始菜单快捷方式及 Windows 应用列表卸载。程序使用独立的 `%LOCALAPPDATA%\Meow.Windows` 存档，升级复用、卸载保留。不要将存档目录手动复制进发布目录。

完整安装包含 .NET 自包含运行环境、当前角色动画、Node/iroh 信箱组件，以及 Qwen2.5-0.5B-Instruct Q4_K_M 本地模型；精简安装不安装本地模型。缺少 VC++ v14.50 或更新的 x64 运行库时，向导调用随附微软官方安装程序，此一步会请求管理员权限。安装前应从角色右键菜单退出旧版；安装程序通过应用互斥量拦截运行中的版本，防止误以为启动了新版。

## 重建

准备 Inno Setup 7（ISCC.exe）、.NET 10 SDK、微软 VC++ x64 Redistributable、应用图标 ICO。默认工具路径见 `scripts/package_windows_installer.ps1`，均可通过参数覆盖。下载入口：[Inno Setup 官方网站](https://jrsoftware.org/isdl.php)、[微软运行库](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)。编译工具与运行库均应验证 Authenticode 签名；本打包脚本会拒绝没有有效微软签名的 VC++ 安装程序。

图标使用已有 `assets/icon.png` 转为包含 16、32、48、64、128、256 像素的 ICO，放在 `build/installer-dependencies/Meow.ico`。OpenCvSharp 与 OpenCV 的上游许可证放在该目录的 `OpenCvSharp-LICENSE.txt` 和 `OpenCV-LICENSE.txt`；本地模型与运行时预先通过 `scripts/prepare_windows_local.ps1` 准备，并将 llama.cpp 对应版本 LICENSE 保存为 `build/local-engine/LICENSE-llama.cpp.txt`。

```powershell
./scripts/package_windows_installer.ps1 -Version 0.1.0 -IncludeLocalModel
```

脚本每次在新的 staging 目录发布，不直接封装运行目录。它拒绝存档、私钥容器、快捷方式和调试文件，保留逐文件哈希清单，校验本地模型哈希。构建不会读取用户的云端密钥、对话或信箱数据。PNG 图集播放不需要 OpenCV 附带的 FFmpeg 视频 I/O 插件，安装负载不包含该可选 DLL；OpenCV 本体仍用于动作光流过渡。

当前安装包未配置代码签名证书；官方依赖签名不等于本应用安装包已签名。需要对外正式发行时，应为最终 EXE 配置自己的签名证书。
