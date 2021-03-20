#!/usr/bin/python3
# -*-coding:utf-8-*-
"""
Created on 2020/12/3
「君は道具ではなく、その名が似合う人になろんだ」
@author: Jerry_FaGe
"""
import os
import json
import time
from mcdreforged.api.rtext import *
from mcdreforged.api.decorator import new_thread

PLUGIN_METADATA = {
    'id': 'bot_mono_safe',
    'version': '0.0.1',
    'name': '假人物品映射（和谐版）',  # RText component is allowed
    'description': '将输入的英文，中文（甚至拼音）指向同一假人并提供昵称映射和简化指令',  # RText component is allowed
    'author': 'Jerry-FaGe',
    'link': 'https://github.com/Jerry-FaGe/MCDR-BotMono',
    'dependencies': {
        'mcdreforged': '>=1.0.0',
        'minecraft_data_api': '*',
    }
}

config_path = './config/BotMono.json'
prefix_short = '!!bm'
prefix = '!!botmono'
bot_dic = {}
bot_list = []
help_msg = '''
================== §bBotMono §r==================
§6欢迎使用由@Jerry-FaGe开发的假人全物品-和谐版（暂时并不全）插件！
§6你可以在Github搜索MCDR-BotMono找到本项目！
「君は道具ではなく、その名が似合う人になろんだ」
本插件中§d{prefix_short}§r与§d{prefix}§r效果相同，两者可以互相替换
§b{prefix_short} §r显示本帮助信息
§b{prefix_short} list §r显示由本插件召唤出的假人列表
§b{prefix_short} reload §r重载插件配置
§b{prefix_short} <mono> §r输出一个可点击的界面，自动根据假人是否在线改变选项
§b{prefix_short} <mono> spawn §r召唤一个用于存储<mono>的假人
§b{prefix_short} <mono> kill §r干掉用于存储<mono>的假人
§b{prefix_short} <mono> one §r假人扔出一个手中物品（执行此条前无需执行spawn，如假人不存在会自动创建）
§b{prefix_short} <mono> all §r假人扔出身上所有物品（执行此条前无需执行spawn，如假人不存在会自动创建）
§b{prefix_short} <mono> handall §r假人扔出手中所有物品（执行此条前无需执行spawn，如假人不存在会自动创建）
'''.format(prefix=prefix, prefix_short=prefix_short)
help_head = """
================== §bBotMono §r==================
§6欢迎使用由@Jerry-FaGe开发的假人全物品-和谐版（暂时并不全）插件！
§6你可以在Github搜索MCDR-BotMono找到本项目！
「君は道具ではなく、その名が似合う人になろんだ」
本插件中§d{prefix_short}§r与§d{prefix}§r效果相同，两者可以互相替换
""".format(prefix=prefix, prefix_short=prefix_short)
help_body = {
    f"§b{prefix_short}": "§r显示本帮助信息",
    f"§b{prefix_short} list": "§r显示由本插件召唤出的假人列表",
    f"§b{prefix_short} reload": "§r重载插件配置",
    f"§b{prefix_short} <mono>": "§r输出一个可点击的界面，自动根据假人是否在线改变选项",
    f"§b{prefix_short} <mono> spawn": "§r召唤一个用于存储<mono>的假人",
    f"§b{prefix_short} <mono> kill": "§r干掉用于存储<mono>的假人",
    f"§b{prefix_short} <mono> one": "§r假人扔出一个手中物品（执行此条前无需执行spawn，如假人不存在会自动创建）",
    f"§b{prefix_short} <mono> all": "§r假人扔出身上所有物品（执行此条前无需执行spawn，如假人不存在会自动创建）",
    f"§b{prefix_short} <mono> handall": "§r假人扔出手中所有物品（执行此条前无需执行spawn，如假人不存在会自动创建）"
}


def get_pos(server, info):
    api = server.get_plugin_instance('minecraft_data_api')
    pos = api.get_player_info(info.player, 'Pos')
    dim = api.get_player_info(info.player, 'Dimension')
    facing = api.get_player_info(info.player, 'Rotation')
    return pos, dim, facing


def read():
    global bot_dic
    with open(config_path, encoding='utf8') as f:
        bot_dic = json.load(f)


def save():
    with open(config_path, 'w', encoding='utf8') as f:
        json.dump(bot_dic, f, indent=4, ensure_ascii=False)


def search(mono):
    for k, v in bot_dic.items():
        if mono in v:
            return k


def auth_player(player):
    """验证玩家是否为bm假人"""
    lower_dic = {i.lower(): i for i in bot_dic}
    bot_name = lower_dic.get(player.lower(), None)
    return bot_name if bot_name else None


def spawn_cmd(server, info, name):
    if info.is_player:
        pos, dim, facing = get_pos(server, info)
        return f'/execute as {info.player} run player {name} spawn at {pos[0]} {pos[1]} {pos[2]} facing {facing[0]} {facing[1]} in {dim}'
    else:
        return f'/player {name} spawn'


def spawn(server, info, name):
    return spawn_cmd(server, info, name)


def kill(name):
    return f'/player {name} kill'


def drop_one(name):
    return f'/player {name} drop once'


def drop_all(name):
    return f'/player {name} dropStack all'


def drop_handall(name):
    return f'/player {name} dropStack once'


def on_load(server, old):
    global bot_list
    server.register_help_message(f'{prefix_short}', RText(
        '假人物品映射').c(RAction.run_command, f'{prefix_short}').h('点击查看帮助'))
    if old is not None and old.bot_list is not None:
        bot_list = old.bot_list
    else:
        bot_list = []
    if not os.path.isfile(config_path):
        save()
    else:
        try:
            read()
        except Exception as e:
            server.say('§b[BotMono]§4配置加载失败，请确认配置路径是否正确：{}'.format(e))


@new_thread(PLUGIN_METADATA["name"])
def on_info(server, info):
    if info.is_user:
        if info.content.startswith(prefix) or info.content.startswith(prefix_short):
            info.cancel_send_to_server()
            global bot_dic, bot_list
            args = info.content.split(' ')

            if len(args) == 1:
                # server.reply(info, help_msg)
                head = [help_head]
                body = [RText(f'{k} {v}\n').c(
                    RAction.suggest_command, k.replace('§b', '')).h(v)
                        for k, v in help_body.items()]
                server.reply(info, RTextList(*(head + body)))

            elif len(args) == 2:
                if args[1] == "list":
                    msg = ['\n', f'当前共有{len(bot_list)}个假人在线']
                    for name in bot_list:
                        bot_info = RTextList(
                            '\n'
                            f'§7----------- §6{name}§7 -----------\n',
                            f'§7此假人存放:§6 {bot_dic.get(name, "没有索引")}\n',
                            RText('§d[扔出所有]  ').c(
                                RAction.run_command, f'{prefix_short} {name} all').h(f'§6{name}§7扔出身上所有物品'),
                            RText('§d[扔出一个]  ').c(
                                RAction.run_command, f'{prefix_short} {name} one').h(f'§6{name}§7扔出一个物品'),
                            RText('§d[扔出手中]  ').c(
                                RAction.run_command, f'{prefix_short} {name} handall').h(f'§6{name}§7扔出手中物品'),
                            RText('§d[下线]  ').c(
                                RAction.run_command, f'{prefix_short} {name} kill').h(f'§7干掉§6{name}')
                        )
                        msg.append(bot_info)
                    server.reply(info, RTextList(*msg))

                elif args[1] == "reload":
                    try:
                        read()
                        server.say('§b[BotMono]§a由玩家§d{}§a发起的BotMono重载成功'.format(info.player))
                    except Exception as e:
                        server.say('§b[BotMono]§4由玩家§d{}§4发起的BotMono重载失败：{}'.format(info.player, e))

                elif search(args[1]):
                    name = search(args[1])
                    if name not in bot_list:
                        msg = RTextList(
                            '\n'
                            f'§7----------- §6{name} §4离线 §7-----------\n',
                            f'§7此假人存放:§6 {bot_dic.get(search(args[1]), "没有索引")}\n',
                            RText('§d[召唤]  ').c(
                                RAction.run_command, f'{prefix_short} {name} spawn').h(f'§7召唤§6{name}'),
                            RText('§d[扔出所有]  ').c(
                                RAction.run_command, f'{prefix_short} {name} all').h(f'§6{name}§7扔出身上所有物品'),
                            RText('§d[扔出一个]  ').c(
                                RAction.run_command, f'{prefix_short} {name} one').h(f'§6{name}§7扔出一个物品'),
                            RText('§d[扔出手中]  ').c(
                                RAction.run_command, f'{prefix_short} {name} handall').h(f'§6{name}§7扔出手中物品')
                        )
                        server.reply(info, msg)
                    else:
                        msg = RTextList(
                            '\n'
                            f'§7----------- §6{name} §a在线 §7-----------\n',
                            f'§7此假人存放:§6 {bot_dic.get(search(args[1]), "没有索引")}\n',
                            RText('§d[扔出所有]  ').c(
                                RAction.run_command, f'{prefix_short} {name} all').h(f'§6{name}§7扔出身上所有物品'),
                            RText('§d[扔出一个]  ').c(
                                RAction.run_command, f'{prefix_short} {name} one').h(f'§6{name}§7扔出一个物品'),
                            RText('§d[扔出手中]  ').c(
                                RAction.run_command, f'{prefix_short} {name} handall').h(f'§6{name}§7扔出手中物品'),
                            RText('§d[下线]  ').c(
                                RAction.run_command, f'{prefix_short} {name} kill').h(f'§7干掉§6{name}')
                        )
                        server.reply(info, msg)

                else:
                    server.reply(info, f"§b[BotMono]§4未查询到§d{args[1]}§4对应的假人")
            elif len(args) == 3:
                name = search(args[1])
                if name:
                    if args[2] == "spawn":
                        if name not in bot_list:
                            server.execute(spawn(server, info, name))
                        else:
                            server.reply(info, f"§b[BotMono]§4假人§d{name}§6（{args[1]}）§4已经在线")

                    elif args[2] == "kill":
                        if name in bot_list:
                            server.execute(kill(name))
                            server.reply(info, f"§b[BotMono]§a假人§d{name}§6（{args[1]}）§a已被下线")

                    elif args[2] == "one":
                        if name not in bot_list:
                            server.execute(spawn(server, info, name))
                            server.reply(info, f"§b[BotMono]§a已自动创建假人§d{name}§6（{args[1]}）")
                            time.sleep(1)
                        server.execute(drop_one(name))
                        server.reply(info, f"§b[BotMono]§a假人§d{name}§6（{args[1]}）§a扔出1个物品")

                    elif args[2] == "all":
                        if name not in bot_list:
                            server.execute(spawn(server, info, name))
                            server.reply(info, f"§b[BotMono]§a已自动创建假人§d{name}§6（{args[1]}）")
                            time.sleep(1)
                        server.execute(drop_all(name))
                        server.reply(info, f"§b[BotMono]§a假人§d{name}§6（{args[1]}）§a扔出身上所有物品")

                    elif args[2] == "handall":
                        if name not in bot_list:
                            server.execute(spawn(server, info, name))
                            server.reply(info, f"§b[BotMono]§a已自动创建假人§d{name}§6（{args[1]}）")
                            time.sleep(1)
                        server.execute(drop_handall(name))
                        server.reply(info, f"§b[BotMono]§a假人§d{name}§6（{args[1]}）§a扔出手中所有物品")

                    else:
                        server.reply(info, f"§b[BotMono]§4参数输入错误，输入§6{prefix_short}§4查看帮助信息")

                else:
                    server.reply(info, f"§b[BotMono]§4未查询到§d{args[1]}§4对应的假人")


def on_player_joined(server, player, info):
    bot_name = auth_player(player)
    if bot_name:
        if bot_name not in bot_list:
            bot_list.append(bot_name)


def on_player_left(server, player):
    bot_name = auth_player(player)
    if bot_name:
        if bot_name in bot_list:
            bot_list.remove(bot_name)


def on_server_stop(server, return_code):
    global bot_list
    bot_list = []
