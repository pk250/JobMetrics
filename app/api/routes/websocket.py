from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.db.crud import execution_log_crud
import json

router = APIRouter(prefix="/api/ws", tags=["websocket"])

# 存储活跃的WebSocket连接
class ConnectionManager:
    def __init__(self):
        # 所有活跃连接
        self.active_connections: List[WebSocket] = []
        # 按日志ID分组的连接
        self.log_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, log_id: int = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if log_id:
            if log_id not in self.log_connections:
                self.log_connections[log_id] = []
            self.log_connections[log_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, log_id: int = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if log_id and log_id in self.log_connections:
            if websocket in self.log_connections[log_id]:
                self.log_connections[log_id].remove(websocket)
            if not self.log_connections[log_id]:
                del self.log_connections[log_id]
    
    async def send_log_update(self, log_id: int, message: dict):
        if log_id in self.log_connections:
            for connection in self.log_connections[log_id]:
                await connection.send_text(json.dumps(message))

# 创建连接管理器实例
manager = ConnectionManager()

@router.websocket("/logs/{log_id}")
async def websocket_log_endpoint(websocket: WebSocket, log_id: int, db: Session = Depends(get_db)):
    """WebSocket端点，用于实时获取执行日志更新"""
    await manager.connect(websocket, log_id)
    try:
        # 发送初始日志数据
        log = execution_log_crud.get(db, log_id)
        if log:
            await websocket.send_text(json.dumps({
                "type": "initial",
                "data": {
                    "id": log.id,
                    "spider_id": log.spider_id,
                    "start_time": log.start_time.isoformat() if log.start_time else None,
                    "end_time": log.end_time.isoformat() if log.end_time else None,
                    "status": log.status,
                    "log_content": log.log_content,
                    "error_message": log.error_message
                }
            }))
        
        # 等待客户端消息
        while True:
            data = await websocket.receive_text()
            # 客户端可以发送ping来保持连接
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, log_id)

# 用于其他模块调用，发送日志更新
async def send_log_update(log_id: int, log_data: dict):
    """发送日志更新到所有订阅该日志的WebSocket连接"""
    await manager.send_log_update(log_id, {
        "type": "update",
        "data": log_data
    })