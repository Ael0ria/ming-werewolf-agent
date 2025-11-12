# agents/graph.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
import random
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage, AIMessage
from game_engine import MingWerewolfGame
from tools import *
from .role_agent import RoleAgent
from game_engine.victory import check_victory
import time
import threading

class GameState(TypedDict):
    game: MingWerewolfGame
    phase: str
    messages: List[AnyMessage]
    alive: List[str]
    speaker_queue: List[str]
    current_speaker: str
    night_actors: List[str]
    voter_queue: List[str]
    current_voter: str

def create_game_graph():
    graph = StateGraph(GameState)

    def judge_node(state: GameState) -> GameState:
        game = state["game"]
        pm = state["game"].phase_mgr
        pm.next_phase(state["game"])
        next_phase = pm.sequence[pm.current]

        if next_phase == "day_discuss":
            nigth_msg = game.process_night()
            state["messages"].append(AIMessage(content=nigth_msg))

            victory = check_victory(game)
            if victory:
                state["phase"] = "end"
                state["messages"].append(AIMessage(content=f"[游戏结束] {victory}"))
                return state

            state["phase"] = "speak"  # 交给 speak_node 自己处理
        elif next_phase == "vote":
            state["phase"] = "vote"
        elif next_phase == "exile":
            state["phase"] = "exile"
        elif next_phase == "night_action":
            state["phase"] = "night_action"
        return state


    _player_input = None
    _input_ready = threading.Event()

    _player_vote = None
    _vote_ready = threading.Event()

    _player_night_action = None
    _night_action_ready = threading.Event()

    def _speak_input_with_timeout():
        global _player_input
        try:
            _player_input = input("\n> ")
        except:
            _player_input = None
        finally:
            _input_ready.set()

    def _vote_input_with_timeout():
        global _player_vote
        try:
            _player_vote = input("\n> ").strip()
        except:
            _player_vote = None
        finally:
            _vote_ready.set()

    def _night_input_with_timeout():
        global _player_night_action
        try:
            _player_night_action = input("\n> ").strip()
        except:
            _player_night_action = None
        finally:
            _night_action_ready.set()


    def speak_node(state: GameState) -> GameState:
        game = state["game"]

        if "speaker_queue" not in state or not state["speaker_queue"]:
            from game_engine.roles import ROLE_POOL
            state["speaker_queue"] = [r.name for r in ROLE_POOL if r.name in game.alive]
            print(f"[DEBUG] speaker_queue: {state['speaker_queue']}") 
            state["current_speaker"] = state["speaker_queue"][0]

        while state["speaker_queue"]:
            speaker_name = state["speaker_queue"][0]
            speaker = game.players[speaker_name]

            # state["current_speaker"] = speaker_name


            if speaker.is_player:
                role = speaker.role
                print(f"\n[轮到你发言 - {speaker_name}]")
                print(f"身份：{role.name}")
                print(f"阵营：{role.team}")
                print(f"技能：{role.description}")
                if role.night_action:
                    print("[夜晚可行动]", end="")
                    if role.has_poison: print(" 毒药", end="")
                    if role.has_medicine: print(" 解药", end="")
                    print()
                print("请在 5 分钟内输入发言内容（超时将视为沉默）")
                # print(f"\n[轮到你来发言 - {speaker_name}]")
                # print(f"身份：{speaker.role.name} | 阵营： {speaker.role.team} | 技能：{speaker.role.description}")
                # print("请在5分钟输入发言内容（超时视为沉默）")

                global _player_input
                _player_input = None
                _input_ready.clear()

                thread = threading.Thread(
                    target=_speak_input_with_timeout,
                    # args=(f"\n剩余时间：5:00 > ",),
                    daemon=True
                )
                timeout = 300
                thread.start()

                if _input_ready.wait(timeout):
                    text = _player_input.strip() if _player_input else ""

                    if not text:
                        text = "(此人沉默不语)"
                    msg = f"[发言] {speaker_name}: {text}"
                else:
                    msg = f"[发言] {speaker_name}: (此人沉默不语)"
                result = AIMessage(content=msg)
                state["messages"].append(result)
            else:

                tools = [speak_tool]
                if speaker_name == "杨涟": tools += [seer_check_tool]
                if speaker_name == "魏忠贤": tools += [wei_tamper_tool]

                agent = RoleAgent(speaker_name, game, tools)
                result = agent.invoke(state, config={"configurable": {}})

                if isinstance(result, AIMessage):
                    ai_text = result.content.strip()
                else:
                    ai_text = str(result).strip()
                
                msg = f"[发言] {ai_text}"
                result = AIMessage(content=msg)
                state["messages"].append(result)
            
            state["speaker_queue"].pop(0)
            if state["speaker_queue"]:
                state["current_speaker"] = state["speaker_queue"][0]
            else:
                break  

        state["phase"] = "vote"
        return state

    def vote_node(state: GameState) -> GameState:
        game = state["game"]
        alive_names = list(game.alive)

        print(f"\n第{state.get('day', 1)}天，投票阶段，存活：{len(alive_names)}人")
        print("=".center(60, "="))

        # 只初始化一次
        if "voter_queue" not in state or not state["voter_queue"]:
            from game_engine.roles import ROLE_POOL
            state["voter_queue"] = [r.name for r in ROLE_POOL if r.name in game.alive]
            print("[DEBUG] vote_queue: {state['voter_queue']}")

        votes = {}
        # 连续投票，但只执行一次 while
        while state["voter_queue"]:
            voter_name = state["voter_queue"][0]
            voter = game.players[voter_name]


            if voter.is_player:
                print(f"\n[轮到你投票 - {voter_name}]")
                print(f"存活玩家：{', '.join(alive_names)}")
                print("请输入你要投票放逐的玩家姓名（5分钟超时随机投票）")

                global _player_vote
                _player_vote = None
                _vote_ready.clear()

                thread = threading.Thread(
                    target = _vote_input_with_timeout,
                    daemon=True
                )
                thread.start()

                if _vote_ready.wait(300):
                    target = _player_vote.strip() if _player_vote else ""
                    if not target or target not in alive_names:
                        target = random.choice([n for n in alive_names if n != voter_name])
                        print(f"输入无效，随机投票给：{target}")
                    else:
                        print(f"投票给：{target}")
                else:
                    target = random.choice([n for n in alive_names if n != voter_name])
                    print(f"超时，随机投票给：{target}")

                votes.setdefault(target, []).append(voter_name)

            else:
                tools = [vote_tool]
                agent = RoleAgent(voter_name, game, tools)
                result = agent.invoke(state, config={"configurable": {}})

                ai_text = result.content.strip()
                target = None
                for name in alive_names:
                    if name in ai_text and name != voter_name:
                        target = name
                        break
                
                if not target:
                    target = random.choice([n for n in alive_names if n != voter_name])


                votes.setdefault(target, []).append(voter_name)
                print(f"{voter_name} -> {target}")
                

            state["voter_queue"].pop(0)

        print("\n投票结果：")
        print("-"*60)
        max_votes = 0
        candidates = []
        for target, voters in votes.items():
            count = len(voters)
            print(f"{target}: {count}票 <- {', '.join(voters)}")
            if count > max_votes:
                max_votes = count
                candidates = [target]
            elif count == max_votes:
                candidates.append(target)
            
        if len(candidates) == 1:
            exiled = candidates[0]
            print(f"\n最高票：{exiled} ({max_votes}票 -> 被放逐！)")
        else:
            exiled = random.choice(candidates)
            print(f"\n票数并列：{', '.join(candidates)} -> 随机放逐：{exiled}！")

        game.players[exiled].is_alive = False
        if exiled in game.alive:
            game.alive.remove(exiled)

        print(f"【放逐】{exiled} 已出局，存活人数：{len(game.alive)}人")
        print("=" * 60)

        state["phase"] = "exile"
        # state["day"] = state.get("day", 1) + 1
        return state


    def exile_node(state: GameState) -> GameState:
        game = state["game"]

        victory = check_victory(game)
        if victory:
            state["phase"] = "end"
            state["messages"].append(AIMessage(content=f"[游戏结束]{victory}"))
            return state
        

        state["phase"] = "night_action"
        return state


    def night_action_node(state: GameState) -> GameState:

        global _player_night_action
        game = state["game"]
        alive = set(game.alive)
        player_name = None


        for name, p in game.players.items():
            if p.is_player:
                player_name = name
                break

        print(f"\n第{state.get('day', 1)}天，夜晚行动阶段")
        print("=".center(60, "="))

        if "night_action" not in state or not state["night_action"]:
            from game_engine.roles import ROLE_POOL 
            state["night_actors"] = [
                r.name for r in ROLE_POOL if r.name in alive and r.night_action
            ]

            print(f"[DEBUG] night_actors: {state['night_actors']}")


        wolves = {"魏忠贤", "皇太极"} & alive
        player_is_wolf = player_name in wolves

        if player_is_wolf:
            print(f"\n[狼人行动]轮到你 - {player_name}")
            print(f"存活玩家：{', '.join(alive - {player_name})}")
            print("请输入你要刀的玩家姓名（5分钟超时随机刀一人）：")

            
            _player_night_action = None
            _night_action_ready.clear()

            thread = threading.Thread(
                target=_night_input_with_timeout,
                daemon=True
            )
            thread.start()

            if _night_action_ready.wait(300):
                target = _player_night_action.strip()
                if not target or target not in alive or target == player_name:
                    target = random.choice(list(alive - {player_name}))
                    print(f"输入无效，随机刀：{target}")
                else:
                    print(f"你选择刀 -> {target}")

            else:
                target = random.choice(list(alive - {player_name}))
                print(f"超时，随机刀：{target}") 
        
            game.phase_mgr_wolf_knief.add(target)
            print(f"[狼人]{player_name} -> {target}")

            other_wolves = wolves - {player_name}
            for wolf in other_wolves:
                print(f"\n[狼人行动]{wolf} 这个在选择目标...")
                agent = RoleAgent(wolf, game, [wolf_kill])
                result = agent.invoke(state, config={"configurable":{"actor": wolf}})
                state["messages"].append(result)

                t = None
                for name in alive:
                    if name in result.content and name != wolf:
                        t = name
                        break

                if t:
                    game.phase_ngr.wolf_knief.add(t)
                    print(f"{wolf} 刀 -> {t}")

                else:
                    print(f"{wolf} 放弃刀人")
        else:
            for wolf in wolves:
                print("\n[狼人行动]{wolf} 正在选择目标...")
                agent = RoleAgent(wolf, game, [wolf_kill])
                result = agent.invoke(state, config={"configurable": {"actor": wolf}})
                state["messages"].append(result)

                target = None
                for name in alive:
                    if name in result.content and name != wolf:
                        target = name
                        break
                if target:
                    game.phase_mgr.wolf_knief.add(target)
                    print(f"{wolf}刀 -> {target}")

                else:
                    print(f"{wolf} 放弃刀人")

        ## 预言家
        if "杨涟" in alive:
            seer = game.players["杨涟"]
            if seer.is_player:
                print(f"\n[预言家行动]轮到你 - 杨涟")
                print(f"存活玩家：{', '}.join(alive -{'杨涟'})")
                print("请输入你要查验的玩家姓名")

                _night_action_ready.clear()
                thread = threading.Thread(target=_night_input_with_timeout, daemon=True)
                thread.start()

                if _night_action_ready.wait(300):
                    target = _player_night_action.strip()
                    if not target or target not in alive or target == "杨涟":
                        target = random.choice(list(alive - {"杨涟"}))
                        print(f"输入无效，随机查验：{target}")
                    else:
                        print(f"你查验：{target}")
                else:
                    target = random.choice(list(alive - {"杨涟"}))
                    print(f"超时，随机查验：{target}")

                # 查验结果
                team = game.players[target].role.team
                is_wolf = "狼" if team in {"阉党", "后金"} else "好人"
                msg = f"【查验】杨涟 → {target}：{is_wolf}"
                state["messages"].append(AIMessage(content=msg))
                print(msg)

            else:
                print(f"\n[预言家行动] 正在查验...")
                agent = RoleAgent("杨涟", game, [seer_check_tool])
                result = agent.invoke(state, config={"configurable": {"actor": "杨涟"}})
                state["messages"].append(result)
                print(result.content.strip())


        ## 女巫
        if "李自成" in alive:
            witch = game.players["李自成"]
            has_poison = witch.role.has_poison
            has_medicine = witch.role.has_medicine

            if witch.is_player and (has_poison or has_medicine):
                print("\n[女巫行动] 轮到你 - 李自成")
                if game.phase_mgr.wolf_knife:
                    print(f"昨夜被刀：{', '.join(game.phase_mgr.wolf_knife)}")
                print("输入格式：")
                if has_poison: print("  毒 玩家名")
                if has_medicine: print("  救 玩家名")
                print("  空 放弃行动")
                print("（5分钟超时自动放弃）")
                
                _player_night_action = None
                _night_action_ready.clear()
                thread = threading.Thread(target=_night_input_with_timeout, daemon=True)
                thread.start()

                if _night_action_ready.wait(300):
                    action = _player_night_action.strip().lower()
                    if action.startswith("毒 ") and has_poison:
                        target = action[2:].strip()
                        if target in alive and target != "李自成":
                            game.phase_mgr.witch_poison.add(target)
                            witch.role.has_poison = False
                            print(f"你毒 → {target}")
                    elif action.startswith("救 ") and has_medicine:
                        target = action[2:].strip()
                        if target in game.phase_mgr.wolf_knife:
                            game.phase_mgr.witch_save.add(target)
                            witch.role.has_medicine = False
                            print(f"你救 → {target}")
                    else:
                        print("你放弃行动")
                else:
                    print("超时，自动放弃")

            elif not witch.is_player and (has_poison or has_medicine):
                tools = []
                if has_poison: tools.append(witch_poison_tool)
                if has_medicine: tools.append(witch_heal_tool)
                print(f"\n[女巫行动] 正在决策...")
                agent = RoleAgent("李自成", game, tools)
                result = agent.invoke(state, config={"configurable": {"actor": "李自成"}})
                state["messages"].append(result)
                print(result.content.strip())

        print("\n夜晚行动结束，天亮请睁眼！")
        print("="*60)

        state["phase"] = "day_discuss"
        return state

    # ====== 注册节点 ======
    graph.add_node("judge", judge_node)
    graph.add_node("speak", speak_node)
    graph.add_node("vote", vote_node)
    graph.add_node("night_action", night_action_node)
    graph.add_node("exile", exile_node)

    graph.set_entry_point("judge")

    # 条件跳转
    def route(state: GameState):
        phase = state["phase"]
        if phase == "speak":
            return "speak"
        if phase == "vote":
            return "vote"
        if phase == "night_action":
            return "night_action"
        if phase == "exile":
            return "exile"
        if phase == "end":
            return END
        return "judge"

    graph.add_conditional_edges(
        "judge", 
        route, 
        {
            "speak": "speak",
            "vote": "vote",
            "judge": "judge",
            "night_action": "night_action",
            "exile": "exile",
            "end": END
        })
    graph.add_edge("speak", "judge")
    graph.add_edge("vote", "judge")
    graph.add_edge("night_action", "judge")
    graph.add_edge("exile", "judge")

    return graph.compile()