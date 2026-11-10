import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcdreforged.api.command import CommandError

import bot_mono
from bot_mono import command, utils, view
from bot_mono.config import config
from bot_mono.storage import read_json, write_json


def run_command(root, source, text):
    executions = root._entry_execute(source, text)
    # MCDR 2.12 executes inline; 2.16 returns scheduled callbacks.
    if executions is not None:
        from mcdreforged.command.builder.callback import DirectCallbackInvoker
        for execution in executions:
            execution.scheduled_callback.invoke(DirectCallbackInvoker())


@pytest.fixture
def player_data(monkeypatch):
    calls = []

    def query(player):
        calls.append(player)
        return {'Pos': [1.25, 70, -2.5], 'Dimension': 'minecraft:the_nether', 'Rotation': [90, -10]}

    monkeypatch.setitem(sys.modules, 'minecraft_data_api', SimpleNamespace(get_player_info=query))
    return calls


@pytest.fixture
def capture_tasks(env, monkeypatch):
    tasks = []
    submit = env.manager.submit

    def capture(*args):
        task = submit(*args)
        tasks.append(task)
        return task

    monkeypatch.setattr(env.manager, 'submit', capture)
    return tasks


def test_command_tree_add_list_alias_delete_without_server(env, monkeypatch):
    env.server.running = False
    command.register_command_tree(env.server, env.manager)
    root = env.server.roots[0]

    def fail(*args):
        raise AssertionError('registering bots must not query player coordinates')

    monkeypatch.setattr(utils, 'get_pos', fail)
    for source in [env.source, env.player]:
        run_command(root, source, '!!bm add Fireworks 烟花火箭')
        run_command(root, source, '!!bm add Fireworks 火箭')
        bot = env.manager.get_bot('Fireworks')
        assert bot.aliases == ['烟花火箭', '火箭']
        assert bot.to_dict() == {'aliases': bot.aliases}
        run_command(root, source, '!!bm list search 烟花')
        assert '[离线] 烟花火箭' in source.messages[-1]
        run_command(root, source, '!!bm 火箭 alias add fireworks_new')
        assert env.manager.resolve_bot('FIREWORKS_NEW') is bot
        run_command(root, source, '!!bm fireworks_new alias del 火箭')
        assert env.manager.resolve_bot('火箭') is None
        run_command(root, source, '!!bm del 烟花火箭')
        assert env.manager.get_bot('Fireworks') is None
    assert env.server.commands == []


@pytest.mark.parametrize('action,carpet', [
    ('one', 'drop once'), ('all', 'dropStack all'), ('handall', 'dropStack once'),
])
@pytest.mark.parametrize('source_name', ['player', 'source'])
@pytest.mark.parametrize('online', [False, True])
def test_drop_commands_spawn_only_when_needed_and_use_confirmed_name(
        env, bot, player_data, capture_tasks, action, carpet, source_name, online):
    source = getattr(env, source_name)
    bot.is_online = online
    if not online:
        # The name may be corrected while the spawn is in flight.
        def acknowledge(_):
            bot.confirm_name('sAnDbOt')
            bot.is_online = True
        env.server.on_execute = acknowledge
    command.register_command_tree(env.server, env.manager)
    run_command(env.server.roots[0], source, f'!!bm farm {action}')
    capture_tasks[0].result(timeout=3)
    expected = []
    if not online:
        expected.append(
            'execute as Tester run player sandbot spawn at 1.25 70.0 -2.5 facing 90.0 -10.0 in minecraft:the_nether'
            if source_name == 'player' else 'player sandbot spawn in survival'
        )
    expected.append(f'player {"sandbot" if online else "sAnDbOt"} {carpet}')
    assert env.server.commands == expected
    assert player_data == (['Tester'] if not online and source_name == 'player' else [])
    assert len(source.messages) == 1
    assert '请求已发送' in source.messages[0]
    assert '已确认上线' not in source.messages[0]


def test_each_spawn_uses_the_current_players_position(env, bot, monkeypatch):
    calls = []
    positions = {'Alice': [1.125, 65, -2.5], 'Bob': [80, 75.5, 100]}

    def query(player):
        calls.append(player)
        return {'Pos': positions[player], 'Dimension': 'example:custom/room', 'Rotation': [-90, 30]}

    monkeypatch.setitem(sys.modules, 'minecraft_data_api', SimpleNamespace(get_player_info=query))
    env.server.on_execute = lambda _: setattr(bot, 'is_online', True)
    assert bot.spawn(executor='Alice')
    bot.is_online = False
    assert bot.spawn(executor='Bob')
    assert calls == ['Alice', 'Bob']
    assert env.server.commands == [
        'execute as Alice run player sandbot spawn at 1.125 65.0 -2.5 facing -90.0 30.0 in example:custom/room',
        'execute as Bob run player sandbot spawn at 80.0 75.5 100.0 facing -90.0 30.0 in example:custom/room',
    ]
    assert set(read_json(config.bots_path)['SandBot']) == {'aliases'}


@pytest.mark.parametrize('method', ['spawn', 'drop_one', 'drop_all', 'drop_handall'])
def test_online_bot_never_queries_position_or_moves(env, bot, monkeypatch, method):
    bot.is_online = True

    def fail(*args):
        raise AssertionError('online actions must not query the executor position')

    monkeypatch.setattr(utils, 'get_pos', fail)
    assert getattr(bot, method)(executor='Tester')
    assert all('spawn' not in text and 'tp ' not in text and 'teleport' not in text for text in env.server.commands)


@pytest.mark.parametrize('method', ['drop_one', 'drop_all', 'drop_handall'])
def test_spawn_timeout_never_sends_followup_drop(env, bot, method):
    config.spawn_max_wait_time = 0.03
    config.spawn_check_interval = 0.2
    start = time.monotonic()
    assert not getattr(bot, method)()
    assert time.monotonic() - start < 1
    assert env.server.commands == ['player sandbot spawn in survival']


def test_join_event_wakes_spawn_and_allows_drop(env, bot, player_data):
    requested = threading.Event()
    env.server.on_execute = lambda _: requested.set()
    task = env.manager.submit(bot.drop_all, 'Tester')
    try:
        assert requested.wait(2)
        env.manager.update_player_status('SandBot', True)
        assert task.result(timeout=2)
        assert env.server.commands[-1] == 'player SandBot dropStack all'
    finally:
        bot.cancel()


def test_concurrent_drops_spawn_and_query_position_only_once(env, bot, player_data):
    requested = threading.Event()
    env.server.on_execute = lambda _: requested.set()
    tasks = [env.manager.submit(bot.drop_one, 'Tester') for _ in range(3)]
    try:
        assert requested.wait(2)
        env.manager.update_player_status(bot.real_name, True)
        assert all(task.result(timeout=2) for task in tasks)
    finally:
        bot.cancel()
    assert len(player_data) == 1
    assert sum(' spawn ' in text for text in env.server.commands) == 1
    assert env.server.commands.count('player sandbot drop once') == 3


@pytest.mark.parametrize('operation', ['reload', 'unload', 'delete', 'server_stop'])
@pytest.mark.parametrize('phase', ['query', 'spawn'])
def test_lifecycle_change_cancels_pending_player_actions(env, bot, monkeypatch, operation, phase):
    entered = threading.Event()
    release = threading.Event()

    def query(player):
        if phase == 'query':
            entered.set()
            assert release.wait(3)
        return {'Pos': [1, 64, 2], 'Dimension': 'minecraft:overworld', 'Rotation': [0, 0]}

    monkeypatch.setitem(sys.modules, 'minecraft_data_api', SimpleNamespace(get_player_info=query))
    env.server.on_execute = lambda _: entered.set()
    task = env.manager.submit(bot.drop_all, 'Tester')
    try:
        assert entered.wait(2)
        if operation == 'reload':
            env.manager.reload_config()
        elif operation == 'unload':
            env.manager.shutdown()
        elif operation == 'delete':
            env.manager.remove_bot(bot.name)
        else:
            env.server.running = False
            env.manager.clear_all_online_status()
        release.set()
        assert not task.result(timeout=3)
    finally:
        release.set()
        bot.cancel()
    assert len(env.server.commands) == (1 if phase == 'spawn' else 0)
    assert all('drop' not in text for text in env.server.commands)


def test_join_during_position_query_does_not_issue_duplicate_spawn(env, bot, monkeypatch):
    def query(player):
        env.manager.update_player_status('SandBot', True, confirm=False)
        return None

    monkeypatch.setitem(sys.modules, 'minecraft_data_api', SimpleNamespace(get_player_info=query))
    assert bot.drop_one(executor='Tester')
    assert env.server.commands == ['player sandbot drop once']


@pytest.mark.parametrize('data', [
    None, [], {}, {'Pos': [1, 64, 2]},
    {'Pos': [True, 64, 2], 'Dimension': 'minecraft:overworld', 'Rotation': [0, 0]},
    {'Pos': [float('nan'), 64, 2], 'Dimension': 'minecraft:overworld', 'Rotation': [0, 0]},
    {'Pos': [1, 64, 2], 'Dimension': '@a', 'Rotation': [0, 0]},
    {'Pos': [1, 64, 2], 'Dimension': 'minecraft:overworld\nstop', 'Rotation': [0, 0]},
    {'Pos': [1, 64, 2], 'Dimension': 'minecraft:overworld', 'Rotation': [0, float('inf')]},
    {'Pos': '1 64 2', 'Dimension': 'minecraft:overworld', 'Rotation': [0, 0]},
])
def test_invalid_player_data_fails_without_commands_or_false_success(env, bot, monkeypatch, data):
    monkeypatch.setitem(sys.modules, 'minecraft_data_api', SimpleNamespace(get_player_info=lambda _: data))
    command.bot_action(env.player, {'mono': 'farm'}, 'all', env.manager).result(timeout=2)
    assert env.server.commands == []
    assert '操作失败' in env.player.messages[-1]
    assert '已发送' not in env.player.messages[-1]


def test_queued_action_rechecks_permission_before_work(env, bot, player_data):
    release = threading.Event()
    workers = [env.manager.submit(release.wait, 5) for _ in range(4)]
    task = command.bot_action(env.player, {'mono': 'farm'}, 'all', env.manager)
    env.player.permission = 0
    try:
        release.set()
        task.result(timeout=3)
        assert '权限不足' in env.player.messages[-1]
        assert player_data == []
        assert env.server.commands == []
    finally:
        release.set()
        for worker in workers:
            worker.result(timeout=3)


def test_api_error_reports_missing_position(env, bot, monkeypatch):
    def fail(*args):
        raise RuntimeError('API unavailable')

    monkeypatch.setitem(sys.modules, 'minecraft_data_api', SimpleNamespace(get_player_info=fail))
    assert utils.get_pos(env.server, 'Tester') == (None, None, None)
    command.bot_action(env.player, {'mono': 'farm'}, 'spawn', env.manager).result(timeout=2)
    assert '无法获取玩家位置' in env.player.messages[-1]
    assert env.server.commands == []


@pytest.mark.parametrize('executor', ['', '@a', 'Tester\nstop', 'two words', [], 123])
def test_invalid_executor_never_reaches_player_query(env, bot, monkeypatch, executor):
    def fail(*args):
        raise AssertionError('invalid executor must not query Minecraft')

    monkeypatch.setattr(utils, 'get_pos', fail)
    with pytest.raises(ValueError):
        bot.spawn(executor=executor)
    assert env.server.commands == []


@pytest.mark.parametrize('action', ['spawn', 'kill', 'one', 'all', 'handall'])
def test_guest_cannot_schedule_actions(env, bot, action):
    env.source.permission = 0
    assert command.bot_action(env.source, {'mono': 'farm'}, action, env.manager) is None
    assert env.server.commands == []
    assert '权限不足' in env.source.messages[-1]


@pytest.mark.parametrize('text', ['add NewBot new', 'del farm', 'reload', 'farm alias',
                                'farm alias add new', 'farm alias del farm'])
def test_management_commands_require_permission(env, bot, text):
    env.source.permission = 2
    command.register_command_tree(env.server, env.manager)
    before = Path(config.bots_path).read_bytes()
    with pytest.raises(CommandError):
        run_command(env.server.roots[0], env.source, '!!bm ' + text)
    assert Path(config.bots_path).read_bytes() == before
    assert env.server.commands == []


@pytest.mark.parametrize('text', [
    'farm here', 'farm where', 'farm use', 'farm huse', 'farm atk', 'farm stop',
    'farm one extra', 'farm all extra', 'farm handall 1',
    'add NewBot new minecraft:overworld 1 64 2 90 0', 'add', 'add NewBot',
    'farm alias add', 'farm alias del', 'farm alias add new extra',
])
def test_removed_commands_and_invalid_arguments_never_execute(env, bot, monkeypatch, text):
    def fail(*args, **kwargs):
        raise AssertionError('invalid syntax must not invoke any callback')

    monkeypatch.setattr(command, 'bot_action', fail)
    monkeypatch.setattr(command, 'add_bot', fail)
    monkeypatch.setattr(command, 'edit_alias', fail)
    command.register_command_tree(env.server, env.manager)
    before = Path(config.bots_path).read_bytes()
    with pytest.raises(CommandError):
        run_command(env.server.roots[0], env.source, '!!bm ' + text)
    assert Path(config.bots_path).read_bytes() == before
    assert env.server.commands == []


def test_bots_work_again_after_server_restart(env, bot):
    bot.is_online = True
    env.server.running = False
    env.manager.clear_all_online_status()
    current = env.manager.get_bot(bot.name)
    assert current is not bot
    assert not current.is_online
    assert not bot.kill()
    env.server.running = True
    env.server.on_execute = lambda _: setattr(current, 'is_online', True)
    assert current.drop_one()


def test_kill_is_not_blocked_by_incomplete_online_cache(env, bot):
    assert not bot.is_online
    command.bot_action(env.source, {'mono': 'farm'}, 'kill', env.manager).result(timeout=2)
    assert env.server.commands == ['player sandbot kill']
    assert '请求已发送' in env.source.messages[-1]


def test_failed_action_does_not_reply_success(env, bot):
    config.spawn_max_wait_time = 0.01
    command.bot_action(env.source, {'mono': 'farm'}, 'all', env.manager).result(timeout=2)
    assert '操作未完成' in env.source.messages[-1]
    assert '已发送' not in env.source.messages[-1]


def test_custom_prefix_is_used_in_registration_help_and_buttons(env, bot):
    write_json(config.config_path, {'prefix_short': '!!items'})
    bot_mono.on_load(env.server, None)
    assert env.server.roots[-1].literals == {'!!items'}
    assert env.server.help_messages[-1][0] == '!!items'
    assert '!!bm' not in view.render_help().to_plain_text()
    assert '!!items SandBot' in view.render_bot_info(bot).to_json_str()


def test_prefix_reload_rejects_partial_changes(env, bot):
    write_json(config.config_path, {'prefix_short': '!!items', 'permission': {'bot': 4}})
    command.reload_plugin(env.source, env.manager)
    assert config.prefix_short == '!!bm'
    assert config.permission['bot'] == 1
    assert '!!MCDR plugin reload bot_mono' in env.source.messages[-1]


@pytest.mark.parametrize('arguments,status,query,page', [
    ('', 'all', None, 1), ('2', 'all', None, 2), ('online', 'online', None, 1),
    ('offline 2', 'offline', None, 2), ('search 烟花', 'all', '烟花', 1),
    ('online search FIRE 3', 'online', 'FIRE', 3), ('offline search 2', 'offline', '2', 1),
])
def test_list_command_parsing(env, monkeypatch, arguments, status, query, page):
    calls = []
    monkeypatch.setattr(command, 'list_bots', lambda src, manager, status, **kw: calls.append((status, kw)))
    command.register_command_tree(env.server, env.manager)
    run_command(env.server.roots[0], env.source, ('!!bm list ' + arguments).rstrip())
    assert calls == [(status, {'query': query, 'page': page})]


@pytest.mark.parametrize('arguments', ['0', '-1', '1.5', 'all', 'online 0', 'search',
                                       'search farm 0', 'search farm extra', 'online offline', '2 online'])
def test_invalid_list_arguments_never_run_callbacks(env, monkeypatch, arguments):
    def fail(*args, **kwargs):
        raise AssertionError('invalid list syntax must not run callbacks')

    monkeypatch.setattr(command, 'list_bots', fail)
    monkeypatch.setattr(command, 'bot_action', fail)
    command.register_command_tree(env.server, env.manager)
    with pytest.raises(CommandError):
        run_command(env.server.roots[0], env.source, '!!bm list ' + arguments)


def click_commands(message):
    def visit(value):
        if isinstance(value, dict):
            if 'clickEvent' in value:
                yield value['text'], value['clickEvent']['value']
            for child in value.values():
                yield from visit(child)
        elif isinstance(value, list):
            for child in value:
                yield from visit(child)
    return dict(visit(json.loads(message.to_json_str())))


def test_list_buttons_round_trip_and_recheck_permissions(env, bot, monkeypatch, player_data, capture_tasks):
    messages = []
    monkeypatch.setattr(env.player, 'reply', messages.append)
    env.server.on_execute = lambda _: setattr(bot, 'is_online', True)
    command.register_command_tree(env.server, env.manager)
    root = env.server.roots[0]
    run_command(root, env.player, '!!bm list offline search farm')
    buttons = click_commands(messages[-1])
    assert buttons['[扔出所有]'] == '!!bm SandBot all'
    assert buttons['[刷新]'] == '!!bm list offline search farm'
    assert not capture_tasks
    env.manager.remove_alias('SandBot', 'farm')
    run_command(root, env.player, buttons['[扔出所有]'])
    capture_tasks[0].result(timeout=2)
    assert env.server.commands[-1] == 'player sandbot dropStack all'
    env.player.permission = 0
    before = env.server.commands.copy()
    run_command(root, env.player, buttons['[扔出所有]'])
    assert '权限不足' in messages[-1].to_plain_text()
    assert env.server.commands == before


def test_read_only_panels_work_with_server_stopped(env, bot, monkeypatch):
    env.server.running = False
    before = Path(config.bots_path).read_bytes()

    def fail(*args, **kwargs):
        raise AssertionError('panels must not query Minecraft or schedule work')

    monkeypatch.setattr(env.manager, 'submit', fail)
    monkeypatch.setattr(utils, 'get_pos', fail)
    command.register_command_tree(env.server, env.manager)
    for args in ['', 'list', 'list offline search farm', 'farm', 'farm alias']:
        run_command(env.server.roots[0], env.source, ('!!bm ' + args).rstrip())
    assert len(env.source.messages) == 5
    assert Path(config.bots_path).read_bytes() == before
    assert env.server.commands == []


@pytest.mark.parametrize('change', ['rebind_alias', 'delete_and_readd'])
def test_queued_drop_never_switches_to_a_different_record(env, bot, change):
    release = threading.Event()
    workers = [env.manager.submit(release.wait, 5) for _ in range(4)]
    bot.is_online = True
    task = command.bot_action(env.source, {'mono': 'farm'}, 'all', env.manager)
    try:
        if change == 'rebind_alias':
            env.manager.remove_alias('SandBot', 'farm')
            env.manager.upsert_bot('OtherBot', 'farm')
        else:
            env.manager.remove_bot('SandBot')
            env.manager.upsert_bot('SandBot', 'farm')
        release.set()
        task.result(timeout=3)
        if change == 'rebind_alias':
            assert env.server.commands == ['player sandbot dropStack all']
        else:
            assert env.server.commands == []
            assert '记录已变更' in env.source.messages[-1]
    finally:
        release.set()
        for worker in workers:
            worker.result(timeout=3)
