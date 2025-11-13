from .player import Player
from .roles import ROLE_POOL
from .phases import PhaseManager
from .victory import check_victory


class MingWerewolfGame:
    def __init__(self, player_role=None):

        self.players = {}
        # print(f"[DEBUG] player_role: {player_role}")
        for i, role_obj in enumerate(ROLE_POOL):
            name = role_obj.name
            player = Player(name, role_obj.team, role_obj)
            if name == player_role:
                player.is_player = True
                # print(f"[DEBUG] 设置玩家: {name} -> is_player=True")
            self.players[name] = player
            # print(f"[DEBUG] players[{name}].role.name = {player.role.name}")

        self.id_mapping = {name: f"玩家{i + 1}" for i, name in enumerate(self.players.keys())}
        self.reverse_mapping = {vid: name for name, vid in self.id_mapping.items()}
        # print(f"[DEBUG]匿名编号：{self.id_mapping}")

        self.player_id = self.id_mapping[player_role] if player_role else None



        self.alive = set(self.players.keys())
        self.day = 0
        self.history = []
        self.phase_mgr = PhaseManager()
        self.guard_target = None
        self.witch_knows_death = False
 
    
    def start(self):
        self.history.append("游戏开始！")
        phase = self.phase_mgr.next_phase(self)
        while True:
            result = check_victory(self)
            if result:
                self.history.append(f"[游戏结束!] {result}")
                break

            yield phase, self.get_state()
            phase = self.phase_mgr.next_phase(self)


    def get_state(self):
        return {
            "day": self.day,
            "phase": self.phase_mgr.sequence[self.phase_mgr.current],
            "alive": [p.name for p in self.players.values() if p.is_alive],
            "history": self.history[-10:],
            "speaker_order": self.phase_mgr.speaker_order,
            "current_speaker": self.phase_mgr.speaker_order[0] if self.phase_mgr.speaker_order else None
        }
    

    def speak(self, speaker, content):
        if speaker not in self.phase_mgr.speaker_order:
            return "错误： 不在发言顺序中"
        

        self.history.append(f"[{speaker}]: {content}")
        self.phase_mgr.speaker_order.pop(0)
        return "发言结束"


    def vote(self, voter, target):
        if target not in self.alive:
            return "无效目标"
        self.phase_mgr.votes[target] += 1
        
        self.history.append(f"[{voter}] 投票给 [{target}]")
        return f"{voter} 投给 {target}"


    def process_night(self) -> str:
        deaths = set()
        for t in self.phase_mgr.to_die:
            if t in self.alive:
                self.players[t].is_alive = False
                self.alive.remove(t)
                deaths.add(t)
        # 清空
        self.phase_mgr.to_die.clear()
        self.phase_mgr.wolf_knife.clear()
        self.phase_mgr.witch_poison.clear()
        self.phase_mgr.witch_heal.clear()

        if deaths:
            death_ids = [self.id_mapping[n] for n in deaths]
            result = f"昨夜死亡：{', '.join(death_ids)}"
        else:
            result = "昨夜平安夜"
        self.history.append(result)
        return result


    def check_end(self) -> str:
        result = check_victory(self)
        if result:
            self.history.append(f"[游戏结束!] {result}")
        return result