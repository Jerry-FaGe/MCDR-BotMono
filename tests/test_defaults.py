import io
import json
from pathlib import Path

import pytest

import bot_mono
from bot_mono.bot_manager import BotManager, DEFAULT_BOTS_RESOURCE
from bot_mono.config import config
from bot_mono.storage import read_json, write_json


def test_initial_plugin_load_registers_defaults_without_spawning(fresh_env):
    bot_mono.on_load(fresh_env.server, None)
    manager = bot_mono.bot_manager_instance
    assert len(manager.get_all_bots()) == 100
    assert manager.get_online_bots() == []
    assert fresh_env.server.commands == []
    assert fresh_env.server.roots[0].literals == {'!!bm'}
    expected = {
        '烟花火箭': 'Fireworks', 'HUOJIAN': 'Fireworks', 'firework_rocket': 'Fireworks',
        '石头': 'Stone', 'shitou': 'Stone', '圆石': 'Cobblestone', 'yanjiangtong': 'LavaBucket',
        '橡木': 'OakLog', 'xiangmuyuanmu': 'OakLog', '投掷器': 'Dropper', 'touzhiqi': 'Dropper',
        '黏性活塞': 'StickyPiston', '粘性活塞': 'StickyPiston', 'sticky_piston': 'StickyPiston',
        '红石': 'Redstone', '比较器': 'Comparator', '骨粉': 'BoneMeal', '鞘翅': 'Elytra',
        '末影珍珠': 'EnderPearl', '潜影盒': 'ShulkerBox', '金萝卜': 'GoldenCarrot',
    }
    for alias, name in expected.items():
        assert manager.resolve_bot(alias).name == name


@pytest.mark.parametrize('prefix,suffix', [('', ''), ('bot_', ''), ('b_', '_m')])
def test_defaults_fit_custom_affixes_and_all_aliases_resolve(fresh_env, prefix, suffix):
    config.bot_name_prefix = prefix
    config.bot_name_suffix = suffix
    fresh_env.manager = BotManager(fresh_env.server)
    for bot in fresh_env.manager.get_all_bots():
        assert bot.real_name == prefix + bot.name.lower() + suffix
        assert 3 <= len(bot.real_name) <= 16
        assert len(bot.name) <= 12
        assert bot.confirmed_name is None
        assert bot.aliases
        assert bot.name.casefold() not in {alias.casefold() for alias in bot.aliases}
        for name in [bot.name, bot.real_name, *bot.aliases]:
            assert fresh_env.manager.resolve_bot(name.upper()) is bot


@pytest.mark.parametrize('data', [{}, {'CustomBot': {'aliases': ['CustomBot', '我的物品']}}])
def test_existing_registry_is_preserved_without_reading_defaults(fresh_env, monkeypatch, data):
    write_json(config.bots_path, data)
    before = Path(config.bots_path).read_bytes()

    def fail(*args):
        raise AssertionError('existing user registry must not read bundled defaults')

    monkeypatch.setattr(fresh_env.server, 'open_bundled_file', fail)
    fresh_env.manager = BotManager(fresh_env.server)
    fresh_env.manager.reload_config()
    assert set(fresh_env.manager.bots) == set(data)
    assert Path(config.bots_path).read_bytes() == before


def test_removed_defaults_and_custom_aliases_survive_reload_and_restart(fresh_env):
    manager = BotManager(fresh_env.server)
    fresh_env.manager = manager
    assert manager.remove_bot('Stone')
    assert manager.remove_alias('Fireworks', '火箭')
    assert manager.add_alias('Fireworks', '出行补给')
    manager.upsert_bot('CustomBot', '我的物品')
    before = Path(config.bots_path).read_bytes()
    manager.reload_config()
    manager.shutdown()
    fresh_env.manager = BotManager(fresh_env.server)
    assert fresh_env.manager.get_bot('Stone') is None
    assert fresh_env.manager.resolve_bot('火箭') is None
    assert fresh_env.manager.resolve_bot('出行补给').name == 'Fireworks'
    assert fresh_env.manager.resolve_bot('我的物品').name == 'CustomBot'
    assert Path(config.bots_path).read_bytes() == before


@pytest.mark.parametrize('contents', [b'{', b'[]', b'{"BadBot": []}',
                                      b'{"OneBot": {"aliases": ["same"]}, "TwoBot": {"aliases": ["same"]}}'])
def test_invalid_bundled_data_does_not_create_user_registry(fresh_env, monkeypatch, contents):
    monkeypatch.setattr(fresh_env.server, 'open_bundled_file', lambda _: io.BytesIO(contents))
    with pytest.raises(ValueError):
        BotManager(fresh_env.server)
    assert not Path(config.bots_path).exists()
    assert not list(fresh_env.path.glob('*.tmp'))


def test_missing_resource_is_reported_without_creating_empty_registry(fresh_env, monkeypatch):
    def fail(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr(fresh_env.server, 'open_bundled_file', fail)
    with pytest.raises(FileNotFoundError, match='bots.default.json'):
        BotManager(fresh_env.server)
    assert not Path(config.bots_path).exists()


def test_invalid_affixes_for_default_names_do_not_write_partial_registry(fresh_env):
    config.bot_name_prefix = 'prefix_'
    with pytest.raises(ValueError, match='16'):
        BotManager(fresh_env.server)
    assert not Path(config.bots_path).exists()


def test_corrupt_user_registry_is_not_replaced_by_defaults(fresh_env):
    path = Path(config.bots_path)
    path.write_text('{"my data":', encoding='utf8')
    before = path.read_bytes()
    with pytest.raises(ValueError):
        BotManager(fresh_env.server)
    assert path.read_bytes() == before


def test_default_resource_is_explicitly_packaged():
    root = Path(__file__).parents[1]
    metadata = read_json(root / 'mcdreforged.plugin.json')
    assert 'config' in metadata['resources']
    assert (root / DEFAULT_BOTS_RESOURCE).is_file()
    with (root / DEFAULT_BOTS_RESOURCE).open('rb') as stream:
        assert len(json.load(stream)) == 100
