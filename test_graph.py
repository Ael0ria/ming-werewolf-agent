# test_graph.py
import os
os.environ["DASHSCOPE_API_KEY"] = "your-key-here"  # 替换为你的百炼API Key

from agents.graph import create_game_graph

app, game, agents = create_game_graph()
config = {"configurable": {"thread_id": "test1"}}

# 模拟一局
for output in app.stream({"game": game, "messages": [], "alive": [p.name for p in game.players.values() if p.is_alive]}, config):
    print(output)
    if "game" in output and output["game"].phase_mgr.sequence[output["game"].phase_mgr.current] == "exile":
        break

print("\n【游戏结束】")
print("\n".join(game.history[-10:]))