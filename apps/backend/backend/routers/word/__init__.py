from __future__ import annotations

from fastapi import APIRouter

from ...application.wordpack.regenerate_jobs import (
    RegenerateJob,
    _regenerate_jobs,
    _regenerate_lock,
)
from . import (
    example_routes,
    generation_routes,
    guest_public_routes,
    lemma_routes,
    lookup_routes,
    pack_routes,
    regeneration_routes,
    study_progress_routes,
)
from .dependencies import (
    generate_word_pack_id,
    require_authenticated_user as _require_authenticated_user,
    run_wordpack_flow,
    store,
)
from .example_routes import (
    bulk_delete_examples,
    delete_example_from_word_pack,
    generate_examples_for_word_pack,
    list_examples,
    update_example_transcription_typing,
)
from .generation_routes import generate_word_pack
from .guest_public_routes import update_word_pack_guest_public
from .lemma_routes import lookup_by_lemma
from .lookup_routes import lookup_word
from .pack_routes import create_empty_word_pack, delete_word_pack, get_word_pack, list_word_packs
from .regeneration_routes import (
    enqueue_regenerate_word_pack,
    get_regenerate_job_status,
    regenerate_word_pack,
)
from .schemas import ExamplesGenerateRequest, LemmaLookupResponse
from .study_progress_routes import (
    update_example_study_progress,
    update_word_pack_study_progress,
)

router = APIRouter(tags=["word"])
router.include_router(lookup_routes.router)
router.include_router(pack_routes.router)
router.include_router(generation_routes.router)
router.include_router(regeneration_routes.router)
router.include_router(guest_public_routes.router)
router.include_router(study_progress_routes.router)
router.include_router(example_routes.router)
router.include_router(lemma_routes.router)

__all__ = [
    "ExamplesGenerateRequest",
    "LemmaLookupResponse",
    "RegenerateJob",
    "_regenerate_jobs",
    "_regenerate_lock",
    "_require_authenticated_user",
    "bulk_delete_examples",
    "create_empty_word_pack",
    "delete_example_from_word_pack",
    "delete_word_pack",
    "enqueue_regenerate_word_pack",
    "generate_examples_for_word_pack",
    "generate_word_pack",
    "generate_word_pack_id",
    "get_regenerate_job_status",
    "get_word_pack",
    "list_examples",
    "list_word_packs",
    "lookup_by_lemma",
    "lookup_word",
    "regenerate_word_pack",
    "router",
    "run_wordpack_flow",
    "store",
    "update_example_study_progress",
    "update_example_transcription_typing",
    "update_word_pack_guest_public",
    "update_word_pack_study_progress",
]
