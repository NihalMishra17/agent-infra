"""
CLI — submit a goal and tail results in real time.

Usage:
    python cli.py "Find the top 5 ML papers from last month and summarize them"
"""
from __future__ import annotations

import json
import sys
import threading
import time

from dotenv import load_dotenv
from loguru import logger

from config.topics import Topic
from core.kafka import KafkaConsumerLoop, KafkaPublisher, ensure_topics
from core.models import Goal, TaskResult

load_dotenv()

GOAL_TOPIC = "goals.submitted"


def submit_and_watch(goal_text: str) -> None:
    ensure_topics([GOAL_TOPIC, Topic.TASKS_COMPLETED, Topic.TASKS_APPROVED])

    publisher = KafkaPublisher()
    goal = Goal(description=goal_text)

    results: list[TaskResult] = []

    def handle_result(payload: dict) -> None:
        result = TaskResult(**payload)
        if result.goal_id == goal.goal_id:
            results.append(result)
            print(f"\n{'─'*60}")
            print(f"Task completed: {result.task_id[:8]}...")
            print(f"{result.output}")
            print(f"{'─'*60}")

    consumer_loop = KafkaConsumerLoop(
        group_id=f"cli-{goal.goal_id[:8]}",
        topics=[Topic.TASKS_COMPLETED],
        handler=handle_result,
    )

    # start consumer in background
    t = threading.Thread(target=consumer_loop.run, daemon=True)
    t.start()

    # publish goal
    publisher.publish(GOAL_TOPIC, goal, key=goal.goal_id)
    print(f"\nGoal submitted: {goal.goal_id}")
    print(f"Description: {goal_text}\n")
    print("Waiting for results (Ctrl+C to stop)...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        consumer_loop.stop()
        publisher.flush()
        print(f"\n\nTotal tasks completed: {len(results)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli.py \"<goal description>\"")
        sys.exit(1)
    submit_and_watch(" ".join(sys.argv[1:]))
