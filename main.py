import os


from agents.graph import create_game_graph
from game_engine import MingWerewolfGame

app = create_game_graph()


print("🔥 《大明暗夜录》启动！")
def choose_player_role():
    roles = [
        "杨涟", "魏忠贤", "皇太极", "孙承宗", "袁崇焕",
        "钱谦益", "史可法", "吴伟业", "郑森", "卢象升", "李自成"
    ]
    print("\n" + "="*60)
    print("你将化身谁，改写大明历史？")
    print("="*60)
    for i, role in enumerate(roles, 1):
        print(f"[{i:2}] {role}")

    print("-"*60)

    while True:
        try:
            choice = int(input("请选择你的角色 [1]-[11]:").strip())
            if 1 <= choice <= 11:
                selected = roles[choice - 1]
                print(f"\n你选择扮演： [{selected}]\n")
                return selected
        except:
            pass
        print("无效输入，请输入正确的角色序号！")

player_role = choose_player_role()
game = MingWerewolfGame(player_role=player_role)
initial_state = {
    "game": game,
    "messages": [],
    "alive": list(game.alive),
    "speaker_queue": [],
    "current_speaker": "",
    "voter_queue": [],
    "current_voter": "",
    "phase": "day_discuss"
}

print("=" * 60)
day = 0
last_msg_count = 0  # 记录已打印的消息数
config = {"configurable": {}, "recursion_limit": 10000}


for output in app.stream(initial_state, config):
    node = next(iter(output))
    data = output[node]

    # 1. 新的一天
    if node == "judge" and data.get("phase") == "speak":
        day += 1
        print(f"\n第{day}天 白天发言  存活：{len(game.alive)}人")
        print("=" * 60)

    # 2. 发言：打印所有新增发言
    if node == "speak" and data.get("messages"):
        current_msgs = data["messages"]
        new_msgs = current_msgs[last_msg_count:]  # 增量
        for msg in new_msgs:
            content = getattr(msg, 'content', str(msg))
            if "[发言]" in content:
                parts = content.split("[发言]", 1)[1].strip()
                speaker_text = parts.split(":", 1)
                if len(speaker_text) >= 2:
                    speaker = speaker_text[0].strip()
                    text = speaker_text[1].strip()
                    print(f"{speaker}：{text}")
                    print("-" * 60)
        last_msg_count = len(current_msgs)

    # 3. 投票：增量打印
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

    # 5. 游戏结束
    if data.get("phase") == "end":
        final_msg = data["messages"][-1].content if data["messages"] else "游戏结束"
        print(f"\n{final_msg}")
        break

# print("\n🎉 【完整游戏日志】")
# print("\n".join(game.history[-20:]))
# print(f"\n最终胜者：{game.check_end() or '继续中'}")