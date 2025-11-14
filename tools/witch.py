from langchain_core.tools import tool
from typing import Annotated

@tool
def witch_poison_tool(target: str) -> str:
    """
    使用毒药的工具函数
    用于毒杀指定玩家，若毒药已用完则返回提示信息
    """
    # game = state["game"]
    from agents.role_agent import RoleAgent
    game = RoleAgent.current_game
    witch_name = RoleAgent.current_player
    # actor = state.get("current_actor") or state.get("actor")

    witch = game.players[witch_name]


    
    if not witch.role.has_poison:
        return "[无效] 你没有毒药"

    target_name = None
    for name, pid in game.id_mapping.items():
        if pid == target:
            target_name = name
            break

    if not target_name or target_name not in game.alive:
        return f"[无效] {target} 已出局"

    if target == witch_name:
        return "[无效] 不能毒自己"

    # 执行毒
    game.phase_mgr.witch_poison.add(target_name)
    witch.role.has_poison = False
    return f"已毒杀{target}"


@tool
def witch_heal_tool(target: str) -> str:
    """
    使用解药的工具函数
    用于救活指定玩家，若解药已用完则返回提示信息
    """
    # game = state["game"]
    from agents.role_agent import RoleAgent
    game = RoleAgent.current_game
    witch_name = RoleAgent.current_player

    witch = game.players[witch_name]

    if not witch.role.has_medicine:
        return "[无效] 你没有解药"
    
    knife_targets = [game.id_mapping[n] for n in game.phase_mgr.wolf_knife]
    if target not in knife_targets:
        return f"[无效]{target}未被刀"

    target_name = game.reverse_mapping[target]
    if target_name not in game.phase_mgr.wolf_knife:
        return "[无效] 此人未被刀"

    

    game.phase_mgr.witch_save.add(target_name)
    witch.role.has_medicine = False
    return f"以救活{target}"