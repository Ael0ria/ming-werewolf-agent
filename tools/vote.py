from langchain_core.tools import tool
from typing import Annotated

@tool
def vote_tool(target: str, game_state: dict) -> str:
    """ 投票"""
    game = game_state["game"]
    voter = game_state["current_voter"]

    if target not in game.alive:
        return f"[无效] {target} 已出局"
    game.phase_mgr.votes[target] += 1
    return f"【投票】{voter} -> {target}  （当前{game.phase_mgr.votes[target]} 票）"