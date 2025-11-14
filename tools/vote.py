from langchain_core.tools import tool
from typing import Annotated

@tool
def vote_tool(target: str) -> str:
    """ 投票"""
    
    from agents.role_agent import RoleAgent
    game = RoleAgent.current_game
    voter_name = RoleAgent.current_player
    
    # game = game_state["game"]


    target_name = None
    for name, pid in game.id_mapping.items():
        if pid == target:
            target_name = name
            break
    if not target_name or target_name not in game.alive:
        return f"[无效] {target} 已出局"
    
    if target_name == voter_name:
        return f"[无效] 不能投票给自己"


    # 记录投票
    # votes = game_state.setdefault("votes", {})
    # votes[target] = votes.get(target, 0) + 1

    # return f"【投票】{voter_name} → {target} （当前 {votes[target]} 票）"
    return f"已投票给{target}"