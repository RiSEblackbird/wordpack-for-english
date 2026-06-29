from __future__ import annotations

import anyio

from ...application.quiz.generation_jobs import QuizGenerator
from ...flows.quiz_generate import QuizGenerateFlow
from ...models.quiz import Quiz, QuizGenerateRequest


class QuizGenerateFlowAdapter(QuizGenerator):
    async def generate(self, req: QuizGenerateRequest, store: object) -> Quiz:
        flow = QuizGenerateFlow(store=store)
        return await anyio.to_thread.run_sync(flow.run, req)
