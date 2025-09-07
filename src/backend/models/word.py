from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class WordPackRequest(BaseModel):
    """Request model for generating a word pack (MVP)."""

    lemma: str
    pos: Optional[str] = None


class Sense(BaseModel):
    id: str
    gloss_ja: str
    patterns: List[str] = []
    register: Optional[str] = None


class CollocationLists(BaseModel):
    verb_object: List[str] = []
    adj_noun: List[str] = []
    prep_noun: List[str] = []


class Collocations(BaseModel):
    general: CollocationLists = Field(default_factory=CollocationLists)
    academic: CollocationLists = Field(default_factory=CollocationLists)


class ContrastItem(BaseModel):
    with_: str = Field(alias="with")
    diff_ja: str

    class Config:
        allow_population_by_field_name = True


class Examples(BaseModel):
    A1: List[str] = []
    B1: List[str] = []
    C1: List[str] = []
    tech: List[str] = []


class Etymology(BaseModel):
    note: str
    confidence: str = "low"


class Pronunciation(BaseModel):
    ipa_GA: Optional[str] = None
    ipa_RP: Optional[str] = None
    syllables: Optional[int] = None
    stress_index: Optional[int] = None
    linking_notes: List[str] = []


class WordPack(BaseModel):
    lemma: str
    pronunciation: Pronunciation
    senses: List[Sense] = []
    collocations: Collocations = Field(default_factory=Collocations)
    contrast: List[ContrastItem] = []
    examples: Examples = Field(default_factory=Examples)
    etymology: Etymology
    study_card: str


class WordLookupResponse(BaseModel):
    """Response model for word lookup (placeholder)."""

    definition: Optional[str] = None
    examples: List[str] = []
