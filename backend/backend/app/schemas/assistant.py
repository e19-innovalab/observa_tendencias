from pydantic import BaseModel, Field


class AssistantTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AssistantContext(BaseModel):
    """What the user is looking at; every field optional."""
    page: str | None = None
    country: str | None = None
    occupation: str | None = None
    sector: str | None = None


class AssistantChoice(BaseModel):
    """An option the person picked from a previous answer (it repeats the question with it)."""
    occupation: str | None = None
    country: str | None = None


class AskRequest(BaseModel):
    question: str
    context: AssistantContext | None = None
    history: list[AssistantTurn] = []
    choice: AssistantChoice | None = None


class AnswerLink(BaseModel):
    label: str
    href: str


class AnswerOption(BaseModel):
    """A button: send the same question again with choice = {occupation, country}."""
    label: str
    occupation: str | None = None
    country: str | None = None


class ToolCallItem(BaseModel):
    tool: str
    args: dict
    ok: bool


class AskResponse(BaseModel):
    answer: str
    status: str  # ok | unverified | blocked | refused
    verified: bool
    warning: str | None = None
    unverified_numbers: list[str] = []
    links: list[AnswerLink] = []
    options: list[AnswerOption] = []
    tool_calls: list[ToolCallItem] = []
    source: str  # script (template with the data) | model
    provider: str
    model: str
    log_id: int
    remaining_today: int


class AssistantStatus(BaseModel):
    enabled: bool
    provider: str
    model: str
    questions_per_day: int
    remaining_today: int | None = None  # None when not logged in
    max_question_chars: int
    history_turns: int
    texts: dict[str, str]
    examples: list[str] = []
