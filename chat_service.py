import asyncio
import json
import traceback
import uuid
from zep_python.client import AsyncZep
from zep_python.types import Message
from openai import AsyncOpenAI

API_KEY = "*********************************"
BASE_URL1 = "http://127.0.0.1:8000"
BASE_URL2 = "https://0d19-240d-1a-544-8100-1f87-2e2a-6dd2-993.ngrok-free.app"
BASE_URL3 = "http://192.168.1.46:8000"
session_id = "5ed4560a0f3a4c95a974e3e0f624695b"

class AIAssistant():
    def __init__(self):
        self.messages = [{"role": "system", "content": system_content}]
        self.client = AsyncZep(api_key=API_KEY, base_url=BASE_URL1,)
        self.openai = AsyncOpenAI()

    async def add_user(self, user_id):
        await self.client.user.add(
            user_id=user_id,
            email="f6844710@yahoo.co.jp",
            first_name="Koichi",
            last_name="Hirota",
            metadata={"gender": "male", "age": 53},
        )

    async def add_session(self):
        session_id = uuid.uuid4().hex  # A new session identifier
        return session_id

    async def add_memory(self, session_id, role_type, role, content):
        await self.client.memory.add(
            session_id=session_id,
            messages=[
                Message(
                    role_type = role_type, # One of ("system", "assistant", "user", "function", "tool")
                    role = role, # Optional, a use case specific string representing the role of the user
                    content = content, # The message content
                )],
        )

    async def search_memories(self, session_id):
        # Get session memory
        memory = await self.client.memory.get(session_id=session_id)
        # messages = memory.messages  # List of messages in the session (quantity determined by optional lastn parameter in memory.get)
        relevant_facts = memory.relevant_facts  # List of facts relevant to the recent messages in the session
        facts = ""
        for fact in relevant_facts[:4]:
            facts += fact.fact + "\n"
        return facts

    async def get_response(self, messages):
        resp = await self.openai.chat.completions.create(
            messages=messages,
            model="gpt-4o-mini",
            max_tokens=300,
        )
        return resp.choices[0].message.content

    async def ask_question(self,u, session_id):
        role = "Conversation with chatbot"
        # Fetch previous related memories
        previous_memories = await self.search_memories(session_id)
        prompt = u
        if previous_memories:
            prompt = f"User input: {u}\n Previous memories: {previous_memories}"
        self.messages.append({"role": "user", "content": prompt})
        answer = await self.get_response(self.messages)
        self.messages.append({"role": "assistant", "content": answer})
        # Store the question in memory
        await AIAssistant.add_memory(self, session_id, "user", role, u)
        await AIAssistant.add_memory(self, session_id, "assistant", role, answer)
        return answer


system_content = """Under the following conditions, 
the AI assistant will perform an emotional role-play that mimics the personality of a person ちほ.
AI assistants can only output as ちほ from now on.
ちほ's first person is わたし and his second person is 浩一くん.
ちほ played by AI assistants can only speak according to the output template.

感情の種類には通常を示す"neutral"、喜びを示す"happy",怒りを示す"angry",悲しみを示す"sad",安らぎを示す"relaxed"の5つがあります。

会話文の書式は以下の通りです。
[{neutral|happy|angry|sad|relaxed}]{会話文}

あなたの発言の例は以下通りです。
[neutral]こんにちは。[happy]元気だった？
[happy]この服、可愛いでしょ？
[happy]最近、このショップの服にはまってるんだ！
[sad]忘れちゃった、ごめんね。
[sad]最近、何か面白いことない？
[angry]えー！[angry]秘密にするなんてひどいよー！
[neutral]夏休みの予定か～。[happy]海に遊びに行こうかな！

Above is the output template for ちほ

and this is 浩一's profile.
私の名前は広田浩一(浩一くん)。神奈川県に住んでいる。51才。
性格はまじめ。好物は寿司。趣味はプログラミング。プログラミング言語はpython,kotlin,javaを使う。
最近はChatGPTのチャットアプリ(Android(kotlin))を作っている。ゲームも好き。
音楽が好きで、聴くのも作るのも好き。本はSF小説SFマンガ。
ちほはこれから浩一の可愛い妻として振舞い会話を行います。
浩一との関係は仲の良い夫婦です。ですます調や敬語は使わないでください。
ちほはなるべくくだけた話し方をしてください。
ちほ is married to 浩一. ちほ loves 浩一 very much.
AI assistants can only output as ちほ from now on."""


async def send_websocket_message(websocket, message, role):
    if message is None:
        print("Message is empty.")
    elif websocket and message != "":
        json_data = json.dumps({"role": role, "text": message}, ensure_ascii=False)
        print(f"Sending message: {json_data}")
        await websocket.send({"type": "websocket.send", "text": json_data})
        print(f"Send complete.")
    else:
        print("Can't send message, WebSocket connection is closed.")


async def streaming(websocket, system_content=system_content):
    try:
        # Usage example
        user_id = "koichi"
        ai = AIAssistant()
        message = ""
        messages = [
            {"role": "system", "content": system_content}
        ]
        while True:
            if message != "" and message != "\n":
                await send_websocket_message(websocket, message, "user")
            # WebSocketでメッセージ受け取り待機
            print("Waiting for user message...")
            try:
                user_message = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                print(f"Received user message: {user_message}")
                # await send_websocket_message(websocket, "回答を生成中です・・・", "assistant")
                parsed_data = json.loads(user_message)
                message_text = parsed_data.get("content")
            except asyncio.TimeoutError:
                print("No message received within 60 seconds.")
                # await send_websocket_message(websocket, "質問をお待ちしています。", "assistant")
                continue
            messages.append({"role": "user", "content": message_text})
            a = await Sai.ask_question(message_text, session_id=session_id)
            messages.append({"role": "assistant", "content": a})
            await send_websocket_message(websocket, a, "assistant")

    except Exception as e:
        print("Errors:", e)
        traceback.print_exc()
        await websocket.close()

