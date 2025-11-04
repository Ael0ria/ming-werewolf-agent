from collections import defaultdict

class PhaseManager:
    def __init__(self):
        self.sequence = ["night", "day_discuss", "vote", "exile"]
        self.current = 0
        self.speaker_order = []
        self.votes = defaultdict(int)
        self.to_die = set()     # 夜晚死亡
        self.to_exile = None    # 白天放逐

    
    def next_phase(self, game):
        self.current = (self.current + 1) % len(self.sequence)
        phase = self.sequence[self.current]

        if phase == "day_discuss":
            game.day += 1
            self.speaker_order = [p.name for p in game.players.values() if p.is_alive]
            game.history.append(f"\n[第{game.day}天 · 白天]\n存活: {', '.join(self.speaker_order)}")
        elif phase == "night":
            self.to_die.clear()
            game.history.append(f"\n[第{game.day}天 · 夜晚]\n天黑请闭眼...")

        return phase
    
    