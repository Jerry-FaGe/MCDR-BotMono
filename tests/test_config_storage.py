from pathlib import Path

import pytest

from bot_mono import storage
from bot_mono.bot_manager import BotManager
from bot_mono.config import Config, config


def test_partial_permissions_use_defaults():
    assert Config.from_dict({'permission': {'bot': 2}}).permission == {'bot': 2, 'list': 3}


@pytest.mark.parametrize('data', [
    [], {'server': None}, {'config_path': 'somewhere'}, {'prefix_short': ''},
    {'prefix_short': '!!two words'}, {'prefix_short': '!!bad\x00'},
    {'spawn_check_interval': 0}, {'spawn_check_interval': -1},
    {'spawn_max_wait_time': float('inf')}, {'spawn_max_wait_time': float('nan')},
    {'spawn_max_wait_time': True}, {'spawn_max_wait_time': '10'}, {'spawn_max_wait_time': 10 ** 1000},
    {'permission': None}, {'permission': {'list': -1}},
    {'permission': {'bot': 5}}, {'permission': {'bot': True}},
    {'permission': {'other': 1}}, {'bot_name_prefix': '@'},
    {'bot_name_suffix': 'x' * 16},
])
def test_invalid_config_is_rejected(data):
    with pytest.raises(ValueError):
        Config.from_dict(data)


def test_bad_json_preserves_file_and_settings(env):
    path = Path(config.config_path)
    original = '{"prefix_short": "!!farm",'
    path.write_text(original, encoding='utf8')
    before = config.to_dict()
    with pytest.raises(ValueError):
        config.load()
    assert path.read_text(encoding='utf8') == original
    assert config.to_dict() == before


def test_invalid_field_does_not_partially_apply(env):
    storage.write_json(config.config_path, {'prefix_short': '!!farm', 'permission': {'bot': -1}})
    with pytest.raises(ValueError):
        config.load()
    assert config.prefix_short == '!!bm'
    assert config.permission == {'bot': 1, 'list': 3}


def test_atomic_write_preserves_original_if_serialization_fails(tmp_path):
    path = tmp_path / 'bots.json'
    storage.write_json(path, {'original': True})
    before = path.read_bytes()
    with pytest.raises(ValueError):
        storage.write_json(path, {'bad': float('nan')})
    assert path.read_bytes() == before
    assert list(tmp_path.glob('*.tmp')) == []


def test_atomic_write_preserves_original_if_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / 'bots.json'
    storage.write_json(path, {'original': True})
    before = path.read_bytes()

    def fail(*args):
        raise OSError('disk unavailable')

    monkeypatch.setattr(storage.os, 'replace', fail)
    with pytest.raises(OSError):
        storage.write_json(path, {'replacement': True})
    assert path.read_bytes() == before
    assert list(tmp_path.glob('*.tmp')) == []


def test_json_round_trip_does_not_rewrite_string_whitespace(tmp_path):
    path = tmp_path / 'data.json'
    data = {'aliases': ['a  b', 'hello [  world  ]'], 'position': [1, 2, 3]}
    storage.write_json(path, data)
    assert storage.read_json(path) == data


def test_first_install_creates_default_files_without_backups(fresh_env, caplog):
    manager = BotManager(fresh_env.server)
    try:
        assert 'ERROR' not in caplog.text
        assert storage.read_json(config.config_path) == Config().to_dict()
        assert storage.read_json(config.bots_path) == storage.read_json(
            Path(__file__).parents[1] / 'config/bots.default.json')
        assert len(manager.get_all_bots()) == 100
        assert {path.name for path in fresh_env.path.iterdir()} == {'config.json', 'bots.json'}
    finally:
        manager.shutdown()


def test_old_standalone_file_is_not_read_or_migrated(fresh_env):
    legacy = fresh_env.path.parent / 'BotMono.json'
    legacy.write_text('{"Fireworks": ["烟花火箭"]}', encoding='utf8')
    original = legacy.read_bytes()
    manager = BotManager(fresh_env.server)
    try:
        assert manager.get_all_bots()
        assert storage.read_json(config.bots_path) == storage.read_json(
            Path(__file__).parents[1] / 'config/bots.default.json')
    finally:
        manager.shutdown()
    assert legacy.read_bytes() == original


@pytest.mark.parametrize('record', [
    ['Fireworks', '烟花火箭'], {'nick': '烟花'}, {'pos': '1 64 2'},
    {'position': [1, 64, 2]}, {'dimension': 'minecraft:overworld'}, {'facing': [0, 0]},
    {'aliases': ['烟花'], 'unknown': True},
])
def test_unrecognized_record_formats_are_rejected_without_rewriting(env, bot, record):
    storage.write_json(config.bots_path, {'Fireworks': record})
    before = Path(config.bots_path).read_bytes()
    with pytest.raises(ValueError):
        env.manager.reload_config()
    assert env.manager.get_bot('SandBot') is bot
    assert Path(config.bots_path).read_bytes() == before


def test_example_files_validate_as_new_plugin_data(env):
    from bot_mono.bot import Bot

    root = Path(__file__).parents[1]
    settings = Config.from_dict(storage.read_json(root / 'config/config.example.json'))
    assert settings.to_dict() == Config().to_dict()
    data = storage.read_json(root / 'config/bots.default.json')
    bots = {name: Bot.from_dict(env.server, name, record, settings) for name, record in data.items()}
    BotManager._indexes(bots)
    assert len(bots) == 100
