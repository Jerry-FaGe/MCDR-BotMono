"""MinecraftDataAPI queries; all blocking calls run on manager workers."""

from mcdreforged.api.types import ServerInterface


def get_pos(server: ServerInterface, player_name: str):
    try:
        import minecraft_data_api as api
        data = api.get_player_info(player_name)
    except Exception as error:
        server.logger.warning(f'[BotMono] 获取玩家位置失败: {error}')
        return None, None, None
    if not isinstance(data, dict):
        return None, None, None
    return data.get('Pos'), data.get('Dimension'), data.get('Rotation')
