from langchain_core.tools import tool
from typing import Annotated

@tool
def witch_poison_tool(target: str, state: dict) -> str:
    """
    使用毒药的工具函数
    用于毒杀指定玩家，若毒药已用完则返回提示信息
    """
    game = state["game"]
    actor = state.get("current_actor") or state.get("actor")

    if not actor:
        return "[错误] 未知行动者"

    witch = game.players[actor]
    if not witch.role.has_poison:
        return "[无效] 你没有毒药"

    if target not in game.alive:
        return f"[无效] {target} 已出局"

    if target == actor:
        return "[无效] 不能毒自己"

    # 执行毒
    game.phase_mgr.witch_poison.add(target)
    witch.role.has_poison = False
    return f"【女巫毒】{actor} → {target}"


@tool
def witch_heal_tool(target: str, state: dict) -> str:
    """
    使用解药的工具函数
    用于救活指定玩家，若解药已用完则返回提示信息
    """
    game = state["game"]
    actor = state.get("current_actor") or state.get("actor")

    if target not in game.phase_mgr.wolf_knife:
        return "[无效] 此人未被刀"

    game.phase_mgr.witch_save.add(target)
    game.players[actor].role.has_medicine = False
    return f"【女巫救】{actor} → {target}"