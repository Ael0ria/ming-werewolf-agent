from langchain_core.tools import tool
from typing import Annotated

@tool
def speak_tool(content: str, game_state: dict) -> str:
    """发言阶段，玩家发言"""
    game = game_state["game"]
    speaker = game_state["current_speaker"]
    result = game.speak(speaker, content)
    return f"【发言】{speaker}: {content}"  

