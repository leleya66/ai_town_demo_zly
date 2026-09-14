"""定义请求、NPC 决策和行动结果的数据契约，校验字段类型及非法输入。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

NpcId = Literal['joe', 'wise', 'calm', 'stead']
PlaceId = Literal['forest', 'library', 'plaza', 'workshop']
Activity = Literal['seek_company', 'rest', 'read', 'chat', 'work', 'repair_bench', 'sit_bench', 'prepare_talk', 'host_talk', 'attend_talk', 'invite_event', 'run_event', 'join_event']



class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=0, strict=True)


class Suggestion(Command):
    type: Literal['suggest_activity']
    npc_id: NpcId
    activity: Activity
    target_place_id: PlaceId


class AiMode(Command):
    enabled: bool = Field(strict=True)


class Support(Command):
    npc_id: NpcId


class NpcDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    npc_id: NpcId
    activity: Activity
    target_place_id: PlaceId
    target_npc_id: NpcId | None = None
    reason: str = Field(min_length=1)
    source: Literal['rules', 'ai'] = 'rules'
    thought: str = ''
    fallback_reason: str = ''
    related_memory_ids: list[str] = Field(default_factory=list)
    source_action_id: str | None = None
    agenda_item_id: str | None = None


class ActionResult(BaseModel):
    npc_id: NpcId
    agenda_item_id: str | None = None
    activity: Activity
    from_place_id: PlaceId
    to_place_id: PlaceId
    status: Literal['completed']
    effects: dict[Literal['energy', 'mood', 'social'], int]
    event_id: str | None
    notes: list[str] = Field(default_factory=list)


class LegacyCommand(Command):
    type: Literal['message', 'observe', 'interact', 'save', 'load', 'reset', 'save_restart']
    npc_id: NpcId | None = None
    place_id: PlaceId | None = None
    text: str = Field(default='', max_length=240)
    save_id: str | None = Field(default=None, max_length=100)
