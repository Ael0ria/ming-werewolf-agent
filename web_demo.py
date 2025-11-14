import gradio as gr
import threading
import builtins


from agents.graph import create_game_graph, input_queue, output_queue  
from game_engine import MingWerewolfGame

ROLE_DISPLAY = {
    "杨涟": "1. 杨涟", "魏忠贤": "2. 魏忠贤", "皇太极": "3. 皇太极", "孙承宗": "4. 孙承宗",
    "袁崇焕": "5. 袁崇焕", "钱谦益": "6. 钱谦益", "史可法": "7. 史可法", "吴伟业": "8. 吴伟业",
    "郑森": "9. 郑森", "卢象升": "10. 卢象升", "李自成": "11. 李自成"
}
DISPLAY_TO_REAL = {v: k for k, v in ROLE_DISPLAY.items()}
ROLE_CHOICES = list(ROLE_DISPLAY.values())



current_logs = []
player_name = None
game = None
game_thread = None


original_print = builtins.print
def web_print(*args, sep=' ', end='\n'):
    text = sep.join(map(str, args)) + end
    clean = text.strip()
    if clean:
        output_queue.put(("log", clean))
    original_print(*args, sep=sep, end=end)
builtins.print = web_print


def run_game():
    global game, player_name
    initial_state = {
        "game": game,
        "messages": [],
        "phase": "judge",
        "day": 0,
        "speaker_queue": [],
        "voter_queue": [],
        "votes": {},
        "current_speaker": None,
        "current_voter": None
    }
    app = create_game_graph()
    config = {"configurable": {}, "recursion_limit": 10000}
    for output in app.stream(initial_state, config):
        pass  


def submit_speak(text):
    if text.strip():
        current_logs.append({"role": "user", "content": f"你：{text.strip()}"})
        input_queue.put(text.strip()) 
    return gr.update(value="")

def submit_vote(choice):
    if choice:
        current_logs.append({"role": "user", "content": f"你投给：{choice}"})
        input_queue.put(choice)
    return gr.update(value="")


def poll():
    while not output_queue.empty():
        typ, msg = output_queue.get()
        if typ == "log":
            current_logs.append({"role": "assistant", "content": msg})
            return current_logs, gr.update(), gr.update(), gr.update()
    return current_logs, gr.update(), gr.update(), gr.update()


def start_game(choice):
    global game, game_thread, current_logs, player_name
    player_name = DISPLAY_TO_REAL[choice]
    game = MingWerewolfGame(player_role=player_name)
    current_logs = [{"role": "assistant", "content": 
                    f"游戏开始！你的身份：{game.players[player_name].role.name}（{game.players[player_name].role.team}）\n请稍等，第1天即将开始..."}]
    game_thread = threading.Thread(target=run_game, daemon=True)
    game_thread.start()
    return current_logs, gr.update(), gr.update(), gr.update(interactive=False)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 《大明暗夜录》\n明朝·AI狼人杀 网页版")
    with gr.Row():
        role_dd = gr.Dropdown(ROLE_CHOICES, label="选择你的席位", value="1. 杨涟")
        start_btn = gr.Button("开始游戏", variant="primary")

    chat = gr.Chatbot(height=620, type="messages")
    speak_box = gr.Textbox(label="你的发言", placeholder="等待轮到你发言...", visible=False, interactive=True)
    vote_dd = gr.Dropdown(label="投票放逐", choices=[], visible=False, allow_custom_value=True)

   
    def show_speak_box():
        return gr.update(visible=True), gr.update(visible=False)
    def show_vote_box(choices):
        return gr.update(visible=False), gr.update(visible=True, choices=choices)

    
    def poll_with_ui():
        while not output_queue.empty():
            typ, msg = output_queue.get()
            if typ == "log":
                current_logs.append({"role": "assistant", "content": msg})
               
                if "轮到你发言" in msg:
                    return current_logs, *show_speak_box(), gr.update()
                if "轮到你投票" in msg:
                   
                    import re
                    players = re.findall(r"玩家\d+", msg)
                    return current_logs, gr.update(visible=False), gr.update(visible=True, choices=players), gr.update()
        return current_logs, gr.update(), gr.update(), gr.update()

    start_btn.click(start_game, role_dd, [chat, speak_box, vote_dd, start_btn])
    speak_box.submit(submit_speak, speak_box, speak_box)
    vote_dd.change(submit_vote, vote_dd, vote_dd)

    timer = gr.Timer(0.5)
    timer.tick(poll_with_ui, None, [chat, speak_box, vote_dd, start_btn])

demo.launch(server_name="127.0.0.1", server_port=7860)