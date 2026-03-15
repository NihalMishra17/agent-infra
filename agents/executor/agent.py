"""
Executor Agent
--------------
1. Consumes Task events from topics.TASKS_ASSIGNED
2. Searches episodic memory for relevant past results (avoids repeat work)
3. Uses DSPy ExecutorModule to complete the task
4. Publishes TaskResult to topics.TASKS_COMPLETED
5. Stores result in episodic memory
"""
from __future__ import annotations

import os
import signal
import sys

from dotenv import load_dotenv
from loguru import logger

from config.topics import ALL_TOPICS, Topic
from core.dspy_modules import ExecutorModule, configure_dspy
from core.kafka import KafkaConsumerLoop, KafkaPublisher, ensure_topics
from core.memory import MemoryClient
from core.models import Task, TaskResult

load_dotenv()


AGENT_ID = "executor"


class ExecutorAgent:
    def __init__(self) -> None:
        configure_dspy()
        self._publisher = KafkaPublisher()
        self._memory = MemoryClient()
        self._module = ExecutorModule()
        self._loop = KafkaConsumerLoop(
            group_id=os.getenv("EXECUTOR_CONSUMER_GROUP", "executor-group"),
            topics=[Topic.TASKS_ASSIGNED],
            handler=self._handle_task,
        )

    def _handle_task(self, payload: dict) -> None:
        task = Task(**payload)
        logger.info(f"Executor received task {task.task_id}: {task.description[:80]}")

        # check memory — has a similar task been done before?
        memories = self._memory.search(
            query=task.description,
            agent_id=AGENT_ID,
            limit=3,
        )
        past_context = "\n".join(m["content"] for m in memories) if memories else ""
        if past_context:
            logger.debug(f"Found {len(memories)} relevant memories for task {task.task_id}")

        # execute
        output = self._module(task_description=task.description, past_context=past_context)
        logger.info(f"Task {task.task_id} completed ({len(output)} chars)")

        # publish result
        result = TaskResult(
            task_id=task.task_id,
            goal_id=task.goal_id,
            output=output,
            metadata={"agent_id": AGENT_ID},
        )
        self._publisher.publish(Topic.TASKS_COMPLETED, result, key=task.goal_id)

        # store result in memory
        self._memory.store(
            agent_id=AGENT_ID,
            goal_id=task.goal_id,
            content=f"Task: {task.description}\nResult: {output}",
        )

    def run(self) -> None:
        logger.info("Executor agent started")
        self._loop.run()

    def stop(self) -> None:
        self._loop.stop()
        self._publisher.flush()
        self._memory.close()


def main() -> None:
    ensure_topics(ALL_TOPICS)
    agent = ExecutorAgent()

    def _shutdown(sig, frame):
        logger.info("Shutting down executor...")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    agent.run()


if __name__ == "__main__":
    main()
