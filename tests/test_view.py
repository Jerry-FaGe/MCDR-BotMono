import json
from pathlib import Path

import pytest

from bot_mono import command, view
from bot_mono.bot import Bot
from bot_mono.config import config


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def clicks(message):
    return [node['clickEvent'] for node in nodes(json.loads(message.to_json_str())) if 'clickEvent' in node]


@pytest.mark.parametrize('online', [False, True])
@pytest.mark.parametrize('prefix', ['!!bm', '!!items'])
def test_action_buttons_only_offer_mono_actions_and_use_exact_record(env, bot, online, prefix):
    config.prefix_short = prefix
    bot.is_online = online
    actions = ['kill' if online else 'spawn', 'one', 'handall', 'all']
    expected = [{'action': 'run_command', 'value': f'{prefix} SandBot {action}'} for action in actions]
    assert clicks(view.render_bot_actions(bot)) == expected
    info = view.render_bot_info(bot)
    assert clicks(info) == [*expected,
                            {'action': 'run_command', 'value': f'{prefix} SandBot'},
                            {'action': 'run_command', 'value': f'{prefix} list'}]
    text = info.to_plain_text()
    assert '物品别名: farm、刷沙机' in text
    assert '原地扔出' in text
    assert ('在线' if online else '离线') in text
    assert '登记位置' not in text
    assert ' here' not in info.to_json_str()


@pytest.mark.parametrize('can_operate', [False, True])
@pytest.mark.parametrize('can_manage', [False, True])
def test_details_permissions_are_independent(env, bot, can_operate, can_manage):
    message = view.render_bot_info(bot, can_operate=can_operate, can_manage=can_manage)
    events = {event['value']: event['action'] for event in clicks(message)}
    for action in ['spawn', 'one', 'all', 'handall']:
        assert (f'!!bm SandBot {action}' in events) is can_operate
    assert ('!!bm SandBot alias add ' in events) is can_manage
    assert ('!!bm del SandBot' in events) is can_manage
    if can_manage:
        assert events['!!bm SandBot alias add '] == 'suggest_command'
        assert events['!!bm del SandBot'] == 'suggest_command'
        assert events['!!bm SandBot alias'] == 'run_command'
    assert events['!!bm SandBot'] == events['!!bm list'] == 'run_command'


@pytest.mark.parametrize('permission', range(5))
@pytest.mark.parametrize('levels', [(1, 3), (4, 1), (0, 4)])
def test_command_panels_use_current_permissions(env, bot, monkeypatch, permission, levels):
    env.source.permission = permission
    config.permission = dict(zip(['bot', 'list'], levels))
    messages = []
    monkeypatch.setattr(env.source, 'reply', messages.append)
    command.bot_action(env.source, {'mono': 'farm'}, 'info', env.manager)
    assert messages[-1].to_json_str() == view.render_bot_info(
        bot, can_operate=permission >= levels[0], can_manage=permission >= levels[1]).to_json_str()


def test_help_uses_current_prefix_and_contains_only_supported_commands(env):
    config.prefix_short = '!!items'
    templates = [
        '', ' list [online|offline] [page]', ' list [online|offline] search <关键词> [page]',
        ' reload', ' add <name> <alias>', ' del <mono>', ' <mono> alias',
        ' <mono> alias add <alias>', ' <mono> alias del <alias>', ' <mono>',
        ' <mono> spawn', ' <mono> kill', ' <mono> one', ' <mono> all', ' <mono> handall',
    ]
    help_message = view.render_help()
    assert clicks(help_message) == [
        {'action': 'suggest_command', 'value': '!!items' + template} for template in templates
    ]
    assert 'BotMono' in help_message.to_plain_text()
    assert '!!bm' not in help_message.to_plain_text()


@pytest.mark.parametrize('renderer', [view.render_bot_info, view.render_bot_actions,
                                    view.render_bot_summary, view.render_alias_panel])
def test_panels_have_explicit_colors_and_click_hints(env, bot, renderer):
    message = renderer(bot)
    for node in nodes(json.loads(message.to_json_str())):
        if node.get('text', '').strip():
            assert 'color' in node
            assert '§' not in node['text']
        if 'clickEvent' in node:
            hover = json.dumps(node['hoverEvent'], ensure_ascii=False)
            if node['clickEvent']['action'] == 'run_command':
                assert '点击执行' in hover
                assert '回车' not in hover
            else:
                assert node['clickEvent']['action'] == 'suggest_command'
                assert '回车' in hover


@pytest.mark.parametrize('confirmed', [False, True])
def test_details_show_first_alias_and_real_name_without_reordering(env, confirmed):
    config.bot_name_prefix = 'b_'
    bot = Bot(env.server, 'SandBot', ['SANDBOT', 'b_SANDBOT', '沙子', 'sand'],
              confirmed_name='b_SandBot' if confirmed else None)
    before = bot.to_dict()
    message = view.render_bot_info(bot)
    text = message.to_plain_text()
    assert text.startswith('----- 沙子 · 离线 -----')
    assert '物品别名: 沙子、sand' in text
    assert ('b_SandBot' if confirmed else 'b_sandbot') in text
    assert ('待确认' in text) is not confirmed
    assert bot.to_dict() == before


def test_alias_panel_only_removes_custom_aliases(env):
    config.bot_name_prefix = 'b_'
    bot = Bot(env.server, 'SandBot', ['SANDBOT', 'b_SANDBOT', '沙子', 'sand'])
    assert clicks(view.render_alias_panel(bot)) == [
        {'action': 'suggest_command', 'value': '!!bm SandBot alias del 沙子'},
        {'action': 'suggest_command', 'value': '!!bm SandBot alias del sand'},
        {'action': 'suggest_command', 'value': '!!bm SandBot alias add '},
        {'action': 'run_command', 'value': '!!bm SandBot'},
    ]


def test_rendering_never_changes_status_or_persistence(env, bot):
    before = bot.to_dict()
    settings = config.to_dict()
    files = {path: path.read_bytes() for path in env.path.iterdir()}
    generation = env.manager.generation
    for renderer in [view.render_bot_info, view.render_bot_summary, view.render_bot_actions,
                     view.render_alias_panel, lambda bot: view.render_bot_list([bot]),
                     lambda bot: view.render_action_feedback(bot, 'all')]:
        renderer(bot)
    assert bot.to_dict() == before
    assert not bot.is_online
    assert config.to_dict() == settings
    assert env.manager.generation == generation
    assert {path: path.read_bytes() for path in env.path.iterdir()} == files
    assert env.server.commands == []


@pytest.mark.parametrize('action,carpet,label', [
    ('spawn', None, '已确认上线'),
    ('kill', 'kill', '下线请求已发送'),
    ('one', 'drop once', '扔出主手单件物品请求已发送'),
    ('all', 'dropStack all', '扔出全部物品请求已发送'),
    ('handall', 'dropStack once', '扔出主手整组物品请求已发送'),
])
def test_action_feedback_distinguishes_confirmed_spawn_from_requests(env, bot, monkeypatch, action, carpet, label):
    bot.is_online = True
    messages = []
    monkeypatch.setattr(env.source, 'reply', messages.append)
    command.bot_action(env.source, {'mono': 'farm'}, action, env.manager).result(timeout=2)
    assert len(messages) == 1
    message = messages[0]
    assert message.to_plain_text() == f'[BM] farm · {label}'
    assert clicks(message) == [{'action': 'run_command', 'value': '!!bm SandBot'}]
    body = next(node for node in nodes(json.loads(message.to_json_str())) if node.get('text') == label)
    assert body['color'] == ('green' if action == 'spawn' else 'white')
    if action != 'spawn':
        assert '实际动作' in json.dumps(body['hoverEvent'], ensure_ascii=False)
    assert env.server.commands == ([f'player sandbot {carpet}'] if carpet else [])


def test_delete_feedback_has_no_dead_link_and_does_not_kill(env, bot, monkeypatch):
    messages = []
    monkeypatch.setattr(env.source, 'reply', messages.append)
    bot.is_online = True
    command.del_bot(env.source, {'mono': 'farm'}, env.manager)
    assert messages[0].to_plain_text() == '[BM] farm · 已删除记录'
    assert clicks(messages[0]) == []
    assert '不会让假人下线' in messages[0].to_json_str()
    assert env.server.commands == []


def test_alias_feedback_uses_name_after_removing_invoking_alias(env, bot, monkeypatch):
    messages = []
    monkeypatch.setattr(env.source, 'reply', messages.append)
    command.edit_alias(env.source, {'mono': 'farm', 'alias': 'farm'}, env.manager, remove=True)
    assert messages[0].to_plain_text() == '[BM] 刷沙机 · 已移除别名「farm」'
    assert clicks(messages[0]) == [{'action': 'run_command', 'value': '!!bm SandBot'}]


def test_error_feedback_keeps_full_cause_in_hover():
    cause = 'save failed:\nC:/my  world/bots.json\npermission denied'
    message = view.render_feedback(cause, kind='error')
    assert message.to_plain_text() == '[BM] save failed: C:/my  world/bots.json permission denied'
    assert json.dumps(cause)[1:-1] in message.to_json_str()
    assert clicks(message) == []


def test_missing_alias_and_duplicate_alias_feedback_do_not_write(env, bot):
    before = Path(config.bots_path).read_bytes()
    command.edit_alias(env.source, {'mono': 'farm', 'alias': 'FARM'}, env.manager)
    assert '无需重复添加' in env.source.messages[-1]
    command.edit_alias(env.source, {'mono': 'farm', 'alias': 'missing'}, env.manager, remove=True)
    assert '未作修改' in env.source.messages[-1]
    assert Path(config.bots_path).read_bytes() == before
