from langchain_core.tools import tool
from typing import Annotated

@tool
def vote_tool(target: str, voter_name: str, game_state: dict) -> str:
    """ 投票"""
    game = game_state["game"]
    alive = game.alive

    if target not in alive:
        return f"[无效] {target} 已出局"
    if target == voter_name:
        return f"[无效] 不能投票给自己"

    # 记录投票
    votes = game_state.setdefault("votes", {})
    votes[target] = votes.get(target, 0) + 1

    return f"【投票】{voter_name} → {target} （当前 {votes[target]} 票）"