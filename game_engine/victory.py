def check_victory(game):
    alive = [p for p in game.players.values() if p.is_alive]

    teams = {}

    for p in alive:
        teams[p.team] = teams.get(p.team, 0) + 1

    # 农民军胜利：李自成存活且独自存活
    if teams.get("农民军", 0) > 0 and len(alive) == 1:
        return "农民军胜利！大顺政权建立！"
    
    # 阉党胜利： 阉党人数 >= 明廷人数（含后金卧底）
    if teams.get("阉党", 0) >= teams.get("明廷", 0) + teams.get("后金", 0):
        return "阉党胜利！魏忠贤专权，天子称朕幼！"
    
    # 后金胜利：皇太极存货 + 后金系 >= 明廷
    if "皇太极" in [p.name for p in alive] and teams.get("后金", 0) >= teams.get("明廷", 0):
        return "后金胜利！大清入关，崇祯煤山自缢！"
    
    # 明廷胜利：狼全死 + 李自成死
    if teams.get("阉党", 0) == 0 and teams.get("后金", 0) == 0 and teams.get("农民军", 0) == 0:
        return "明廷胜利！虽千疮百孔，朱氏江山尚存！"
    
    return None