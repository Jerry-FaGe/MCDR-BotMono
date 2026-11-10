import re
import threading
import time

from mcdreforged.api.types import PluginServerInterface, ServerInterface

from .config import Config, config, is_finite_number
from . import utils


class Bot:
    def __init__(self, server: PluginServerInterface | ServerInterface, name: str, aliases: list[str],
                 settings: Config | None = None,
                 confirmed_name: str | None = None):
        settings = settings or config
        if not isinstance(name, str) or re.fullmatch(r'[A-Za-z0-9_]{1,16}', name) is None:
            raise ValueError('假人名称只能包含 1 到 16 个英文字母、数字或下划线')
        self.server = server
        self.name = name
        self._expected_name = f'{settings.bot_name_prefix}{name.lower()}{settings.bot_name_suffix}'
        if re.fullmatch(r'[A-Za-z0-9_]{3,16}', self._expected_name) is None:
            raise ValueError(f'{name}: 加上前后缀后的游戏名必须是 3 到 16 个英文字母、数字或下划线')
        self._confirmed_name: str | None = None
        if confirmed_name is not None:
            if not isinstance(confirmed_name, str) or re.fullmatch(r'[A-Za-z0-9_]{3,16}', confirmed_name) is None:
                raise ValueError(f'{name}: confirmed_name 必须是 3 到 16 个英文字母、数字或下划线')
            self.confirm_name(confirmed_name)
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) and alias and not any(
                ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in alias
            ) for alias in aliases
        ):
            raise ValueError(f'{name}: aliases 必须是字符串列表，每个别名须非空且不含空白或控制字符')
        identities = {name.casefold(), self.real_name.casefold()}
        self.aliases = []
        for alias in aliases:
            key = alias.casefold()
            if key not in identities:
                self.aliases.append(alias)
                identities.add(key)
        self._state = threading.Condition()
        self._action_lock = threading.RLock()
        self._online = False
        self._cancelled = False

    @staticmethod
    def _vector(values, length: int, field: str) -> list[float]:
        if not isinstance(values, (list, tuple)) or len(values) != length or not all(
            is_finite_number(value) for value in values
        ):
            raise ValueError(f'{field} 必须包含 {length} 个有限数值')
        return [float(value) for value in values]

    @property
    def expected_name(self) -> str:
        return self._expected_name

    @property
    def confirmed_name(self) -> str | None:
        return self._confirmed_name

    @property
    def real_name(self) -> str:
        return self._confirmed_name or self._expected_name

    def confirm_name(self, player: str) -> bool:
        """Learn spelling, not a new identity; the manager serializes observations."""
        if not isinstance(player, str) or re.fullmatch(r'[A-Za-z0-9_]{3,16}', player) is None:
            return False
        if player.casefold() != self.expected_name.casefold() or player == self._confirmed_name:
            return False
        self._confirmed_name = player
        return True

    @property
    def is_online(self) -> bool:
        with self._state:
            return self._online

    @is_online.setter
    def is_online(self, value: bool) -> None:
        with self._state:
            self._online = value
            self._state.notify_all()

    def cancel(self) -> None:
        with self._state:
            self._cancelled = True
            self._state.notify_all()

    def _execute(self, command: str) -> bool:
        with self._state:
            if self._cancelled or not self.server.is_server_running():
                return False
            self.server.execute(command)
            return True

    # --- 核心动作 ---

    def spawn(self, executor: str | None = None) -> bool:
        """在执行玩家的当前位置召唤；控制台使用 Carpet 默认位置和生存模式。"""
        with self._action_lock:
            with self._state:
                if self._cancelled or not self.server.is_server_running():
                    return False
                if self._online:
                    return True
            if executor is None:
                command = f'player {self.real_name} spawn in survival'
            else:
                if not isinstance(executor, str) or re.fullmatch(r'[A-Za-z0-9_]{3,16}', executor) is None:
                    raise ValueError('无效的执行玩家名')
                # Query a single snapshot only when this serialized action needs a spawn.
                pos, dim, facing = utils.get_pos(self.server, executor)
                with self._state:
                    if self._cancelled or not self.server.is_server_running():
                        return False
                    if self._online:
                        return True
                if pos is None or dim is None or facing is None:
                    raise ValueError('无法获取玩家位置，请确认玩家在线并检查 MinecraftDataAPI 日志')
                pos_str = ' '.join(map(str, self._vector(pos, 3, 'Pos')))
                facing_str = ' '.join(map(str, self._vector(facing, 2, 'Rotation')))
                if not isinstance(dim, str) or re.fullmatch(r'[a-z0-9_.-]+:[a-z0-9_./-]+', dim) is None:
                    raise ValueError('无效的维度 ID')
                command = (f'execute as {executor} run player {self.real_name} spawn '
                           f'at {pos_str} facing {facing_str} in {dim}')
            if not self._execute(command):
                return False

            deadline = time.monotonic() + config.spawn_max_wait_time
            with self._state:
                while not self._online and not self._cancelled and self.server.is_server_running():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._state.wait(min(config.spawn_check_interval, remaining))
                if self._online and not self._cancelled and self.server.is_server_running():
                    return True
            self.server.logger.warning(f'[BotMono] 未能确认假人 {self.name} 上线，操作已终止')
            return False

    def kill(self):
        """下线假人"""
        with self._action_lock:
            return self._execute(f'player {self.real_name} kill')

    def _drop(self, command: str, executor: str | None) -> bool:
        with self._action_lock:
            if not self.spawn(executor=executor):
                return False
            return self._execute(f'player {self.real_name} {command}')

    # --- 交互动作 ---

    def drop_one(self, executor: str | None = None) -> bool:
        """扔出主手的一件物品。"""
        return self._drop('drop once', executor)

    def drop_all(self, executor: str | None = None) -> bool:
        """扔出全部物品栏物品（Carpet dropStack all）。"""
        return self._drop('dropStack all', executor)

    def drop_handall(self, executor: str | None = None) -> bool:
        """扔出主手整组物品。"""
        return self._drop('dropStack once', executor)

    # --- 数据转换 ---

    def to_dict(self) -> dict:
        data = {
            'aliases': self.aliases.copy(),
        }
        confirmed_name = self.confirmed_name
        if confirmed_name is not None:
            data['confirmed_name'] = confirmed_name
        return data

    @staticmethod
    def from_dict(server: PluginServerInterface, name: str, data: dict, settings: Config | None = None) -> "Bot":
        if not isinstance(data, dict):
            raise ValueError(f'{name}: 假人数据必须是 JSON 对象')
        unknown = set(data) - {'aliases', 'confirmed_name'}
        if unknown:
            raise ValueError(f'{name}: 未知假人数据项: {", ".join(sorted(unknown))}')

        return Bot(
            server=server,
            name=name,
            aliases=data.get('aliases', []),
            settings=settings,
            confirmed_name=data.get('confirmed_name'),
        )
