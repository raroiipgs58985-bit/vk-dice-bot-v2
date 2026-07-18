import json
import time
from pathlib import Path
from typing import Optional

from config import TRIGGER_COOLDOWN_SECONDS


class ReplyManager:
    def __init__(self, path: str):
        self.path = Path(path)
        self.replies = self._load()
        self.cooldowns: dict[tuple[int, str], float] = {}

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            print(f"Файл автоответов не найден: {self.path}", flush=True)
            return {}
        except json.JSONDecodeError as error:
            print(f"Ошибка JSON в {self.path}: {error}", flush=True)
            return {}

        return data if isinstance(data, dict) else {}

    def find_available(
        self,
        peer_id: int,
        text: str,
    ) -> Optional[tuple[str, dict]]:
        lower_text = text.lower()
        now = time.monotonic()

        for trigger, data in self.replies.items():
            if trigger.lower() not in lower_text:
                continue

            cooldown_key = (peer_id, trigger.lower())
            last_used = self.cooldowns.get(cooldown_key, 0.0)

            if now - last_used < TRIGGER_COOLDOWN_SECONDS:
                continue

            self.cooldowns[cooldown_key] = now
            return trigger, data

        return None
