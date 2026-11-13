# 可复用骨骼角色候选

已下载并检查 Quaternius 的熊猫和粉发兔子。来源：https://quaternius.com/packs/sushirestaurantkit.html ，许可 CC0：https://creativecommons.org/publicdomain/zero/1.0/ 。原始 glTF 位于 `assets/sushi-original`，未修改。这里是独立原型，没有替换噜噜/高喵喵，也没有删除旧素材。

两个角色各有 43 个蒙皮关节（含根与控制节点），骨骼名称与父子结构一致，具有独立四肢、手指。尺寸和绑定姿势略有不同，所以通过相对绑定姿势映射动作，不能把“同名骨骼”当作无条件通用。

`build_shared.py` 将原资源拆成：

- `assets/runtime/Panda.glb`：232,352 字节，零内嵌动画。
- `assets/runtime/Rabbit_Pink.glb`：331,748 字节，零内嵌动画。
- `assets/runtime/shared-motions.glb`：824,556 字节，共用 30 段原作者动画，没有角色网格。

这三份合计约 1.32 MiB，不含 Three.js 播放器和原始归档。网页同时播放两个独立蒙皮角色，实际只加载一份动作库。模型本身的骨骼/绑定信息仍需各自保留；节省的是重复的动作关键帧和视频帧。

运行 `node prototypes/shared-rig/server.mjs`，打开 http://127.0.0.1:8432/ 。基础预览提供待机、走路、挥手、点头、摇头；可同步对比、单角色显示、显示骨骼、暂停和调速。

验证：`node --experimental-loader ./prototypes/lulu-rig/three-loader.mjs prototypes/shared-rig/check-shared.mjs`。检查角色包没有动画、库有 30 段、骨骼结构对应、实际蒙皮顶点有限且动作可见、快速切换零时间不跳变。结果 `shared-checks.json`。静态 Cycles 候选渲染由 `model.py` 制作，使用原作者 Idle；它不是网页截图，也不冒充共享映射的视觉验收。

限制：这些是低多边形卡通替代角色，不是噜噜的高还原模型。当前只验证部分基础动作；Jump 和坐下/起身是分段动作，不能直接首尾循环。床铺、拿西瓜/球、表情、服装和现有 Windows 播放器都尚未适配。数值检查不等于全部动作已经自然或无穿插。
