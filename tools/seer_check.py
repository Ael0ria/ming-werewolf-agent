from langchain_core.tools import tool
from typing import Annotated
@tool
def seer_check_tool(
    target: Annotated[str, "要查验的玩家编号（如 玩家1）或姓名"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """杨涟查验身份（返回：好人/狼人）"""
    game = game_state["game"]
    target_name = target.strip()

    # === 自动映射：玩家X → 真实姓名 ===
    if target_name in game.reverse_mapping:
        target_name = game.reverse_mapping[target_name]  # 玩家3 → 皇太极
    elif target_name not in game.players:
        return "查验失败：目标不存在"

    player = game.players[target_name]
    if not player.is_alive:
        return "查验失败：目标已死"

    if player.role.team in ["阉党", "后金"]:
        return f"查验结果：{game.id_mapping[target_name]} 是 狼人！"
    else:
        return f"查验结果：{game.id_mapping[target_name]} 是 好人！"