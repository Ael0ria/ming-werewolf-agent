from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from typing import List, Dict
from langchain_core.messages import AnyMessage, AIMessage

import os

class RoleAgent:
    def __init__(self, player_name: str, game_ref, tools: List):
        self.player_name = player_name
        self.game = game_ref
        player = game_ref.players[player_name]
        self.role_name = player.role.name
        self.team = player.role.team
        self.description = player.role.description
        
        self.llm = ChatOpenAI(
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=os.getenv("DASHSCOPE_API_KEY")
        ).bind_tools(tools)
        
        # prompt = ROLE_PROMPTS.get(self.role.name, ROLE_PROMPTS["default"]).format(
        #     team=self.team, role=self.role.name
        # )
        
        # self.chain = (
        #     {"messages": lambda x: x["messages"] + [
        #         {"role": "system", "content": prompt},
        #         {"role": "user", "content": self._format_state(x)}
        #     ]}
        #     | self.llm
        # )
        self.system_prompt = f"""
        你现在是[{self.player_name}]，真实身份是[{self.role_name}]，阵营是[{self.team}]。
        你必须以第一人称发言，风格符合历史人物性格。
        禁止说“我是AI”或“我是模拟”。
        你正在第{self.game.day}天，存活玩家：{', '.join(self.game.alive)}
        """.strip()

        self.tool_node = ToolNode(tools)

    def _format_state(self, state: Dict) -> str:
        phase = state["phase"]
        alive = ', '.join(state.get("alive", []))
        if phase == "speak":
            return f"第{self.game.day}天，白天发言。存活：{alive}\n请发言或使用工具。"
        elif phase == "vote":
            return f"第{self.game.day}天，投票阶段。存活：{alive}\n请使用vote_tool投票。"
        return "请行动。"
    def invoke(self, input, config=None) -> AIMessage:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_state(input)}
        ]

        response = self.llm.invoke(messages)

        if response.tool_calls:
            # 为每个 tool_call 添加 game_state
            for tool_call in response.tool_calls:
                tool_call["args"]["game_state"] = {
                    "game": self.game,
                    "current_speaker": self.player_name,
                    "current_voter": input.get("current_voter"),
                    "current_actor": input.get("current_actor")
                }


            tool_result = self.tool_node.invoke(
                {"messages": [response]},
                config={"configurable": {}} 
            )
            tool_msg = tool_result["messages"][-1]
            return AIMessage(content=tool_msg.content)

        return response
