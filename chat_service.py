import asyncio
import json
import traceback
import uuid
from zep_python.client import AsyncZep
from zep_python.types import Message
from openai import AsyncOpenAI

API_KEY = ""
BASE_URL1 = "http://127.0.0.1:8000"
BASE_URL2 = "https://0d19-240d-1a-544-8100-1f87-2e2a-6dd2-993.ngrok-free.app"
BASE_URL3 = "http://192.168.1.46:8000"
session_id = "5ed4560a0f3a4c95a974e3e0f624695b"

class AIAssistant():
    def __init__(self):
        self.messages = [{"role": "system", "content": system_content}]
        self.client = AsyncZep(api_key=API_KEY, base_url=BASE_URL3,)
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
    if message is None or message == "":
        print("Message is empty.")
        return

    try:
        json_data = json.dumps({"role": role, "text": message}, ensure_ascii=False)
        print(f"Sending message: {json_data}")
        await websocket.send_text(json_data)  # send_text メソッドを使用
        print(f"Send complete.")
    except Exception as e:
        print(f"Error sending message: {e}")
        raise  # 呼び出し元で処理できるようにエラーを再発生

async def streaming(websocket, system_content=system_content):
    try:
        user_id = "koichi"
        ai = AIAssistant()
        messages = [
            {"role": "system", "content": system_content}
        ]

        # 初期化メッセージをクライアントに送信
        await websocket.send_text(json.dumps(
            {"role": "assistant", "text": "こんにちは！何かお手伝いできることはありますか？"},
            ensure_ascii=False
        ))

        while True:
            try:
                # WebSocketでメッセージ受け取り待機
                print("Waiting for user message...")
                user_message = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                print(f"Received user message: {user_message}")

                # メッセージのパース
                try:
                    message_data = json.loads(user_message)
                    message_text = message_data.get("content", "")
                    if not message_text or message_text.strip() == "":
                        continue
                except json.JSONDecodeError:
                    # JSONでない場合はそのまま使用
                    message_text = user_message

                # 処理中のメッセージを送信（オプション）
                await websocket.send_text(json.dumps(
                    {"role": "assistant", "text": "回答を生成中です・・・"},
                    ensure_ascii=False
                ))

                # AIに質問して回答を取得
                messages.append({"role": "user", "content": message_text})
                answer = await ai.ask_question(message_text, session_id=session_id)
                messages.append({"role": "assistant", "content": answer})

                # 回答をクライアントに送信
                await websocket.send_text(json.dumps(
                    {"role": "assistant", "text": answer},
                    ensure_ascii=False
                ))

            except asyncio.TimeoutError:
                print("No message received within 60 seconds.")
                # タイムアウト通知（オプション）
                await websocket.send_text(json.dumps(
                    {"role": "system", "text": "長時間通信がありませんでした。何かご質問はありますか？"},
                    ensure_ascii=False
                ))
            except Exception as e:
                print(f"Error processing message: {e}")
                await websocket.send_text(json.dumps(
                    {"role": "system", "text": "エラーが発生しました。もう一度お試しください。"},
                    ensure_ascii=False
                ))
                # 深刻なエラーの場合はループを抜ける
                if isinstance(e, (ConnectionError, RuntimeError)):
                    break

    except Exception as e:
        print(f"Streaming function error: {e}")
        traceback.print_exc()
    finally:
        # 必ず接続を閉じる処理を行う
        try:
            await websocket.close()
        except:
            pass

