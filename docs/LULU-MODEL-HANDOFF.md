# 最新噜噜模型：换电脑继续开发

同步日期：2026-11-13。仓库：`https://github.com/zsw20001005/Meow.git`，分支：`main`。

## 下载

先安装 Git 和 Git LFS，然后执行：

```powershell
git lfs install
git clone --branch main https://github.com/zsw20001005/Meow.git
cd Meow
git lfs pull
```

已有仓库时，在工作区改动妥善保存后拉取对应分支，再执行 `git lfs pull`。不要只使用 GitHub 的 Download ZIP：它可能只包含 LFS 指针。正常模型文件应有数十 MB，而不是一百多字节。

## 直接打开最新模型

使用 **Blender 4.5 LTS**（制作环境为 4.5.9）打开：

[`Lulu-Five-Motions-Preview.blend`](../prototypes/lulu-reference-model/image-to-3d/hunyuan-tpose-02/motion-set-01/Lulu-Five-Motions-Preview.blend)

该文件包含角色网格、22 根骨骼、五个独立 Action、预览相机和地面网格。打开及编辑模型无需访问生成服务，也无需原电脑上的 Codex 技能。

选择 `Lulu_Rig`，在 Dope Sheet 的 Action Editor 中切换动作，并设置对应时间轴范围：

| Action | 内容 | 帧范围（30 fps） |
| --- | --- | --- |
| `Lulu_Idle` | 待机呼吸 | 1–120 |
| `Lulu_LookAround` | 左右张望 | 1–144 |
| `Lulu_Wave` | 挥手 | 1–144 |
| `Lulu_WalkSteps` | 起步、行走、停下 | 1–128 |
| `Lulu_StepTurn360` | 交替踏步转身一圈 | 1–186 |

实际渲染效果见 [`lulu-five-motions.mp4`](../prototypes/lulu-reference-model/image-to-3d/hunyuan-tpose-02/motion-set-01/lulu-five-motions.mp4)。动作说明和检查结果位于同目录的 `README.md`、`manifest.json`、`playback-check.json`。

## 保留的源文件

以下路径均相对于 `prototypes/lulu-reference-model/image-to-3d/hunyuan-tpose-02/`：

- `lulu-tpose-raw.glb`：原始生成结果。
- `lulu-tpose-source.blend`：清理并归一化后的高模。
- `lulu-tpose-rig-input.blend` / `.glb`：约 20 万三角面的蒙皮输入。
- `rigged/lulu-tpose-mia-original.glb`：原始自动绑骨骼结果。
- `rigged/lulu-tpose-mia-import.blend`：修整骨架脚本的输入。
- `rigged/lulu-tpose-rigged-v5.blend`：蒙皮修整后的骨架。
- `rigged/Lulu-Tpose-Rig-Preview.blend`：五组动作制作前的关节测试底稿。
- `motion-set-01/Lulu-Five-Motions.blend`：最新五组动作，不带预览地面。
- `../references-v2/t-pose-views-v1/`：实际使用的多角度参考图，包含尾巴。

模型及 GLB 使用 Git LFS。可重建的逐帧 PNG、重复下载、自动备份未上传，原电脑上的文件仍保留。

本次也同步 Windows 客户端的未提交开发改动，以及 `prototypes/lulu-rig/`、`prototypes/shared-rig/`、`prototypes/lulu-reference-model/` 中的历史源模型、实验脚本和预览资料。历史版本用于追溯，继续本轮工作仍优先打开上面列出的五动作模型。完整检出包含数 GB 模型资料，需要等待 Git LFS 下载完成。应用构建入口见根目录 README；本地模型权重、编译产物和用户配置按原有规则单独准备。

## 当前限制与脚本

当前是灰模身体动作原型，没有完整材质、面部表情或独立手指控制。Blender 的保体积蒙皮与关节平滑修正不能由标准 GLB 完整表达；`rigged/lulu-tpose-rigged-lbs.glb` 是兼容导出，只有早期关节测试动画，不能替代最新五动作 `.blend`。

制作与验证脚本随模型保留。`check_motion_set.py` 和 `render_motion_set.py` 使用脚本所在目录定位模型，可通过 Blender 的 `--background --python` 执行。重新渲染会创建本机 `motion-set-01/frames/` 缓存。

部分早期制作脚本仍包含原电脑的路径：`inspect_model.py` 从 `shape-result.json` 读取下载位置；`build_rig.py`、`make_motion_set.py` 等依赖 `blender-modeler` 技能的 `render_views.py` / `check_geometry.py`；`encode_motion_set.py` 依赖 FFmpeg 和微软雅黑字体。重新运行这些制作脚本前需调整路径并准备依赖，直接打开已保存的 `.blend` 不受影响。`generate_remote.py` 会向第三方服务上传参考图，不是打开模型的必要步骤。

桌面客户端仍使用原有二维动画素材；旧角色和本机旧模型没有删除。
