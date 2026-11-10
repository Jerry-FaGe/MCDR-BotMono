from pathlib import Path

import pytest

from bot_mono import view
from bot_mono.config import config
from bot_mono.storage import read_json, write_json


@pytest.mark.parametrize('record', [{}, {'aliases': []}])
def test_record_without_aliases_keeps_both_identities_and_display_name(env, record):
    write_json(config.config_path, {'bot_name_prefix': 'b_', 'bot_name_suffix': '_m'})
    write_json(config.bots_path, {'Stone': record})
    env.manager.reload_config()
    bot = env.manager.get_bot('Stone')
    assert bot.aliases == []
    assert env.manager.resolve_bot('STONE') is bot
    assert env.manager.resolve_bot('B_Stone_M') is bot
    assert 'Stone' in view.render_bot_summary(bot).to_plain_text()
    env.manager.save()
    env.manager.load()
    assert read_json(config.bots_path) == {'Stone': {'aliases': []}}
    assert env.manager.resolve_bot('b_stone_m') is env.manager.get_bot('Stone')


def test_aliases_store_only_extra_names_in_first_occurrence_order(env):
    write_json(config.config_path, {'bot_name_prefix': 'b_'})
    write_json(config.bots_path, {'Stone': {
        'aliases': ['STONE', 'B_Stone', '石头', 'stone', 'Straße', 'STRASSE', 'shitou', '石头'],
    }})
    env.manager.reload_config()
    bot = env.manager.get_bot('Stone')
    assert bot.aliases == ['石头', 'Straße', 'shitou']
    for target in ['stone', 'B_STONE', '石头', 'strasse', 'SHITOU']:
        assert env.manager.resolve_bot(target) is bot
    assert view.render_feedback('ok', bot=bot).to_plain_text() == '[BM] 石头 · ok'
    env.manager.save()
    assert read_json(config.bots_path)['Stone']['aliases'] == ['石头', 'Straße', 'shitou']
    for alias in ['石头', 'STRASSE', 'shitou']:
        assert env.manager.remove_alias('b_stone', alias)
    env.manager.load()
    bot = env.manager.resolve_bot('stone')
    assert bot.aliases == []
    assert env.manager.resolve_bot('b_stone') is bot
    assert view.render_feedback('ok', bot=bot).to_plain_text() == '[BM] Stone · ok'


@pytest.mark.parametrize('legacy', [{'nicknames': ['Stone', '石头']}, {'nick': '石头'}])
@pytest.mark.parametrize('include_aliases', [False, True])
def test_legacy_alias_fields_are_rejected_without_rewriting(env, legacy, include_aliases):
    record = {**legacy, **({'aliases': []} if include_aliases else {})}
    write_json(config.bots_path, {'Stone': record})
    before = Path(config.bots_path).read_bytes()
    with pytest.raises(ValueError):
        env.manager.load()
    assert not env.manager.bots
    assert Path(config.bots_path).read_bytes() == before
