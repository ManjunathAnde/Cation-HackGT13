from pathlib import Path as FilePath
from typing import Annotated, Literal, Union

from dotenv import load_dotenv
from fastapi import FastAPI, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app import core

# Load backend/.env (one level above this app/ package).
load_dotenv(FilePath(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="Cation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DoctorId = Annotated[str, Path(examples=["dr_patel"])]
Score = Union[int, float]

# Example values for Swagger, taken from the §12 demo path.
CARD_EXAMPLE = core.CARDS_BY_ID["label-ozempic-ckd"]
ION_EXAMPLE = {"pick": "kidney outcomes content", "why": "top score 3 from replies"}
SCORES_EXAMPLE = {
    "glycemic control": 1,
    "kidney outcomes": 3,
    "ozempic safety": 1,
    "cardio-kidney-metabolic care": 1,
}
PROFILE_EXAMPLE = {
    "id": "dr_patel",
    "name": "Dr. Patel",
    "specialty": "endocrinology",
    "conditions": ["type 2 diabetes", "chronic kidney disease"],
    "interests": ["ozempic safety"],
    "frequency": "weekly",
    "topics": {"glycemic control": 1, "kidney outcomes": 1, "ozempic safety": 1},
    "muted": [],
    "ion": {"pick": "General update for endocrinology", "why": "specialty only"},
}
CARD_MESSAGE_EXAMPLE = {"type": "card", "t": 1790000000.0, "card": CARD_EXAMPLE, "answer": "yes"}
OFFER_MESSAGE_EXAMPLE = {"type": "offer", "t": 1790000001.0, "topic": "cardio-kidney-metabolic care", "answer": None}
EVENT_EXAMPLE = {
    "t": 1790000000.0,
    "type": "reply",
    "doctor": "dr_patel",
    "card": "label-ozempic-ckd",
    "answer": "yes",
    "scores": {"glycemic control": 1, "kidney outcomes": 2, "ozempic safety": 2},
}


def examples(*values):
    return ConfigDict(json_schema_extra={"examples": list(values)})


# ---------- models ----------

class HealthResponse(BaseModel):
    model_config = examples({"ok": True})

    ok: bool


class Card(BaseModel):
    model_config = examples(CARD_EXAMPLE)

    id: str
    title: str
    summary: str
    source: str
    link: str
    topics: list[str]
    claims: list[str]
    kind: Literal["label", "study"]


class Ion(BaseModel):
    model_config = examples(ION_EXAMPLE)

    pick: str
    why: str


class OnboardRequest(BaseModel):
    model_config = examples({key: PROFILE_EXAMPLE[key] for key in
                             ("id", "name", "specialty", "conditions", "interests", "frequency")})

    id: str
    name: str
    specialty: str
    conditions: list[str]
    interests: list[str]
    frequency: Literal["daily", "weekly"]


class Profile(BaseModel):
    model_config = examples(PROFILE_EXAMPLE)

    id: str
    name: str
    specialty: str
    conditions: list[str]
    interests: list[str]
    frequency: Literal["daily", "weekly"]
    topics: dict[str, Score]
    muted: list[str]
    ion: Ion


class SendResponse(BaseModel):
    model_config = examples({"card": CARD_EXAMPLE}, {"card": None})

    card: Card | None


class CardMessage(BaseModel):
    model_config = examples(CARD_MESSAGE_EXAMPLE)

    type: Literal["card"]
    t: float
    card: Card
    answer: Literal["yes", "not_interested", "no_reply"] | None


class OfferMessage(BaseModel):
    model_config = examples(OFFER_MESSAGE_EXAMPLE)

    type: Literal["offer"]
    t: float
    topic: str
    answer: Literal["yes", "no"] | None


Message = Annotated[Union[CardMessage, OfferMessage], Field(discriminator="type")]


class InboxResponse(BaseModel):
    model_config = examples({
        "messages": [CARD_MESSAGE_EXAMPLE, OFFER_MESSAGE_EXAMPLE],
        "active": OFFER_MESSAGE_EXAMPLE,
    })

    messages: list[Message]
    active: Message | None


class ReplyRequest(BaseModel):
    model_config = examples({"doctor_id": "dr_patel", "card_id": "label-ozempic-ckd", "answer": "yes"})

    doctor_id: str
    card_id: str
    answer: Literal["yes", "not_interested", "no_reply"]


class ReplyResponse(BaseModel):
    model_config = examples({"offer": "cardio-kidney-metabolic care", "ion": ION_EXAMPLE})

    offer: str | None
    ion: Ion


class TopicReplyRequest(BaseModel):
    model_config = examples({"doctor_id": "dr_patel", "topic": "cardio-kidney-metabolic care", "answer": "yes"})

    doctor_id: str
    topic: str
    answer: Literal["yes", "no"]


class TopicReplyResponse(BaseModel):
    model_config = examples({"ion": ION_EXAMPLE})

    ion: Ion


class Event(BaseModel):
    """Every event has t, type, and doctor; the other fields depend on the type (blueprint §5.3)."""

    model_config = ConfigDict(extra="allow", json_schema_extra={"examples": [EVENT_EXAMPLE]})

    t: float
    type: str
    doctor: str


class Metrics(BaseModel):
    model_config = examples({
        "engagement_score": 72,
        "reply_rate": 1.0,
        "yes_rate": 0.67,
        "topics_added": 1,
        "muted": 0,
        "saved": 2,
        "scores": SCORES_EXAMPLE,
        "timeline": [EVENT_EXAMPLE],
    })

    engagement_score: int
    reply_rate: float
    yes_rate: float
    topics_added: int
    muted: int
    saved: int
    scores: dict[str, Score]
    timeline: list[Event]


# ---------- errors: one short plain-English message ----------

def error(status, message):
    return JSONResponse(status_code=status, content={"detail": message})


@app.exception_handler(core.NotFound)
def not_found(request: Request, exc: core.NotFound):
    return error(404, str(exc))


@app.exception_handler(core.BadRequest)
def bad_request(request: Request, exc: core.BadRequest):
    return error(400, str(exc))


@app.exception_handler(core.Invalid)
def invalid(request: Request, exc: core.Invalid):
    return error(422, str(exc))


@app.exception_handler(RequestValidationError)
def validation_failed(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if part not in ("body", "query", "path"))
    return error(422, f"{field}: {first['msg']}" if field else first["msg"])


# ---------- endpoints ----------

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True)


@app.post("/onboard", response_model=Profile, summary="Onboard a doctor (re-onboarding resets them)")
def onboard(body: OnboardRequest):
    return core.onboard(
        doctor_id=body.id,
        name=body.name,
        specialty=body.specialty,
        conditions=body.conditions,
        interests=body.interests,
        frequency=body.frequency,
    )


@app.post("/send/{doctor_id}", response_model=SendResponse, summary="Send the doctor's next card")
def send(doctor_id: DoctorId):
    return {"card": core.next_card(doctor_id)}


@app.get("/inbox/{doctor_id}", response_model=InboxResponse, summary="Get the doctor's message thread")
def inbox(doctor_id: DoctorId):
    return core.inbox(doctor_id)


@app.post("/reply", response_model=ReplyResponse, summary="Record the doctor's reply to their last card")
def reply(body: ReplyRequest):
    return core.reply(body.doctor_id, body.card_id, body.answer)


@app.post("/topic-reply", response_model=TopicReplyResponse, summary="Record the doctor's answer to a topic offer")
def topic_reply(body: TopicReplyRequest):
    return core.topic_reply(body.doctor_id, body.topic, body.answer)


@app.get("/vault/{doctor_id}", response_model=list[Card], summary="List the doctor's saved cards")
def vault(doctor_id: DoctorId, q: Annotated[str | None, Query(examples=["kidney"])] = None):
    return core.vault(doctor_id, q)


@app.get("/metrics/{doctor_id}", response_model=Metrics, summary="Get the doctor's engagement metrics")
def metrics(doctor_id: DoctorId):
    return core.metrics(doctor_id)


@app.get("/profile/{doctor_id}", response_model=Profile, summary="Get the doctor's public profile")
def profile(doctor_id: DoctorId):
    return core.profile(doctor_id)


@app.get("/events", response_model=list[Event], summary="List events newer than a timestamp")
def events(since: Annotated[float, Query(examples=[0])] = 0):
    return core.events(since)


# ---------- OpenAPI ----------

def openapi_with_null_examples():
    """FastAPI drops None values when building /openapi.json, including inside examples
    (so {"card": null} shows as {}). Put each model's own examples back unchanged."""
    if app.openapi_schema is None:
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for name, model_schema in schema["components"]["schemas"].items():
            model = globals().get(name)
            extra = getattr(model, "model_config", {}).get("json_schema_extra")
            if extra:
                model_schema["examples"] = extra["examples"]
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = openapi_with_null_examples
