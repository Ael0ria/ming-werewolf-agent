import random
from .player import Player
from .roles import ROLE_POOL
from .phases import PhaseManager
from .victory import check_victory
from collections import defaultdict

class MingWerewolfGame:
    def __init__(self, player_names=None):
        if player_names is None:
            player_names = [
                "杨涟", "魏忠贤", "皇太极", "孙承宗", "袁崇焕",
                "钱谦益", "史可法", "吴伟业", "郑森", "卢象升",
                "李自成"
            ]
        
        self.players = {name: Player(name) for name in player_names}
        self.day = 0
        self.history = []
        self.phase_mgr = PhaseManager()
        self.pending_tamper = None  # 魏忠贤篡改目标
        self.assign_roles()


    def assign_roles(self):
        roles = ROLE_POOL.copy()
        random.shuffle(roles)
        for name, player in self.players.items():
            player.role = roles.pop()
            player.team = player.role.team
        self.history.append("[身份分配完成]天黑请闭眼...")

    
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
        if self.phase_mgr.sequence[self.phase_mgr.current] != "vote":
            return "错误，非投票阶段"

        self.phase_mgr.votes[target] += 1
        return f"{voter} 投给 {target}"


    def night_action(self, actor, action_type, target):
        role = self.players[actor].role
        if role.name == "魏忠贤" and action_type == "tamper":
            self.pending_tamper = target
            return f"魏忠贤锁定篡改目标：{target}"

        # 其他行动预留
        return "行动执行"
    

    def to_dict(self):
        return {
            "day": self.day,
            "history": self.history.copy(),
            "players": {
                name: {
                    "name": p.name,
                    "role": p.role.name,
                    "team": p.team,
                    "is_alive": p.is_alive,
                    "last_will": p.last_will
                } for name, p in self.players.items()
            },
            "phase_mgr": {
                "current": self.phase_mgr.current,
                "speaker_order": self.phase_mgr.speaker_order.copy(),
                "votes": dict(self.phase_mgr.votes),
                "to_die": list(self.phase_mgr.to_die),
                "to_exile": self.phase_mgr.to_exile,
                "pending_tamper": self.pending_tamper
            }
        }

    @staticmethod
    def from_dict(data, game_instance=None):
        if game_instance is None:
            game_instance = MingWerewolfGame([])
        game_instance.day = data["day"]
        game_instance.history = data["history"]
        game_instance.pending_tamper = data["phase_mgr"]["pending_tamper"]
        
        # 恢复玩家
        for name, info in data["players"].items():
            if name in game_instance.players:
                p = game_instance.players[name]
                p.is_alive = info["is_alive"]
                p.last_will = info["last_will"]
        
        # 恢复阶段
        pm = game_instance.phase_mgr
        pm.current = data["phase_mgr"]["current"]
        pm.speaker_order = data["phase_mgr"]["speaker_order"]
        pm.votes = defaultdict(int, data["phase_mgr"]["votes"])
        pm.to_die = set(data["phase_mgr"]["to_die"])
        pm.to_exile = data["phase_mgr"]["to_exile"]
        
        return game_instance