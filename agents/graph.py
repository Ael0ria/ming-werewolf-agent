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

    # ====== speak_node 保持不变 ======
    def speak_node(state: GameState) -> GameState:
        game = state["game"]

        # 初始化队列（只第一次）
        if "speaker_queue" not in state or not state["speaker_queue"]:
            state["speaker_queue"] = list(game.alive)
            state["current_speaker"] = state["speaker_queue"][0]

        # 连续处理所有人
        while state["speaker_queue"]:
            speaker = state["current_speaker"]
            tools = [speak_tool]
            if speaker == "杨涟": tools += [seer_check_tool]
            if speaker == "魏忠贤": tools += [wei_tamper_tool]

            agent = RoleAgent(speaker, game, tools)
            result = agent.invoke(state, config={"configurable": {}})
            state["messages"].append(result)

            # 移除当前发言者
            state["speaker_queue"].pop(0)
            if state["speaker_queue"]:
                state["current_speaker"] = state["speaker_queue"][0]
            else:
                break  # 所有人都发言完

        # 进入投票
        state["phase"] = "vote"
        return state

    def vote_node(state: GameState) -> GameState:
        game = state["game"]

        # 只初始化一次
        if "voter_queue" not in state or not state["voter_queue"]:
            state["voter_queue"] = list(game.alive)
            state["current_voter"] = state["voter_queue"][0]

        # 连续投票，但只执行一次 while
        while state["voter_queue"]:
            voter = state["current_voter"]
            agent = RoleAgent(voter, game, [vote_tool])
            result = agent.invoke({**state, "current_voter": voter}, config={"configurable": {}})
            state["messages"].append(result)

            state["voter_queue"].pop(0)
            if state["voter_queue"]:
                state["current_voter"] = state["voter_queue"][0]
            else:
                break

        state["phase"] = "exile"
        return state
    

    def night_action_node(state: GameState) -> GameState:
        game = state["game"]
        wolves = {"魏忠贤", "皇太极"}

        # 狼人刀（只活的狼行动）
        for wolf in wolves & set(game.alive):
            agent = RoleAgent(wolf, game, [wolf_knife_tool])
            result = agent.invoke({**state, "current_actor": wolf}, config={"configurable": {}})
            state["messages"].append(result)
            if "刀" in result.content:
                target = result.content.split("刀")[-1].strip()
                game.phase_mgr.wolf_knife.add(target)

        # 女巫（李自成）
        if "李自成" in game.alive:
            agent = RoleAgent("李自成", game, [witch_poison_tool])
            result = agent.invoke({**state, "current_actor": "李自成"}, config={"configurable": {}})
            if "毒" in result.content:
                target = result.content.split("毒")[-1].strip()
                game.phase_mgr.witch_poison.add(target)

        state["phase"] = "day_discuss"
        return state
        

    def exile_node(state: GameState) -> GameState:
        game = state["game"]

        # 1. 执行放逐
        exile_msg = game.perform_exile()
        state["messages"].append(AIMessage(content=exile_msg))

        # 2. 胜负判定
        victory = check_victory(game)
        if victory:
            state["phase"] = "end"
            state["messages"].append(AIMessage(content=f"【游戏结束】{victory}"))
        else:
            # 3. 进入夜晚行动（不要处理死亡！）
            state["phase"] = "night_action"

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
        if state["phase"] == "speak":
            return "speak"
        if state["phase"] == "vote":
            return "vote"
        if state["phase"] == "night_action":
            return "night_action"
        if state["phase"] == "exile":
            return "exile"
        if state["phase"] == "end":
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