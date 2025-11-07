from langchain_core.tools import tool

@tool
def guard_protect_tool(target: str, game_state: dict) -> str:
    """守卫保护一位玩家"""
    game = game_state["game"]
    game.guard_target = target

    return f"[守卫]今夜保护{target}"