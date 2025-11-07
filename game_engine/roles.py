from dataclasses import dataclass
from typing import Optional

@dataclass
class Role:
    name: str
    team: str
    description: str
    night_action: bool = False
    has_poison: bool = False
    has_medicine: bool = False


# ====================双狼阵营====================
魏忠贤 = Role("魏忠贤", "阉党", "掌控东厂，每晚可篡改一人发言", night_action=True)
皇太极 = Role("皇太极", "后金", "每晚可策反一人（转为后金卧底）", night_action=True)


# ====================神职====================
杨涟 = Role("杨涟", "明廷", "预言家，每晚查验一人身份（狼/非狼）", night_action=True)
孙承宗 = Role("孙承宗", "明廷", "守卫，每晚保护一人免刀", night_action=True)
袁崇焕 = Role("袁崇焕", "明廷", "猎人，被放逐时可带走一人", night_action=False)

# ====================平民====================
钱谦益 = Role("钱谦益", "明廷", "投机平民，无技能，但可倒戈", night_action=False)
史可法 = Role("史可法", "明廷", "铁血平民，无技能", night_action=False)
吴伟业 = Role("吴伟业", "明廷", "诗人平民，无技能", night_action=False)
郑森 = Role("郑森", "明廷", "少年平民，无技能", night_action=False)
卢象升 = Role("卢象升", "明廷", "悍将平民，无技能", night_action=False)

# ====================第三方====================
李自成 = Role("李自成", "农民军", "女巫+丘比特：有毒有解，可联两人", night_action=True, has_poison=True, has_medicine=True)


ROLE_POOL = [
    魏忠贤, 皇太极,
    杨涟, 孙承宗, 袁崇焕,
    钱谦益, 史可法, 吴伟业, 郑森,
    卢象升,
    李自成,
]