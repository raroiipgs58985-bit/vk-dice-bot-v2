import random
import re
from dataclasses import dataclass
from typing import Optional

from config import MAX_DICE_COUNT, MAX_DICE_SIDES


DICE_PATTERN = re.compile(r"(\d*)к(\d+)([+-]\d+)?", re.IGNORECASE)


@dataclass(frozen=True)
class DiceResult:
    rolls: list[int]
    total: int
    modifier: int
    dice: str
    comment: str


def roll(command: str) -> Optional[DiceResult | str]:
    command = command.strip()

    if not command.startswith("["):
        return None

    command = command[1:].strip().lower().replace("k", "к")
    comment = ""

    if "#" in command:
        command, comment = command.split("#", 1)
        command = command.strip()
        comment = comment.strip()

    match = DICE_PATTERN.fullmatch(command)
    if not match:
        return None

    count = int(match.group(1) or 1)
    sides = int(match.group(2))
    modifier = int(match.group(3) or 0)

    if count < 1:
        return "⛔ Количество кубиков должно быть не меньше 1."

    if count > MAX_DICE_COUNT:
        return f"⛔ Слишком много кубиков. Максимум: {MAX_DICE_COUNT}."

    if sides < 2:
        return "⛔ У кубика должно быть минимум 2 грани."

    if sides > MAX_DICE_SIDES:
        return f"⛔ Слишком много граней. Максимум: {MAX_DICE_SIDES}."

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    dice_name = f"{count}к{sides}"
    if modifier > 0:
        dice_name += f"+{modifier}"
    elif modifier < 0:
        dice_name += str(modifier)

    return DiceResult(
        rolls=rolls,
        total=total,
        modifier=modifier,
        dice=dice_name,
        comment=comment,
    )


def format_single_roll(player: str, result: DiceResult, quote: str) -> str:
    lines = [
        "🎲 КУБЯТНЯ 🎲",
        "━━━━━━━━━━━━━━━",
        "",
        f"👤 Игрок: {player}",
        f"🎲 Бросок: {result.dice}",
    ]

    if result.comment:
        lines.append(f"💬 {result.comment}")

    lines.extend([
        "",
        f"🎯 Выпало: {', '.join(map(str, result.rolls))}",
    ])

    if result.modifier > 0:
        lines.append(f"➕ Бонус: +{result.modifier}")
    elif result.modifier < 0:
        lines.append(f"➖ Штраф: {result.modifier}")

    lines.extend([
        f"🏆 Итог: {result.total}",
        "",
        "📜 Цитата дня:",
        f"«{quote}»",
    ])

    return "\n".join(lines)


def format_multiple_rolls(
    player: str,
    results: list[DiceResult | str],
    quote: str,
) -> str:
    lines = [
        "🎲 КУБЯТНЯ 🎲",
        "━━━━━━━━━━━━━━━",
        f"👤 Игрок: {player}",
        "",
    ]

    for number, result in enumerate(results, start=1):
        if isinstance(result, str):
            lines.append(f"{number}. {result}")
            continue

        rolls_text = ", ".join(map(str, result.rolls))
        comment_text = f" — {result.comment}" if result.comment else ""
        lines.append(
            f"{number}. {result.dice}: {rolls_text} → {result.total}{comment_text}"
        )

    lines.extend([
        "",
        "📜 Цитата дня:",
        f"«{quote}»",
    ])

    return "\n".join(lines)
