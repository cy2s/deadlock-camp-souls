# Deadlock 营地 Souls

按住 `Tab` 打开的 Midtown 地图上，已刷新的点位显示**按当前对局时间估算的满营 Souls**。数字用游戏的 12 px 数字字体，三位数底牌宽 24 px，达到四位时加宽至 28 px。偏移较远的标签用细线指向营地。绿色、黄色、浅红色分别用于小、中、大营地，紫色用于含老虎机的营地。

- **野怪营地**按配置的怪物只数累加。例如车库地面层 `2×43 + 71` 的基础值为 `157`，在 5:00 按 `2×45 + 74` 显示 `164`。
- **老虎机及混合营地**按满营配置累加。例如单台在 8:00 约值 `337`，在 20:00 约值 `377`。

收益取顶部原生对局计时器的整分钟数，每分钟按基础值增加 `1.08%`。野怪按单只截断后累加，老虎机按单台总额取近似整数。数字按满营估算，实际到账会受剩余数量、分配和逐次取整影响。[野怪收益计算](https://www.dltimes.com/articles/city-never-sleeps-spawn-timers) · [老虎机结算规则](https://deadlock.wiki/Sinner%27s_Sacrifice#Souls)

只有原生小地图面板提供可见、激活的营地标记，并能唯一对上点位，才显示数字。清空到重刷之间跟随游戏原生标记隐藏。读不到对局时钟或营地状态时会隐藏相应数字。

`camps.json` 的 51 个点位按地图 ID 关联 Deadlock API 的客户端 `6871` 坐标和 Deadlock Vault 的营地阵容。`counts` 依次为小怪、中怪、大怪、老虎机的数量。11 月 26 日补丁将单只野怪的基础值改为 `43 / 71 / 189`。单台老虎机的满额估算用 `155×2 = 310`，合计敲击和打碎两部分。[官方补丁说明](https://store.steampowered.com/news/app/1422450/view/680768104678032838) · [地图数据 API](https://api.deadlock-api.com/v1/assets/map?client_version=6871) · [营地阵容](https://deadlockvault.net/map/camps) · [NPC 数据](https://raw.githubusercontent.com/SteamTracking/GameTracking-Deadlock/77b862290ad3050cafd2e9c3f47e0532e9d6dcfd/game/citadel/pak01_dir/scripts/npc_units.vdata)

## 安装与卸载

从 [GitHub Releases](https://github.com/cy2s/deadlock-camp-souls/releases) 下载测试 ZIP，安装时任选一个包。本页下方也提供本地构建命令。

- **Tab 版**按住 `Tab` 时显示所有已刷新的营地和老虎机收益，松开时隐藏。
- **悬停试验版**按住 `Tab` 后，把鼠标移到营地或老虎机的原生图标上，只显示这个点位的收益。移开鼠标或松开 `Tab` 时隐藏。

关闭游戏，在 Deadlock Mod Manager 的 `Mods Library → Add Local Mod` 导入选中的 ZIP，然后启用。手动安装时，解压 ZIP，把其中的 `pak99_dir.vpk` 复制到 `Deadlock/game/citadel/addons/`。如果装过之前的营地收益版本，用选中的包替换。如果同名文件属于其他模组，给本包选一个空闲的 `pakNN_dir.vpk` 文件名。[管理器导入说明](https://docs.deadlockmods.app/using-mod-manager/library#add-local-mods)

如果是第一次手动安装模组，在 `Deadlock/game/citadel/gameinfo.gi` 的 `SearchPaths` 区块中，在 `Game citadel` 之前添加 `Game citadel/addons`。重新启动游戏，可在自定义对局按 `Tab` 查看营地。卸载时移除本包即可。[社区安装文档](https://wiki.divineskins.gg/en/docs/deadlock/getting-started#install-mods-without-a-manager)

## 构建与验证

使用 Python 3.10 或更高版本。构建时会取 `6871` 对应的原生小地图布局，也可以用 `--minimap-layout` 指定同一版本的解包 XML。

```sh
python build.py
python build.py --hover-only
```

`dist/` 的 VPK 包含小地图布局、样式和 Panorama 脚本。若安装了同样覆盖 `hud_minimap.vxml_c` 的模组，两份布局需要合并才能同时生效。游戏更新后需核对营地组成、坐标和布局。[原生 HUD 小地图布局](https://github.com/SteamTracking/GameTracking-Deadlock/blob/77b862290ad3050cafd2e9c3f47e0532e9d6dcfd/game/citadel/pak01_dir/panorama/layout/hud_minimap.xml) · [原生小地图样式](https://github.com/SteamTracking/GameTracking-Deadlock/blob/77b862290ad3050cafd2e9c3f47e0532e9d6dcfd/game/citadel/pak01_dir/panorama/styles/hud_minimap.css)

已用 Source 2 Viewer 21.1 校验两个 VPK 并读回三项资源。模拟覆盖时间变化、清空隐藏、重刷恢复、Tab 开关和悬停切换。按 360 px 布局同时摆放 51 个标签，即使全部按四位数宽度计算也无重叠。本机无 Deadlock 客户端，尚未确认 `6871` 的实际对局是否对 Panorama 暴露逐点位的活动标记，以及营地图标是否提供悬停状态。缺少所需标记或状态时，收益会保持隐藏。Tab 加载、实机缩放、阵营翻转和坐标对齐也待实机验证。
