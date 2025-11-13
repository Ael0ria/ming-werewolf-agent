from .roles import Role
class Player:
    def __init__(self, name: str, team: str, role: Role):
        self.name = name
        self.team = team
        self.role = role
        self.is_alive = True
        self.is_player = False


    def __str__(self):
        return f"{self.name} ({'存活' if self.is_alive else '阵亡'})"