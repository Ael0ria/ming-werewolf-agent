from langchain_core.tools import tool
from typing import Annotated

@tool
def witch_poison_tool(
    target: Annotated[str, "要毒杀的玩家"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """
    使用毒药的工具函数
    用于毒杀指定玩家，若毒药已用完则返回提示信息
    """
    game = game_state["game"]
    actor = game_state["current_actor"]
    role = game.players[actor].role
    if not hasattr(role, 'has_poison') or not role.has_poison:
        return "毒药已用完"
    game.phase_mgr.to_die.add(target)
    role.has_poison = False
    return f"[毒药生效] {target} 今夜将死！"


@tool
def witch_heal_tool(
    target: Annotated[str, "要治疗的玩家"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """
    使用解药的工具函数
    用于救活指定玩家，若解药已用完则返回提示信息
    """
    game = game_state["game"]
    actor = game.state["current_actor"]
    role = game.players[actor].role
    if not hasattr(role, 'has_medicine') or not role.has_medicine:
        return "解药已用完！"
    game.phase_mgr.to_die.discard(target)
    role.has_medicine = False
    return f"[解药生效] {target} 被救活！"