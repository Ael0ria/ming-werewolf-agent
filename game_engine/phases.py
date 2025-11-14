from collections import defaultdict

class PhaseManager:
    def __init__(self):
        self.sequence = ["night", "day_discuss", "vote", "exile"]
        self.current = 0
        self.speaker_order = []
        self.voter_order = []
        self.votes = defaultdict(int)
        self.to_die = set()     # 夜晚死亡
        self.to_exile = None    # 白天放逐

        self.wolf_knife = set()
        self.witch_poison = set()
        self.witch_heal = set()
    
    def next_phase(self, game):
        self.current = (self.current + 1) % len(self.sequence)
        phase = self.sequence[self.current]

        if phase == "day_discuss":
            game.day += 1
            game.history.append(f"\n【第{game.day}天】存活：{', '.join(game.alive)}")
        elif phase == "vote":
            game.history.append("【投票阶段】")
            self.votes.clear() 
        elif phase == "night":
            game.history.append("天黑请闭眼...")

        return phase
    
    