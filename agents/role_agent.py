from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from typing import List
from .prompts import ROLE_PROMPTS
import os

class RoleAgent(Runnable):
    def __init__(self, player_name: str, game_ref, tools: List):
        self.player_name = player_name
        self.game = game_ref
        self.role = game_ref.players[player_name].role
        self.team = game_ref.players[player_name].team
        
        self.llm = ChatOpenAI(
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=os.getenv("DASHSCOPE_API_KEY")
        ).bind_tools(tools)
        
        prompt = ROLE_PROMPTS.get(self.role.name, ROLE_PROMPTS["default"]).format(
            team=self.team, role=self.role.name
        )
        
        self.chain = (
            {"messages": lambda x: x["messages"] + [
                {"role": "system", "content": prompt},
                {"role": "user", "content": self._format_state(x)}
            ]}
            | self.llm
        )
        self.tool_node = ToolNode(tools)

    def _format_state(self, state):
        phase = state["phase"]
        alive = ', '.join(state["alive"])
        
        if phase == "speak":
            return f"""
第{self.game.day}天，白天发言。
存活：{alive}
请发言，分析局面，悍跳身份或推狼。
（使用speak_tool发言）
            """
        elif phase == "vote":
            return f"""
第{self.game.day}天，投票阶段。
存活：{alive}
请决定投谁，使用vote_tool(target)。
（好人投狼，狼人乱投或自保）
            """
        return f"第{self.game.day}天，{phase}阶段。"
    def invoke(self, input, config=None):
        messages = [
            {"role": "system", "content": f"你是{self.role.name}，阵营为{self.role.team}"},
            {"role": "user", "content": self._format_state(input)}
        ]

        response = self.llm.invoke(messages)

        if response.tool_calls:
            # 为每个 tool_call 添加 game_state
            for tool_call in response.tool_calls:
                tool_call["args"]["game_state"] = {
                    "game": self.game,
                    "current_speaker": self.player_name
                }
                if "current_voter" in input:
                    tool_call["args"]["game_state"]["current_voter"] = input["current_voter"]

            # ToolNode 执行（必须传 config）
            tool_result = self.tool_node.invoke(
                {"messages": [response]},
                config={"configurable": {}}  # 必须！
            )
            return tool_result["messages"][-1]

        return response
