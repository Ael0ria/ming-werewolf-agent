# test_graph.py
import os


from agents.graph import create_game_graph
from game_engine import MingWerewolfGame

app = create_game_graph()

game = MingWerewolfGame()
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

print("🔥 《大明暗夜录》启动！")
day = 0
config = {"configurable": {}, "recursion_limit": 10000}
last_msg_count = 0

for output in app.stream(initial_state, config):
    node = next(iter(output))
    data = output[node]

    if node == "judge" and data.get("phase") == "speak":
        day += 1
        print(f"\n{'='*60}")
        print(f"第{day}天 白天发言  存活：{len(game.alive)}人")
        print(f"{'='*60}")

    # 2. 发言：打印所有新增发言
    if node == "speak" and data.get("messages"):
        current_msgs = data["messages"]
        new_msgs = current_msgs[last_msg_count:]  # 增量
        for msg in new_msgs:
            content = getattr(msg, 'content', str(msg))
            if "【发言】" in content:
                speaker = content.split("【发言】")[1].split(":", 1)[0].strip()
                text = content.split(":", 1)[1].strip()
                print(f"{speaker}：{text}")
                print("-"*50)
        last_msg_count = len(current_msgs)  # 更新

    # 3. 投票：同理增量打印
    if node == "vote" and data.get("messages"):
        current_msgs = data["messages"]
        new_msgs = current_msgs[last_msg_count:]
        for msg in new_msgs:
            content = getattr(msg, 'content', str(msg))
            print(f"{content}")
        last_msg_count = len(current_msgs)

    # 4. 放逐 + 夜晚
    if node == "exile" and data.get("messages"):
        current_msgs = data["messages"]
        new_msgs = current_msgs[last_msg_count:]
        for msg in new_msgs:
            print(f"{getattr(msg, 'content', str(msg))}")
        last_msg_count = len(current_msgs)

    # 5. 胜负
    if data.get("phase") == "end":
        print(f"\n{getattr(data['messages'][-1], 'content', '')}")
        break

# print("\n🎉 【完整游戏日志】")
# print("\n".join(game.history[-20:]))
# print(f"\n最终胜者：{game.check_end() or '继续中'}")