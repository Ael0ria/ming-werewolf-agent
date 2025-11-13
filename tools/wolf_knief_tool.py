from langchain.tools import tool
from typing import Any

@tool
def wolf_knife_tool(target: str, game_state: dict) -> str:
    """
    狼人夜晚刀人
    """
    game = game_state["game"]
    actor = game_state("current_actor") or game_state.get("actor")

    if not actor:
        return f"[无效] {target}已出局"

    if target == actor:
        return f"[无效] 不能刀自己"

    game.phase_mgr.wolf_knief.add(target)
    return f"[狼人刀]{actor} -> {target}"