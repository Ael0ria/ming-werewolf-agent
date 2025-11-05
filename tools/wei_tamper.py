from langchain_core.tools import tool
from typing import Annotated

@tool
def wei_tamper_tool(
    target: Annotated[str, "要篡改发言的玩家"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """魏忠贤夜晚指定一人，次日其发言被篡改"""
    game = game_state["game"]
    if target not in game.players or not game.players[target].is_alive:
        return "篡改失败：目标玩家不存在"
    game.pending_tamper = target
    return f"[东厂密令]以锁定篡改目标: {target}, 明日发言将被扭曲！"