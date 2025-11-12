import random
from .player import Player
from .roles import ROLE_POOL
from .phases import PhaseManager
from .victory import check_victory
from collections import defaultdict

class MingWerewolfGame:
    def __init__(self, player_role=None):
        


        self.players = {}
        print(f"[DEBUG] player_role: {player_role}")
        for i, role_obj in enumerate(ROLE_POOL):
            name = role_obj.name
            player = Player(name, role_obj.team, role_obj)
            if name == player_role:
                player.is_player = True
                print(f"[DEBUG] 设置玩家: {name} -> is_player=True")
            self.players[name] = player
            print(f"[DEBUG] players[{name}].role.name = {player.role.name}")


        self.alive = set(self.players.keys())
        self.day = 0
        self.history = []
        self.phase_mgr = PhaseManager()
        self.pending_tamper = None  # 魏忠贤篡改目标
        self.guard_target = None
        self.witch_knows_death = False
        # self.assign_roles()


    # def assign_roles(self):
    #     roles = ROLE_POOL.copy()
    #     random.shuffle(roles)
    #     for name, player in self.players.items():
    #         player.role = roles.pop()
    #         player.team = player.role.team
    #         if player.role.name == "李自成":
    #             player.role.has_poison = True
    #             player.role.has_medicine = True
    #     self.history.append("[身份分配完成]天黑请闭眼...")

    
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
        
        # 魏忠贤篡改
        if self.pending_tamper == speaker:
            content = content.replace("好人", "金穴").replace("狼", "忠臣")
            self.pending_tamper = None

        self.history.append(f"[{speaker}]: {content}")
        self.phase_mgr.speaker_order.pop(0)
        return "发言结束"


    def vote(self, voter, target):
        if target not in self.alive:
            return "无效目标"
        self.phase_mgr.votes[target] += 1
        
        self.history.append(f"[{voter}] 投票给 [{target}]")
        return f"{voter} 投给 {target}"
    


    # def perform_exile(self) -> str:
    #     if not self.phase_mgr.votes:
    #         return "【无人放逐】"

    #     # 找最高票
    #     max_votes = max(self.phase_mgr.votes.values())
    #     candidates = [p for p, v in self.phase_mgr.votes.items() if v == max_votes]
    #     target = random.choice(candidates) if len(candidates) > 1 else candidates[0]

    #     # 执行放逐
    #     self.players[target].is_alive = False
    #     self.alive.remove(target)

    #     result = f"【放逐】{target} 出局！({max_votes}票)"
    #     self.history.append(result)

    #     # 清空票数（防止累加）
    #     self.phase_mgr.votes.clear()
    #     return result   

    def process_night(self) -> str:
        deaths = list(self.phase_mgr.to_die)
        details = []
        for t in deaths:
            if t in self.alive:
                self.players[t].is_alive = False
                self.alive.remove(t)
                if t in self.phase_mgr.wolf_knife:
                    details.append(f"{t}被狼刀死")
                elif t in self.phase_mgr.witch_poison:
                    details.append(f"{t}被巫师毒死")
              
                # self.history.append(f"【死亡】{t}")
        self.phase_mgr.to_die.clear()
        self.phase_mgr.wolf_knife.clear()
        self.phase_mgr.witch_poison.clear()
        if deaths:
            result = f"昨夜死亡：{', '.join(deaths)}"
        else:
            result = "昨夜平安夜"
        self.history.append(result)
        return result


    def check_end(self) -> str:
        result = check_victory(self)
        if result:
            self.history.append(f"[游戏结束!] {result}")
        return result