# agents/graph.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage
from game_engine import MingWerewolfGame
from tools import *
from .role_agent import RoleAgent

class GameState(TypedDict):
    game: MingWerewolfGame
    phase: str
    messages: List[AnyMessage]
    alive: List[str]
    speaker_queue: List[str]
    current_speaker: str
    night_actors: List[str]

def create_game_graph():
    game = MingWerewolfGame()
    graph = StateGraph(GameState)
    
    # 初始化角色Agent
    agents = {}
    for name in game.players:
        tools = [speak_tool]
        role = game.players[name].role
        if role.name == "杨涟":
            tools.append(seer_check_tool)
        elif role.name == "魏忠贤":
            tools.append(wei_tamper_tool)
        agents[name] = RoleAgent(name, game, tools)

    # ====== 修复：judge_node 必须初始化 current_speaker ======
    def judge_node(state: GameState) -> GameState:
        phase_mgr = state["game"].phase_mgr
        current_phase = phase_mgr.sequence[phase_mgr.current]

        if current_phase == "night":
            state["night_actors"] = [
                p for p in state["alive"]
                if state["game"].players[p].role.night_action
            ]
            state["phase"] = "night_action"
        elif current_phase == "day_discuss":
            state["speaker_queue"] = state["alive"][:]
            state["current_speaker"] = state["speaker_queue"][0]  # 关键修复！
            state["phase"] = "speak"
        elif current_phase == "vote":
            state["phase"] = "vote"
        elif current_phase == "exile":
            state["phase"] = "exile"

        # 自动推进阶段
        next_phase = phase_mgr.next_phase(state["game"])
        state["game"].phase_mgr = phase_mgr  # 同步回去

        return state

    # ====== speak_node 保持不变 ======
    def speak_node(state: GameState) -> GameState:
        agent = agents[state["current_speaker"]]
        result = agent.invoke(state)
        state["messages"].append(result)

        state["speaker_queue"].pop(0)
        if not state["speaker_queue"]:
            state["phase"] = "vote"
        else:
            state["current_speaker"] = state["speaker_queue"][0]

        return state

    # ====== 注册节点 ======
    graph.add_node("judge", judge_node)
    graph.add_node("speak", speak_node)

    graph.set_entry_point("judge")

    # 条件跳转
    def route(state: GameState):
        if state["phase"] == "speak":
            return "speak"
        return END

    graph.add_conditional_edges("judge", lambda s: "speak" if s["phase"] == "speak" else END)
    graph.add_conditional_edges("speak", route)

    memory = MemorySaver()
    return graph.compile(), game, agents