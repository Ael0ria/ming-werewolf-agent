from langchain_core.tools import tool
from typing import Annotated

@tool
def vote_tool(
    target: Annotated[str, "要投票放逐的玩家姓名"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """投票阶段，投票放逐一人"""
    game = game_state["game"]
    voter = game_state["current_voter"]
    return game.vote(voter, target)