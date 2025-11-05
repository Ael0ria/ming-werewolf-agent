from langchain_core.tools import tool
from typing import Annotated

@tool
def speak_tool(
    content: Annotated[str, "你要发表的完整发言内容"],
    game_state: Annotated[dict, "当前游戏状态"]
) -> str:
    """在白天发言阶段发表言论"""
    game = game_state["game"]
    speaker = game_state["current_speaker"]
    return game.speak(speaker, content)

