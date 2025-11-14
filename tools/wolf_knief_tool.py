from langchain.tools import tool
from typing import Any

@tool
def wolf_knife_tool(target: str) -> str:
    """
    狼人夜晚刀人
    """
    # game = game_state["game"]
    from agents.role_agent import RoleAgent
    game = RoleAgent.current_game
    wolf_name = RoleAgent.current_player
    
    wolf_id = game.id_mapping[wolf_name]
    target_name = None

    for name, pid in game.id_mapping.items():
        if pid == target:
            target_name = name
            break
    if not target_name or target_name not in game.alive:
        return f"[无效] {target}已出局"
        

    if target_name == wolf_name:
        return f"[无效] 不能刀自己"

    game.phase_mgr.wolf_knief.add(target_name)
    return f"[以刀 {target}"