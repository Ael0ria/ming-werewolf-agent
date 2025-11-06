# agents/graph.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage, AIMessage
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
    voter_queue: List[str]
    current_voter: str

def create_game_graph():
    graph = StateGraph(GameState)
    


    # ====== 修复：judge_node 必须初始化 current_speaker ======
    def judge_node(state: GameState) -> GameState:
        game = state["game"]
        phase_mgr = game.phase_mgr
        current_phase = phase_mgr.sequence[phase_mgr.current]

        phase_mgr.next_phase(game)

        if current_phase == "day_discuss":
            state["alive"] = list(game.alive)
            state["speaker_queue"] = list(game.alive)
            state["current_speaker"] = state["speaker_queue"][0]
            state["phase"] = "speak"
        elif current_phase == "vote":
            state["voter_queue"] = list(game.alive)
            state["current_voter"] = state["voter_queue"][0]
            state["phase"] = "vote"
        elif current_phase == "exile":
            game.perform_exile()
            game.process_night()
            result = game.check_end()
            if result:
                state["phase"] = "end"
                state["messages"].append(AIMessage(content=result))
            else:
                state["phase"] = "day_discuss"

        elif current_phase == "night":
            state["phase"] = "night"

        # # 自动推进阶段
        # next_phase = phase_mgr.next_phase(state["game"])
        # state["game"].phase_mgr = phase_mgr  # 同步回去

        return state

    # ====== speak_node 保持不变 ======
    def speak_node(state: GameState) -> GameState:
        game = state["game"]
        speaker = state["current_speaker"]
        role_name = game.players[speaker].role.name
    
        tools = [speak_tool]
        if role_name == "杨涟":
            tools += [seer_check_tool]
        elif role_name == "魏忠贤":
            tools += [wei_tamper_tool]

        agent = RoleAgent(speaker, game, tools)
        result = agent.invoke(state, config={"configurable": {}})
        state["messages"].append(result)
        
        state["speaker_queue"].pop(0)
        if state["speaker_queue"]:
            state["current_speaker"] = state["speaker_queue"][0]
        else:
            state["phase"] = "vote"
        return state

    def vote_node(state: GameState) -> GameState:
        game = state["game"]
        voter = state["current_voter"]

        tools = [vote_tool]
        agent = RoleAgent(voter, game, tools)
        result = agent.invoke(state, config={"configurable": {}})
        state["messages"].append(result)

        state["voter_queue"].pop(0)
        if state["voter_queue"]:
            state["current_voter"] = state["voter_queue"][0]
        else:
            state["phase"] ="exile"
        return state

    # ====== 注册节点 ======
    graph.add_node("judge", judge_node)
    graph.add_node("speak", speak_node)
    graph.add_node("vote", vote_node)

    graph.set_entry_point("judge")

    # 条件跳转
    def route(state: GameState):
        if state["phase"] == "speak":
            return "speak"
        if state["phase"] == "vote":
            return "vote"
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
            "end": END
        })
    graph.add_edge("speak", "judge")
    graph.add_edge("vote", "judge")

    return graph.compile()