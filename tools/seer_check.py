from langchain_core.tools import tool
from typing import Annotated 


@tool
def seer_check_tool(
    target: Annotated[str, "要查验的玩家姓名"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """杨涟查验身份（返回：好人/狼人）"""
    game = game_state["game"]
    player = game.players.get(target)
    if not player or not player.is_alive:
        return "查验失败：目标已死或不存在"

    if player.team in ["阉党", "后金"]:
        return f"查验结果 {target} 是 狼人！"
    else:
        return f"查验结果 {target} 是 好人！"
    
    