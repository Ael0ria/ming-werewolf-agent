from game_engine import MingWerewolfGame

game = MingWerewolfGame()
for phase, state in game.start():
    print(f"\n=== {phase} ===")
    print(state["history"][-1] if state["history"] else "")
    if phase == "day_discuss" and state["current_speaker"]:
        print(f"{state['current_speaker']} 发言中...")
    if phase == "exile":
        break