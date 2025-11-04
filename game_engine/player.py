class Player:
    def __init__(self, name):
        self.name = name
        self.role = None
        self.team = None
        self.is_alive = True
        self.last_will = ""

    def __str__(self):
        return f"{self.name} ({'存活' if self.is_alive else '阵亡'})"