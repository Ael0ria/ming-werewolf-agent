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
        self.role = game_ref.players[player_name].role
        self.role_name = player.role.name
        self.team = player.role.team
        self.description = player.role.description
        self.vid = game_ref.id_mapping[player_name]

        self.system_prompt = f"""
你正在玩《大明暗夜录》狼人杀游戏。
你的编号：{self.vid}
你的真实身份：{self.role.name}({self.team})
【重要规则】：
1. 不要在发言开口写"【发言】{self.vid}"等内容，直接说发言内容。
2. 不要说明自己的真实身份，当然也可以说自己的名字用真诚打动别人，或者说其他人的名字来混淆视听，或者什么名字都不说，也可以说自己是预言家等等，一切有自己决定！
3. 发言要像真实朝堂辩论，逻辑严密，混淆/推断视身份而定
4. 如果你是女巫，你会知道当天晚上谁被刀了，你可以选择用解药就此人或坐视不管，或者选择毒杀某人，每个回合只能做一次决定。
5. 狼人知道同伴，可以查看同伴的技能。
""" 
        if player_name == "杨涟":
            self.system_prompt += f"""
        【白天发言】
        - 你是预言家，昨晚查验了玩家X
        - 第一天发言不能预言，只能从第二天开始才可以
        - 必须跳身份：说“我是预言家，昨晚查了玩家X，是[好人/狼人]”
        - 不要只说查验结果，要结合正常的发言来说
        - 不能说“查验结果”，要像真人一样推理
        - 存活玩家：{', '.join(game_ref.id_mapping[n] for n in game_ref.alive)}
        """

        if self.team in ["阉党", "后金"]:  # 狼人知道同伴
            wolf_companions = [name for name, p in game_ref.players.items() 
                             if p.role.team in ["阉党", "后金"] and name != player_name]
            if wolf_companions:
                self.system_prompt += f"\n你的狼人同伴：{', '.join(wolf_companions)}"
        else:  # 好人匿名视角
            self.system_prompt += f"\n所有玩家都是匿名编号：{game_ref.id_mapping}"
            self.system_prompt += f"\n你的编号：{game_ref.id_mapping[player_name]}"
        

        # 技能提示
        if self.role.night_action:
            self.system_prompt += f"\n夜晚可行动：{self.role.description}"
        
        self.llm = ChatOpenAI(
            model="qwen-plus-latest",
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
