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
        game = state["game"]
        return f"""
【当前局面】
第{game.day}天，阶段：{state['phase']}
存活：{', '.join(state['alive'])}
昨夜：{'平安' if not game.phase_mgr.to_die else '有死者'}
---
【历史发言】
{chr(10).join(game.history[-5:])}
---
请决定你的行动或发言。
"""

    def invoke(self, input, config=None):
        response = self.chain.invoke(input)
        if response.tool_calls:
            tool_input = {"game_state": input, "current_speaker": self.player_name}
            if "current_actor" in input:
                tool_input["current_actor"] = self.player_name
            tool_result = self.tool_node.invoke({"messages": [response]}, {"tool_input": tool_input})
            return tool_result
        return response
    

