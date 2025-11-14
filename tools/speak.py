from langchain_core.tools import tool
from typing import Annotated

@tool
def speak_tool(content: str) -> str:
    """发言阶段，玩家发言"""
    from agents.role_agent import RoleAgent
    game = RoleAgent.current_game
    player_name = RoleAgent.current_player
    # game = game_state["game"]
    
    # speaker = game_state["current_speaker"]  # 真实姓名
    if hasattr(game, 'speak'):
        game.speak(player_name, content.strip())

    return content.strip()

