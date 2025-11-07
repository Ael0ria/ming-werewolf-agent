# game_engine/utils.py
def check_victory(game) -> str | None:
    alive = set(game.alive)
    
    # 提取阵营
    teams = {p: game.players[p].team for p in alive}
    
    # 统计各势力
    has_wei = "魏忠贤" in alive
    has_huang = "皇太极" in alive
    has_li = "李自成" in alive
    has_ming = any(t == "明廷" for t in teams.values())
    
    # 1. 明廷胜利：所有反派（狼 + 女巫）全死
    if not (has_wei or has_huang or has_li):
        return "【明廷胜利！奸佞尽除！】忠臣肃清内患，大明中兴有望！"
    
    # 2. 大顺政权建立：只有李自成一人存活
    if len(alive) == 1 and "李自成" in alive:
        return "【大顺政权建立！闯王称帝！】李自成一统天下，改元永昌！"
    
    # 3. 大清建立：明廷全灭 + 皇太极存活
    if not has_ming and has_huang:
        return "【大清建立！明廷倾覆！】皇太极入主中原，改元崇德！"
    
    # 4. 魏忠贤专权：明廷全灭 + 魏忠贤存活
    if not has_ming and has_wei:
        return "【魏忠贤专权！阉党再起！】魏忠贤重掌东厂，朝堂再陷黑暗！"
    
    # 5. 人数不足（保险）
    if len(alive) <= 1:
        return "【游戏结束】存活不足，局势失控！"
    
    return None  # 继续游戏