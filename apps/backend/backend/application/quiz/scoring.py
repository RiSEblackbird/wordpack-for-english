from __future__ import annotations

from ...models.quiz import Quiz, QuizAnswerInput, QuizQuestionResult


def score_quiz_attempt(
    quiz: Quiz,
    answers: list[QuizAnswerInput],
) -> tuple[int, int, list[QuizQuestionResult]]:
    answer_map = {answer.question_id: answer.selected_choice_id for answer in answers}
    questions = [question for section in quiz.sections for question in section.questions]
    results: list[QuizQuestionResult] = []
    score = 0
    for question in questions:
        selected = answer_map.get(question.id)
        is_correct = selected == question.correct_choice_id
        if is_correct:
            score += 1
        results.append(
            QuizQuestionResult(
                question_id=question.id,
                selected_choice_id=selected,
                correct_choice_id=question.correct_choice_id,
                is_correct=is_correct,
            )
        )
    return score, len(questions), results
