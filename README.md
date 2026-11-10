# MCDR-BotMono（Botもの）

基于 [MCDReforged](https://github.com/MCDReforged/MCDReforged) 和 [Carpet](https://github.com/gnembon/fabric-carpet) 的假人物品管理插件。为物品假人设置中文、英文或拼音别名，就能用简短命令召唤假人、取出物品、让假人下线。

> 君は道具ではなく、その名が似合う人になろんだ

例如，先给 `Fireworks` 假人装入烟花火箭并让它下线。旅行途中需要补充火箭时，在安全的位置输入 `!!bm 烟花火箭 all`，插件会在你身边召唤它，确认上线后让它扔出背包中的物品。

**别名只是对假人的索引。** 插件不会生成物品、识别或整理背包，也不会按别名筛选物品；物品需要事先由玩家实际放入假人背包。假人的背包由 Minecraft / Carpet 保存，插件只管理名字和别名。

## 特性

- **多别名映射**：登记名、带前后缀的游戏名、任意自定义别名均可使用，查找不区分大小写。
- **随身召唤与取物**：离线时在执行玩家的位置与朝向召唤，确认上线后再执行扔物品动作。
- **交互面板**：单行列表、详情、别名管理与简短操作反馈，常用按钮可直接点击。
- **分页与搜索**：每页 10 条，支持在线/离线筛选以及名称关键词搜索。
- **可靠的状态管理**：加载和服务器启动后同步已在线假人；玩家加入/退出事件更新状态，并保存服务端确认的名字大小写。
- **配置与数据分离**：原子写入、严格校验、配置热重载、权限控制；重载、卸载、删除或停服会取消未完成的动作。

本项目采用与 [BotKikai](https://github.com/Jerry-FaGe/MCDR-BotKikai) 一致的模块结构。Kikai 面向固定机器位置，Mono 面向随身物品假人，Mono 不保存召唤坐标。

BotMono 与 BotKikai 以 **1.0.0** 作为共同的稳定版起点。后续共同功能同步发版，独立修复各自递增补丁号；具体约定见 [版本与发布流程](.github/WORKFLOWS.md#版本约定)。

## 依赖与安装

- Python >= 3.10
- [MCDReforged](https://github.com/MCDReforged/MCDReforged) >= 2.12.0，推荐 >= 2.16.2
- [MinecraftDataAPI](https://github.com/MCDReforged/MinecraftDataAPI) >= 1.6.2
- Minecraft 服务端安装 [Carpet](https://github.com/gnembon/fabric-carpet)，并允许使用 `player` 命令

将发布的 `BotMono-v1.0.0.mcdr` 放入 MCDR 的 `plugins` 目录并加载。插件不要求开启 RCON。

这是全新的打包插件，插件 ID 为 `bot_mono`，默认命令前缀为 `!!bm`。首次加载会在 `config/bot_mono/` 创建默认配置和一份常用物品映射；之后修改过的 `bots.json` 会原样保留。旧的单文件版本、`BotMono.json`、`!!botmono`、MCDR 0.x / 1.x 兼容代码均不再使用，也不做自动迁移；安装时请移除旧插件文件，避免重复处理命令。

## 快速上手

首次安装已经登记了常用物品。先查看列表并召唤烟花假人，向它投放要储存的烟花火箭，再让它下线：

```minecraft
!!bm list
!!bm 烟花 spawn
!!bm 烟花 kill
```

需要取物时执行 `!!bm 火箭 all` 即可。内置映射覆盖 100 种物品，共 463 个名称和别名：

| 用途 | 部分内置物品 |
|---|---|
| 出行与补给 | 烟花火箭、鞘翅、末影珍珠、金胡萝卜、牛排、图腾、水桶、脚手架 |
| 建筑 | 石头、圆石、深板岩、泥土、沙子、玻璃、黑曜石、羊毛、混凝土、冰、原木 |
| 材料 | 铁锭、金锭、铜锭、钻石、红石粉、石英、黏液球、纸、火药、骨粉 |
| 红石与运输 | 活塞、黏性活塞、侦测器、中继器、比较器、漏斗、投掷器、铁轨、矿车、TNT |
| 存储与工具 | 箱子、潜影盒、末影箱、工作台、熔炉、铁砧、钻石工具、箭、剪刀 |

例如 `烟花火箭`、`烟花`、`火箭`、`huojian`、`firework_rocket` 都指向登记名 `Fireworks`；常见译名和写法也已覆盖，如 `黏性活塞` / `粘性活塞`。

默认的 `床`、`船`、`羊毛`、`混凝土` 分别指向红色床、橡木船、白色羊毛和白色混凝土。需要其他颜色、木种或用途时，管理员可以另行登记：

```minecraft
!!bm add BlueWool 蓝色羊毛
!!bm BlueWool alias add 蓝羊毛
!!bm BlueWool alias add lanyangmao
```

`add` 只登记名字，不需要读取玩家位置，也不会召唤假人。控制台也能登记。同一登记名再次执行 `add` 会保留原别名并追加新别名。

普通玩家可以执行：

```minecraft
!!bm 烟花火箭 spawn    # 在自己身边召唤假人
!!bm 烟花火箭          # 查看详情与快捷操作
!!bm 烟花火箭 one      # 扔出主手的一件物品
!!bm 烟花火箭 handall  # 扔出主手整组物品
!!bm 烟花火箭 all      # 扔出全部物品栏物品
!!bm 烟花火箭 kill     # 让假人下线，保留登记记录
```

三种取物命令都会在假人离线时自动召唤，无需先输入 `spawn`。假人已经在线时，`spawn` 不再召唤或移动它，取物命令则让它**在当前所在地**扔物品。插件不提供传送命令。

## 命令

`<mono>` 可填写登记名、游戏名或任意别名。`<name>` 是基础登记名；加上配置中的前后缀后，游戏名须为 3～16 个英文字母、数字或下划线。`<alias>` 是要添加或移除的单个别名，允许中文，但不允许空白和控制字符。

| 命令 | 说明 | 默认权限 |
|---|---|---|
| `!!bm` | 帮助 | guest (0) |
| `!!bm list [online\|offline] [page]` | 分页查看所有已登记的假人，可筛选在线/离线 | guest (0) |
| `!!bm list [online\|offline] search <关键词> [page]` | 搜索登记名、游戏名和别名 | guest (0) |
| `!!bm <mono>` | 详情与操作面板 | guest (0) |
| `!!bm <mono> spawn` | 在执行玩家身边召唤离线假人 | user (1) |
| `!!bm <mono> kill` | 请求让假人下线 | user (1) |
| `!!bm <mono> one` | 扔出主手的一件物品 | user (1) |
| `!!bm <mono> handall` | 扔出主手整组物品 | user (1) |
| `!!bm <mono> all` | 扔出全部物品栏物品 | user (1) |
| `!!bm add <name> <alias>` | 新增记录，或向已有登记名追加别名 | admin (3) |
| `!!bm del <mono>` | 删除记录，不让在线假人下线 | admin (3) |
| `!!bm <mono> alias` | 别名管理面板 | admin (3) |
| `!!bm <mono> alias add <alias>` | 添加别名 | admin (3) |
| `!!bm <mono> alias del <alias>` | 移除自定义别名，登记名和游戏名不可移除 | admin (3) |
| `!!bm reload` | 重载设置和假人数据，并重新同步在线状态 | admin (3) |

列表支持组合查询：

```minecraft
!!bm list
!!bm list 2
!!bm list online
!!bm list offline search 火箭
!!bm list online search stone 2
```

顶层管理词 `add`、`del`、`list`、`reload` 不可作为假人登记名、游戏名或别名。不同假人之间的登记名、游戏名和别名也不可冲突。

## 召唤与动作行为

- **玩家执行**：仅在需要召唤离线假人时，通过 MinecraftDataAPI 一次性读取玩家维度、精确位置和朝向；召唤时保留玩家执行身份，让 Carpet 使用玩家的游戏模式。位置获取失败会明确报错，不会改用控制台位置召唤。
- **控制台执行**：离线假人使用 `player <name> spawn in survival`，位置取 Carpet 的控制台默认位置；需要在身边取物时请由玩家执行命令。
- **上线确认**：使用加入事件或在线状态同步确认假人上线，达到超时时间仍未确认时终止后续动作。
- **并发操作**：同一个假人的动作依次执行，不会因为多人同时取物而重复发送召唤。后台队列有数量限制，满时会提示稍后重试。
- **操作反馈**：召唤成功显示“已确认上线”；下线与扔物品仅显示“请求已发送”，实际掉落数量与执行结果以游戏内为准。空的主手不会凭空产生物品。
- **取物映射**：`one` → `player <name> drop once`，`handall` → `player <name> dropStack once`，`all` → `player <name> dropStack all`。

## 配置

### `config/bot_mono/config.json`

```json
{
    "prefix_short": "!!bm",
    "spawn_max_wait_time": 10.0,
    "spawn_check_interval": 0.5,
    "bot_name_prefix": "",
    "bot_name_suffix": "",
    "permission": {
        "bot": 1,
        "list": 3
    }
}
```

| 配置项 | 默认值 | 含义 |
|---|---|---|
| `prefix_short` | `!!bm` | 命令前缀，不可含空白 |
| `spawn_max_wait_time` | `10.0` | 最长上线确认等待时间，单位秒 |
| `spawn_check_interval` | `0.5` | 等待期间检查停服/取消状态的间隔，单位秒；加入事件会立即唤醒等待 |
| `bot_name_prefix` | `""` | Carpet 假人名前缀 |
| `bot_name_suffix` | `""` | Carpet 假人名后缀 |
| `permission.bot` | `1` | 召唤、下线、取物的最低 MCDR 权限 |
| `permission.list` | `3` | 登记、删除、别名管理和重载的最低 MCDR 权限；不限制查看列表 |

前后缀需与 Carpet 配置一致，避免匹配不到真实游戏名。内置登记名最长 12 个字符，前后缀总长不超过 4 时，全部默认游戏名都能满足 16 字符限制；更长时需相应缩短受影响的登记名。权限范围为 0～4，分别对应 guest / user / helper / admin / owner。

### `config/bot_mono/bots.json`

```json
{
    "Fireworks": {
        "aliases": ["烟花火箭", "烟花", "火箭"]
    },
    "Stone": {
        "aliases": ["石头", "shitou"]
    }
}
```

- 对象的键是登记名，`aliases` 只保存附加别名，不重复存储登记名或游戏名；重复项按不区分大小写去重，保留首次出现的写法和顺序。
- `aliases` 可省略或写成 `[]`。登记名和游戏名始终可用于查找；列表与详情优先显示第一个别名，没有别名时显示登记名。
- 可选字段 `confirmed_name` 由插件自动维护，用于保存服务端确认的真实游戏名大小写。
- 不存储位置、朝向、在线状态或物品数据。不识别旧的 `nicknames` / `nick` 字段、别名数组布局或 Kikai 的坐标字段。
- 首次安装使用内置的 [默认物品映射](config/bots.default.json)；完整设置示例见 [配置示例](config/config.example.json)。默认映射只在 `bots.json` 不存在时写入，手动清空为 `{}` 后不会再次导入。

修改文件后执行 `!!bm reload`。若改了 `prefix_short`，需要执行 `!!MCDR plugin reload bot_mono` 重新注册命令树。

所有设置和假人记录通过校验后才会应用。重载失败时保留原文件和当前内存状态；假人数据损坏后暂停写入，修好文件并成功重载后恢复。保存使用同目录临时文件与原子替换，避免失败时留下半个 JSON 文件。

## 聊天栏交互

- 召唤、下线、取物、详情、列表导航与刷新：点击直接执行，后端仍会检查当前权限。
- 搜索、添加别名、移除别名、删除记录：点击填入命令，补充或核对后按回车执行。
- 鼠标悬浮列表名称可查看完整名字与别名，名称较长时仅缩短列表显示，不改变查找或按钮目标。

Minecraft 的聊天签名限制可能使纯原版客户端无法点击执行 MCDR 的 `!!` 命令。推荐服务端安装 [LetMeClickAndSendForServer](https://github.com/Fallen-Breath/LetMeClickAndSendForServer)，或玩家安装 [LetMeClickAndSend](https://github.com/Fallen-Breath/LetMeClickAndSend)。未安装时可以手动输入所有命令。修改前缀后，也需确保兼容模组的匹配规则覆盖新前缀。

## 开发与验证

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m mcdreforged pack --input . --output dist
```

目录分工：

- `bot_mono/__init__.py`：插件生命周期与玩家事件。
- `config.py` / `storage.py`：配置校验与原子 JSON 读写。
- `bot.py`：名字校验、玩家位置召唤、上线等待与物品动作。
- `bot_manager.py`：记录/别名索引、在线状态、持久化和后台任务。
- `command.py` / `view.py`：MCDR 命令树、权限与富文本面板。
- `utils.py`：MinecraftDataAPI 查询。

测试使用 MCDR 的真实命令树和富文本 API，Minecraft 服务端与 MinecraftDataAPI 查询由测试替身模拟。覆盖默认映射初始化、已有数据保护、玩家位置召唤、掉落命令、并发等待/取消、状态同步、数据错误与只读面板。CI 使用 Python 3.10 / MCDR 2.12.0 与 Python 3.14 / MCDR 2.16.2，并验证 `.mcdr` 包内文件与源码一致。工作流说明见 [.github/WORKFLOWS.md](.github/WORKFLOWS.md)。

## 致谢与协议

感谢 [Fallen_Breath](https://github.com/Fallen-Breath) 的 MCDReforged / MinecraftDataAPI，以及 Carpet 提供的假人功能。

[GPL-3.0 License](LICENSE)
