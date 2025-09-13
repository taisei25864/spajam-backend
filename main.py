import asyncio
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import uuid

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # すべてのHTTPメソッドを許可
    allow_headers=["*"], # すべてのHTTPヘッダーを許可
)

class ConnectionManager:
    """WebSocket接続を管理するクラス"""
    def __init__(self):
        # { "room_id": [WebSocket接続, WebSocket接続, ...] }
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        """新しい接続を受け入れ、ルームに追加する"""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        """接続が切れたクライアントをルームから削除する"""
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            # ルームが空になったら辞書から削除
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: dict, room_id: str):
        """ルーム内の全クライアントにメッセージを送信する"""
        if room_id in self.active_connections:
            message_str = json.dumps(message)
            for connection in self.active_connections[room_id]:
                await connection.send_text(message_str)

# アプリケーション全体で共有するConnectionManagerのインスタンス
manager = ConnectionManager()


@app.post("/create_room")
async def create_room():
    """
    新しいルームを作成し、そのIDを返すHTTPエンドポイント。
    Flutterアプリから最初に呼び出されることを想定。
    """
    room_id = str(uuid.uuid4())[:6] # 6桁のランダムなID
    return {"room_id": room_id}


@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    """
    WebSocket通信を行うメインのエンドポイント。
    ルームへの参加、ゲーム開始通知、シグナリングメッセージの中継を行う。
    """
    # 1. クライアントを接続させ、ルームに追加
    await manager.connect(websocket, room_id)

    # 参加情報をルームの全員に通知
    join_message = {"event": "player_joined", "user_id": user_id}
    await manager.broadcast(join_message, room_id)

    try:
        # 2. 人数チェックとゲーム開始通知
        room_size = len(manager.active_connections.get(room_id, []))
        # ここでは3人ではなく、2人集まったら開始するシンプルな例
        if room_size == 3:
            start_message = {
                "event": "game_start",
                "message": f"{room_size}人集まりました。ゲームを開始します。"
            }
            await manager.broadcast(start_message, room_id)

        # 3. クライアントからのメッセージを待ち受け、中継するループ
        while True:
            # クライアントからメッセージ(SDPやICE Candidateなど)を受信
            data = await websocket.receive_text()
            
            # 受信したメッセージをそのままルーム内の他の全員に転送（シグナリングの中継）
            # 本番環境では、誰からのメッセージか分かるようにuser_idなどを付与する
            relay_message = json.loads(data)
            await manager.broadcast(relay_message, room_id)

    except WebSocketDisconnect:
        # 4. 接続が切れた場合の後処理
        manager.disconnect(websocket, room_id)
        # 誰かが退出したことをルームの全員に通知
        leave_message = {"event": "player_left", "user_id": user_id}
        await manager.broadcast(leave_message, room_id)
        print(f"User {user_id} left room {room_id}")