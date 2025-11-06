# test_graph.py
import os


from agents.graph import create_game_graph
from game_engine import MingWerewolfGame

app = create_game_graph()

game = MingWerewolfGame()  # 12人局
initial_state = {
    "game": game,
    "messages": [],
    "alive": [],
    "speaker_queue": [],
    "current_speaker": "",
    "voter_queue": [],
    "current_voter": "",
    "phase": "night"
}

print("🔥 《大明暗夜录》完整一局启动！")
day_count = 0
config = {"configurable": {}}
for output in app.stream(initial_state, config):
    if "judge" in output:
        ph = output["judge"]["phase"]
        print(f"\n=== {ph.upper()} ===")
    if "speak" in output:
        msg = output["speak"]["messages"][-1]
        print(f"  {msg.content[:80]}...")
    if "vote" in output:
        msg = output["vote"]["messages"][-1]
        print(f"  {msg.content[:80]}...")
    
    day_count += 1
    if day_count > 20:  # 防止无限，跑2天左右
        break

print("\n🎉 【完整游戏日志】")
print("\n".join(game.history[-20:]))
print(f"\n最终胜者：{game.check_end() or '继续中'}")