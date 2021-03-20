# MCDR-BotMono（Botもの）

适用于[MCDR](https://github.com/Fallen-Breath/MCDReforged)的将输入的英文，中文（甚至拼音）指向同一假人并提供操作界面和简化指令的插件。
请根据自己的MCDR版本选择安装哪个文件，不带后缀的支持MCDR 0.x,带后缀的支持MCDR 1.x。
需要安装前置插件[PlayerInfoAPI](https://github.com/TISUnion/PlayerInfoAPI)（MCDR 0.x）或[MinecraftDataAPI](https://github.com/MCDReforged/MinecraftDataAPI)（MCDR 1.x）。

> 君は道具ではなく、その名が似合う人になろんだ

试想一下，有一天你在家里召唤出一个假人`Fireworks`并给他扔了好多`烟花火箭`，然后kill掉。在未来的某一天你出去旅行，飞到半路发现火箭用完了，你降落在一个荒岛上，这时候你就可以用`/player fireworks spawn`召唤出假人后`/player fireworks dropStack all`让其扔出身上所有的`烟花火箭`。这相当于一个容量可观，随叫随到的末影箱。

本插件的本质作用是把`/player fireworks spawn`和`/player fireworks dropStack all`两条指令封装成`!!bm 烟花火箭 all`这一条（`烟花火箭`这一参数可以替换成`fireworks`，`烟花`，`火箭`或自定义字符串）。

当然，使用假人**暂时的**，**应急的**存取物品只是插件的一种用法，具体来用它做什么请自行斟酌（其实之前想给这个插件取名“假人全物品”的，后来想想还是宁愿啰嗦一点尽可能描述清楚本质，让用户来决定怎么使用吧）。

```MCDR(虽然知道不可能会支持但还是写上了23333)
本插件中!!bm与!!botmono效果相同，两者可以互相替换
!!bm 显示本帮助信息
!!bm list 显示由本插件召唤出的假人列表
!!bm reload 重载插件配置
!!bm <mono> 输出一个可点击的界面，自动根据假人是否在线改变选项
!!bm <mono> spawn 召唤一个用于存储<mono>的假人
!!bm <mono> kill 干掉用于存储<mono>的假人
!!bm <mono> here 将用于存储<mono>的假人传送到自己身边(为避免争议，会有和谐版本BotMono_safe.py去掉此功能)
!!bm <mono> one 假人扔出一个手中物品（执行此条前无需执行spawn，如假人不存在会自动创建）
!!bm <mono> all 假人扔出身上所有物品（执行此条前无需执行spawn，如假人不存在会自动创建）
!!bm <mono> handall 假人扔出手中所有物品（执行此条前无需执行spawn，如假人不存在会自动创建）
```

## 功能补充
* `!!bm list`: 输出一个类似下面的界面，可以通过点击进行操作（只显示通过本插件召唤的假人）。
  ```MCDR
  当前共有3个假人在线
  ----------- piston -----------
  此假人存放: ['piston', '活塞']
  [传送]  [扔出所有]  [扔出一个]  [扔出手中]  [下线]  
  ----------- sand -----------
  此假人存放: ['sand', '沙子']
  [传送]  [扔出所有]  [扔出一个]  [扔出手中]  [下线]  
  ----------- repeater -----------
  此假人存放: ['repeater', '红石中继器', '中继器']
  [传送]  [扔出所有]  [扔出一个]  [扔出手中]  [下线]
  ```
* `!!bm reload`: 重载[BotMono.json](https://github.com/Jerry-FaGe/MCDR-BotMono/blob/master/BotMono.json)配置文件，用于用户修改配置。配置文件详见下文**关于配置文件**
* `!!bm <mono>`: 输出一个可点击的界面，自动根据假人是否在线改变选项
  * 假人在线:
    ```
    ----------- fireworks 在线 -----------
    此假人存放: ["fireworks" ,"烟花", "火箭", "烟花火箭"]
    [传送]  [扔出所有]  [扔出一个]  [扔出手中]  [下线]  
    ```
  * 假人离线:
    ```
    ----------- fireworks 离线 -----------
    此假人存放: ["fireworks" ,"烟花", "火箭", "烟花火箭"]
    [召唤]  [扔出所有]  [扔出一个]  [扔出手中]  
    ```
* `!!bm <mono> here`: 只能将假人传送给自己，不能把自己传给假人。这个功能本来是插件初步完成之后为了完善功能加上的，所谓"传送"，本质也就只是把`/player xxx kill`后`/player xxx spawn`这两条指令封装成一条`!!bm <mono> here`而已。结果全写完之后拿去跟人讨论被人抓住传送这点不放群体批斗，根本没有人在乎你插件是干什么的，人们只在乎你会传送。怕了怕了，[和谐版](https://github.com/Jerry-FaGe/MCDR-BotMono/blob/master/BotMono_safe.py)会完全去掉传送功能。

## 关于配置文件

配置文件[BotMono.json](https://github.com/Jerry-FaGe/MCDR-BotMono/blob/master/BotMono.json)是一个json格式文件，请把它放在`MCDR/config`文件夹下，它的格式如下：
```JSON
{
  "Jerry_FaGe": ["Jerry_FaGe", "发哥", "开发者", "作者", "test"],
  "stone": ["stone", "石头"],
  "cobblestone": ["cobblestone", "圆石", "原石", "鹅卵石"],
  "sand": ["sand", "沙子"],
  "piston": ["piston", "活塞"],
  "sticky_piston": ["sticky_piston", "粘性活塞"],
  "comparator": ["comparator", "红石比较器", "比较器"],
  "repeater": ["repeater", "红石中继器", "中继器"],
  "lever": ["lever", "拉杆"],
  "tnt": ["tnt", "TNT", "C4", "boom"],
  "fireworks": ["fireworks" ,"烟花", "火箭", "烟花火箭"],
  "elytra": ["elytra", "鞘翅"]
}
```
每一行的格式为`"真实名": ["昵称1", "昵称2", "昵称3", ...]`，用户可以凭喜好自行增减。本插件的`<mono>`参数为配置文件中的`昵称`，召唤出的假人名称为`真实名`，参数输入列表中任意`昵称`都会召唤名为`真实名`的同一假人。本意是让英语苦手不用背单词，本来想肝一套全物品配置文件的，思考后怕引发争议，留几个示例供用户自行增减。
**注:** 每一个昵称列表应该包含该项的真实名，以便参数输入真实名也可以操作对应假人

## 声明

本插件实现的功能只要是装了carpet mod能召唤假人的服务端都可以实现，即便是这样也仍有可能引发争议。烦请想装本插件的腐竹实装前务必了解下成员们的意愿，毕竟会存在“我可以手动输指令召唤假人让假人扔东西但用这个插件就是作弊”这样的人。

本来想如果顺利的话，还会试着摸一个`假人补货机`来为特定假人补货，尝试一下插件与红石机械联动的形式，现在闹出一堆事也没什么心情摸了。看看大家反馈再决定吧，如有意见建议或者bug欢迎提issue与我交流，因为理解不同来找我理论的，你说得对。
