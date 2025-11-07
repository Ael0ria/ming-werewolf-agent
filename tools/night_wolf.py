from langchain_core.tools import tool

@tool
def wolf_knife_tool(target: str, game_state: dict) -> str:
    """ 狼刀"""
    game = game_state["game"]
    actor = game_state["current_actor"]
    if game.players[target].role.name == "孙崇宗" and game.gurad_target == target:
        return f"[守卫保护] {target} 被守卫保护，刀刃无功！"
    game.phase_mgr.to_die.add(target)
    return f"[狼刀] {actor} 刀 {target}"


