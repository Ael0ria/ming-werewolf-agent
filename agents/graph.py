from typing import TypedDict, List, Optional, Annotated, Dict
from langgraph.graph import StateGraph, END
import random
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage, AIMessage, BaseMessage
from game_engine import MingWerewolfGame
from tools import *
from .role_agent import RoleAgent
from game_engine.victory import check_victory
import threading
import operator

# Reducer: always take the newest value
def replace_value(old, new):
    return new

class GameState(TypedDict):
    # Game state object — must be replaced entirely each time
    game: Annotated[MingWerewolfGame, replace_value]
    
    # Phase control — only one value allowed per step
    phase: Annotated[str, replace_value]
    
    # Message history — accumulate
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Day counter
    day: Annotated[int, replace_value]
    
    # Alive player names (for reference)
    alive: Annotated[List[str], replace_value]
    
    # Speaking queue
    speaker_queue: Annotated[List[str], replace_value]
    current_speaker: Annotated[Optional[str], replace_value]
    
    # Night action actors
    night_actors: Annotated[List[str], replace_value]
    
    # Voting
    voter_queue: Annotated[List[str], replace_value]
    current_voter: Annotated[Optional[str], replace_value]
    votes: Annotated[Dict[str, List[str]], replace_value]  # reset after exile


def create_game_graph():
    graph = StateGraph(GameState)

    # === Shared input handling (thread-safe) ===
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

    
    def judge_node(state: GameState) -> dict:
        current_phase = state.get("phase", "unknown")
        print(f"[DEBUG] judge_node called, current_phase = '{current_phase}'")
        game = state["game"]
        current_phase = state["phase"]
        messages = state["messages"].copy()

        # 游戏结束检查（可在任何阶段后触发）
        victory = check_victory(game)
        if victory:
            messages.append(AIMessage(content=f"[游戏结束] {victory}"))
            return {
                "messages": messages,
                "phase": "end",
                "game": game
            }

        if current_phase == "night_action":
            # 夜晚刚结束 → 进入白天发言
            night_msg = game.process_night()
            messages.append(AIMessage(content=night_msg))


            victory = check_victory(game)
            if victory:
                messages.append(AIMessage(content=f"[游戏结束] {victory}"))
                return {
                    "messages": messages,
                    "phase": "end",
                    "game": game
                }

            day = state.get("day", 0) + 1
            print(f"\n第{day}天 白天开始")
            return {
                "phase": "speak",
                "speaker_queue": [],   # 触发 speak_node 初始化
                "voter_queue": [],
                "votes": {},
                "messages": messages,
                "day": day,
                "alive": list(game.alive),
                "game": game
            }

        elif current_phase == "exile":
            # 放逐刚结束 → 进入夜晚
            return {
                "phase": "night_action",
                "speaker_queue": [],
                "voter_queue": [],
                "votes": {},
                "alive": list(game.alive),
                "game": game
            }

        elif current_phase in ["speak", "vote"]:
            return {"phase": current_phase, "game": game}

        else:

            return {
                "phase": "speak",
                "speaker_queue": [],
                "voter_queue": [],
                "votes": {},
                "day": 1,
                "alive": list(game.alive),
                "game": game
            }


    def speak_node(state: GameState) -> dict:
        game = state["game"]


        if not state.get("speaker_queue"):
            from game_engine.roles import ROLE_POOL
            alive_names = [r.name for r in ROLE_POOL if r.name in game.alive]
            day = state.get("day", 1)
            print(f"\n第{day}天 白天发言阶段 存活：{len(alive_names)}人")
            print("=" * 60)
            return {
                "phase": "speak",
                "speaker_queue": alive_names,
                "current_speaker": alive_names[0] if alive_names else None,
                "day": day,
                "game": game 
            }

        if not state["speaker_queue"]:
            return {"phase": "vote", "game": game}

        current_speaker = state["speaker_queue"][0]
        speaker = game.players[current_speaker]
        vid = game.id_mapping[current_speaker]

        if speaker.is_player:
            print(f"\n【轮到你发言 - {vid}】")
            print(f"身份：{speaker.role.name} | 阵营：{speaker.role.team}")
            print("请在 5 分钟内输入发言内容（超时沉默）")

            global _player_input
            _player_input = None
            _input_ready.clear()
            thread = threading.Thread(target=_speak_input_with_timeout, daemon=True)
            thread.start()

            if _input_ready.wait(300):
                text = _player_input.strip() or "(沉默)"
            else:
                text = "(超时沉默)"

            msg = f"玩家{vid.split('玩家')[1]}：{text}"
        else:
            print(f"\n【{vid} 发言中...】")
            tools = [speak_tool]
            agent = RoleAgent(current_speaker, game, tools)
            result = agent.invoke(state, config={"configurable": {"current_speaker": current_speaker}})
            clean_text = result.content.strip()
            msg = f"玩家{vid.split('玩家')[1]}：{clean_text}"

        new_queue = state["speaker_queue"][1:]
        return {
            "phase": "speak",
            "messages": [AIMessage(content=msg)],
            "speaker_queue": new_queue,
            "current_speaker": new_queue[0] if new_queue else None,
            "game": game
        }

    def vote_node(state: GameState) -> dict:
        game = state["game"]
        alive_names = list(game.alive)
        id_map = game.id_mapping
        rev_map = game.reverse_mapping
        alive_ids = [id_map[n] for n in alive_names]

        if not state.get("voter_queue"):
            from game_engine.roles import ROLE_POOL
            queue = [r.name for r in ROLE_POOL if r.name in game.alive]
            print(f"\n第{state.get('day', 1)}天 投票阶段 存活：{len(alive_ids)}人")
            print("=" * 60)
            return {
                "voter_queue": queue,
                "votes": {},
                "game": game
            }

        if not state["voter_queue"]:
            return {"phase": "exile", "game": game}

        voter_name = state["voter_queue"][0]
        voter_id = id_map[voter_name]

        if game.players[voter_name].is_player:
            print(f"\n【轮到你投票 - {voter_id}】")
            print(f"存活玩家：{', '.join(alive_ids)}")
            print("请输入你要投票放逐的玩家编号（如 玩家1），5分钟超时随机投票")

            global _player_vote
            _player_vote = None
            _vote_ready.clear()
            thread = threading.Thread(target=_vote_input_with_timeout, daemon=True)
            thread.start()

            if _vote_ready.wait(300):
                target_input = _player_vote.strip() if _player_vote else ""
                if target_input in alive_ids:
                    target_id = target_input
                    print(f"你投票给：{target_id}")
                else:
                    target_name = random.choice([n for n in alive_names if n != voter_name])
                    target_id = id_map[target_name]
                    print(f"输入无效，随机投票给：{target_id}")
            else:
                target_name = random.choice([n for n in alive_names if n != voter_name])
                target_id = id_map[target_name]
                print(f"超时，随机投票给：{target_id}")
        else:
            print(f"\n【{voter_id} 投票中...】")
            tools = [vote_tool]
            agent = RoleAgent(voter_name, game, tools)
            result = agent.invoke(state, config={"configurable": {"current_voter": voter_name}})
            ai_text = result.content.strip()
            target_id = None
            for aid in alive_ids:
                if aid in ai_text and aid != voter_id:
                    target_id = aid
                    break
            if not target_id:
                target_name = random.choice([n for n in alive_names if n != voter_name])
                target_id = id_map[target_name]
            print(f"{voter_id} → {target_id}")

        current_votes = state.get("votes", {})
        current_votes[target_id] = current_votes.get(target_id, []) + [voter_name]

        new_voter_queue = state["voter_queue"][1:]
        if not new_voter_queue:
            return {
                "votes": current_votes,
                "voter_queue": new_voter_queue,
                "phase": "exile",
                "game": game
                }
        else:
            return {
                "votes": current_votes,
                "voter_queue": new_voter_queue,
                "game": game
            }

    def exile_node(state: GameState) -> dict:
        game = state["game"]
        id_map = game.id_mapping
        rev_map = game.reverse_mapping
        votes = state["votes"]

        print("\n投票结果：")
        print("-" * 60)
        max_votes = 0
        candidates = []
        for target_id, voters in votes.items():
            count = len(voters)
            voter_ids = [id_map[v] for v in voters]
            print(f"{target_id}: {count}票 ← {', '.join(voter_ids)}")
            if count > max_votes:
                max_votes = count
                candidates = [target_id]
            elif count == max_votes:
                candidates.append(target_id)

        if len(candidates) == 1:
            exiled_id = candidates[0]
            print(f"\n最高票：{exiled_id} ({max_votes}票) → 被放逐！")
        else:
            exiled_id = random.choice(candidates)
            print(f"\n票数并列：{', '.join(candidates)} → 随机放逐：{exiled_id}！")

        exiled_name = rev_map[exiled_id]
        exiled_role = game.players[exiled_name].role
        print(f"【放逐】{exiled_id} → {exiled_name}（{exiled_role.name} · {exiled_role.team}）")

        game.players[exiled_name].is_alive = False
        if exiled_name in game.alive:
            game.alive.remove(exiled_name)

        print(f"存活人数：{len(game.alive)}人")
        print("=" * 60)

        return {
            # "phase": "night_action",
            "votes": {},
            "voter_queue": [],
            "alive": list(game.alive),
            "game": game
        }

    def night_action_node(state: GameState) -> dict:
        print("[DEBUG] 🌙 Night action started!")
        game = state["game"]
        alive = set(game.alive)
        player_name = None
        for name, p in game.players.items():
            if p.is_player:
                player_name = name
                break

        print(f"\n第{state.get('day', 1)}天，夜晚行动阶段")
        print("=".center(60, "="))

        wolves = {"魏忠贤", "皇太极"} & alive
        player_is_wolf = player_name in wolves
        id_map = game.id_mapping
        rev_map = game.reverse_mapping
        alive_ids = [id_map[n] for n in alive]
        final_knife_targets = set()

        if player_is_wolf:
            player_id = id_map[player_name]
            targetable_ids = [aid for aid in alive_ids if aid != player_id]
            print(f"\n【狼人行动】轮到你 - {player_id}")
            print(f"存活玩家：{', '.join(targetable_ids)}")
            print("请输入你要刀的玩家编号（如 玩家1），5分钟超时随机刀一人：")

            global _player_night_action
            _player_night_action = None
            _night_action_ready.clear()
            thread = threading.Thread(target=_night_input_with_timeout, daemon=True)
            thread.start()

            if _night_action_ready.wait(300):
                target_input = _player_night_action.strip()
                if target_input in targetable_ids:
                    target_id = target_input
                    target_name = rev_map[target_id]
                    print(f"你刀 → {target_id}")
                else:
                    target_name = random.choice([n for n in alive if n != player_name])
                    target_id = id_map[target_name]
                    print(f"输入无效，随机刀：{target_id}")
            else:
                target_name = random.choice([n for n in alive if n != player_name])
                target_id = id_map[target_name]
                print(f"超时，随机刀：{target_id}")

            final_knife_targets.add(target_name)
            print(f"【狼人刀】{player_id} → {target_id}")

            other_wolves = wolves - {player_name}
            for wolf in other_wolves:
                wolf_id = id_map[wolf]
                print(f"\n【狼人行动】{wolf_id} 正在选择目标...")
                agent = RoleAgent(wolf, game, [wolf_knife_tool])
                result = agent.invoke(state, config={"configurable": {"actor": wolf}})
                state["messages"].append(result)
                t_id = None
                for aid in alive_ids:
                    if aid in result.content and aid != wolf_id:
                        t_id = aid
                        break
                if t_id:
                    t_name = rev_map[t_id]
                    final_knife_targets.add(t_name)
                    print(f"{wolf_id} 刀 → {t_id}")
                else:
                    print(f"{wolf_id} 放弃刀人")
        else:
            for wolf in wolves:
                wolf_id = id_map[wolf]
                print(f"\n【狼人行动】{wolf_id} 正在选择目标...")
                agent = RoleAgent(wolf, game, [wolf_knife_tool])
                result = agent.invoke(state, config={"configurable": {"actor": wolf}})
                state["messages"].append(result)
                target_id = None
                for aid in alive_ids:
                    if aid in result.content and aid != wolf_id:
                        target_id = aid
                        break
                if target_id:
                    target_name = rev_map[target_id]
                    final_knife_targets.add(target_name)
                    print(f"{wolf_id} 刀 → {target_id}")
                else:
                    print(f"{wolf_id} 放弃刀人")

        new_messages = state["messages"].copy()
        if final_knife_targets:
            death_list = []
            for target_name in final_knife_targets:
                if target_name in game.alive:
                    game.players[target_name].is_alive = False
                    game.alive.remove(target_name)
                    target_id = id_map[target_name]
                    death_list.append(target_id)
                    print(f"【死亡】{target_id}（{target_name}）被狼刀身亡！")
            death_msg = f"昨夜被刀：{', '.join(death_list)}"
            new_messages.append(AIMessage(content=death_msg))
            print(death_msg)
        else:
            safe_msg = "昨夜平安夜"
            new_messages.append(AIMessage(content=safe_msg))
            print(safe_msg)

        game.phase_mgr.wolf_knife.clear()

        # Witch logic (李自成)
        if "李自成" in alive:
            witch = game.players["李自成"]
            has_poison = witch.role.has_poison
            has_medicine = witch.role.has_medicine
            witch_id = game.id_mapping["李自成"]

            if witch.is_player and (has_poison or has_medicine):
                print(f"\n[女巫行动]轮到你 - {witch_id}")
                if game.phase_mgr.wolf_knife:
                    knife_ids = [game.id_mapping[n] for n in game.phase_mgr.wolf_knife]
                    print(f"昨夜被刀：{', '.join(knife_ids)}")
                print("输入格式：")
                if has_poison: print("  毒 玩家X")
                if has_medicine: print("  救 玩家X")
                print("  空 放弃行动")
                print("（5分钟超时自动放弃）")

                _player_night_action = None
                _night_action_ready.clear()
                thread = threading.Thread(target=_night_input_with_timeout, daemon=True)
                thread.start()

                if _night_action_ready.wait(300):
                    action = _player_night_action.strip().lower()
                    if action.startswith("毒 ") and has_poison:
                        target_input = action[2:].strip()
                        if target_input in game.id_mapping.values() and target_input != witch_id:
                            target_name = game.reverse_mapping[target_input]
                            game.phase_mgr.witch_poison.add(target_name)
                            witch.role.has_poison = False
                            print(f"你毒 → {target_input}")
                    elif action.startswith("救 ") and has_medicine:
                        target_input = action[2:].strip()
                        if target_input in [game.id_mapping[n] for n in game.phase_mgr.wolf_knife]:
                            target_name = game.reverse_mapping[target_input]
                            game.phase_mgr.witch_save.add(target_name)
                            witch.role.has_medicine = False
                            print(f"你救 → {target_input}")
                    else:
                        print("你放弃行动")
                else:
                    print("超时，自动放弃")
            elif not witch.is_player and (has_poison or has_medicine):
                tools = []
                if has_poison: tools.append(witch_poison_tool)
                if has_medicine: tools.append(witch_heal_tool)
                print(f"\n【女巫行动】{witch_id} 正在决策...")
                agent = RoleAgent("李自成", game, tools)
                result = agent.invoke(state, config={"configurable": {"actor": "李自成"}})
                new_messages.append(result)
                print(result.content.strip())

        print("\n夜晚行动结束，天亮请睁眼！")
        print("=" * 60)


        return {
            "messages": new_messages,
            "game": game,
            # "phase": "day_discuss",
            "alive": list(game.alive),
            "speaker_queue": [],
            "voter_queue": [],
            "votes": {}

        }

    # === Register nodes ===
    graph.add_node("judge", judge_node)
    graph.add_node("speak", speak_node)
    graph.add_node("vote", vote_node)
    graph.add_node("night_action", night_action_node)
    graph.add_node("exile", exile_node)

    graph.set_entry_point("judge")

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
            "exile": "exile",
            "night_action": "night_action",
            "judge": "judge",
            END: END
        }
    )

    graph.add_conditional_edges(
        "speak",
        lambda s: "vote" if not s.get("speaker_queue") else "speak",
        {"vote": "vote", "speak": "speak"}
    )

    graph.add_conditional_edges(
        "vote",
        lambda s: "exile" if not s.get("voter_queue") else "vote",
        {"exile": "exile", "vote": "vote"}
    )

    graph.add_edge("exile", "judge")
    graph.add_edge("night_action", "judge")

    app = graph.compile()
    return app