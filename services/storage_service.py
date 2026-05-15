"""
存储服务 - 管理运行状态和历史
"""
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass
class Run:
    """运行记录"""
    run_id: str
    message: str
    status: RunStatus
    created_at: str
    completed_at: Optional[str] = None
    events: List[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.events is None:
            self.events = []
        if isinstance(self.status, str):
            self.status = RunStatus(self.status)


class StorageService:
    """
    内存存储服务
    用于管理运行状态和历史
    """

    def __init__(self):
        self._runs: Dict[str, Run] = {}
        self._event_queues: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def create_run(self, message: str) -> str:
        """创建新的运行"""
        run_id = str(uuid.uuid4())
        run = Run(
            run_id=run_id,
            message=message,
            status=RunStatus.PENDING,
            created_at=datetime.now().isoformat(),
        )
        async with self._lock:
            self._runs[run_id] = run
            self._event_queues[run_id] = asyncio.Queue()

        return run_id

    async def update_status(self, run_id: str, status: RunStatus):
        """更新运行状态"""
        async with self._lock:
            if run_id in self._runs:
                self._runs[run_id].status = status
                if status in (RunStatus.COMPLETED, RunStatus.ABORTED, RunStatus.ERROR):
                    self._runs[run_id].completed_at = datetime.now().isoformat()

    async def add_event(self, run_id: str, event: Dict[str, Any]):
        """添加事件"""
        async with self._lock:
            if run_id in self._runs:
                self._runs[run_id].events.append(event)

            # 同时放入队列供 SSE 消费
            if run_id in self._event_queues:
                await self._event_queues[run_id].put(event)

    async def get_run(self, run_id: str) -> Optional[Run]:
        """获取运行"""
        return self._runs.get(run_id)

    async def get_run_events(self, run_id: str) -> List[Dict[str, Any]]:
        """获取运行的所有事件"""
        run = self._runs.get(run_id)
        if run:
            return run.events
        return []

    async def list_runs(self, limit: int = 20) -> List[Run]:
        """列出最近的运行"""
        runs = sorted(
            self._runs.values(),
            key=lambda r: r.created_at,
            reverse=True
        )
        return runs[:limit]

    async def delete_run(self, run_id: str):
        """删除运行"""
        async with self._lock:
            if run_id in self._runs:
                del self._runs[run_id]
            if run_id in self._event_queues:
                del self._event_queues[run_id]

    async def stream_events(self, run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """流式获取事件 (用于 SSE)"""
        if run_id not in self._event_queues:
            return

        queue = self._event_queues[run_id]

        # 先发送已有的事件
        run = self._runs.get(run_id)
        if run:
            for event in run.events:
                yield event

        # 然后等待新事件
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event

                # 如果是结束事件，退出
                if event.get("type") in ("done", "error", "aborted"):
                    break
            except asyncio.TimeoutError:
                # 发送心跳
                yield {"type": "heartbeat", "data": {"time": datetime.now().isoformat()}}
            except asyncio.CancelledError:
                break

    async def set_result(self, run_id: str, result: Dict[str, Any]):
        """设置运行结果"""
        async with self._lock:
            if run_id in self._runs:
                self._runs[run_id].result = result


# 全局实例
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """获取存储服务实例"""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
