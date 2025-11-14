# game_engine/utils.py
def check_victory(game) -> str | None:
    alive = set(game.alive)
    
    # 无人存活
    if len(alive) == 0:
        return "【游戏结束】无人存活，天下大乱！"

    # 关键角色
    WEI = "魏忠贤"
    HUANG = "皇太极"
    LI = "李自成"
    VILLAINS = {WEI, HUANG, LI}
    
    alive_villains = alive & VILLAINS          # 存活的反派
    alive_ming = alive - VILLAINS              # 存活的明廷角色（非反派）

    # === 胜利条件 1：明廷胜利 —— 所有反派死亡（至少一个明廷存活，由 alive 非空保证）===
    if not alive_villains:
        return "【明廷胜利！奸佞尽除！】忠臣肃清内患，大明中兴有望！"

    # === 唯一存活者判定（用于后三种结局）===
    if len(alive) == 1:
        sole_survivor = next(iter(alive))
        if sole_survivor == WEI:
            return "【魏忠贤专权！阉党再起！】魏忠贤重掌东厂，朝堂再陷黑暗！"
        elif sole_survivor == HUANG:
            return "【大清建立！明廷倾覆！】皇太极入主中原，改元崇德！"
        elif sole_survivor == LI:
            return "【大顺政权建立！闯王称帝！】李自成一统天下，改元永昌！"

    # 其他情况：游戏继续（例如多个反派共存，或反派+明廷共存等）
    return None