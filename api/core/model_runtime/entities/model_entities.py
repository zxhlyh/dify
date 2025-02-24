from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from core.model_runtime.entities.common_entities import I18nObject


class ModelType(Enum):
    """
    Enum class for model type.
    """
    LLM = "llm"
    TEXT_EMBEDDING = "text-embedding"
    RERANK = "rerank"
    SPEECH2TEXT = "speech2text"
    MODERATION = "moderation"
    # TTS = "tts"
    # TEXT2IMG = "text2img"

    @classmethod
    def value_of(cls, origin_model_type: str) -> "ModelType":
        """
        Get model type from origin model type.

        :return: model type
        """
        if origin_model_type == 'text-generation' or origin_model_type == cls.LLM.value:
            return cls.LLM
        elif origin_model_type == 'embeddings' or origin_model_type == cls.TEXT_EMBEDDING.value:
            return cls.TEXT_EMBEDDING
        elif origin_model_type == 'reranking' or origin_model_type == cls.RERANK.value:
            return cls.RERANK
        elif origin_model_type == cls.SPEECH2TEXT.value:
            return cls.SPEECH2TEXT
        elif origin_model_type == cls.MODERATION.value:
            return cls.MODERATION
        else:
            raise ValueError(f'invalid origin model type {origin_model_type}')

    def to_origin_model_type(self) -> str:
        """
        Get origin model type from model type.

        :return: origin model type
        """
        if self == self.LLM:
            return 'text-generation'
        elif self == self.TEXT_EMBEDDING:
            return 'embeddings'
        elif self == self.RERANK:
            return 'reranking'
        elif self == self.SPEECH2TEXT:
            return 'speech2text'
        elif self == self.MODERATION:
            return 'moderation'
        else:
            raise ValueError(f'invalid model type {self}')


class FetchFrom(Enum):
    """
    Enum class for fetch from.
    """
    PREDEFINED_MODEL = "predefined-model"
    CUSTOMIZABLE_MODEL = "customizable-model"


class ModelFeature(Enum):
    """
    Enum class for llm feature.
    """
    TOOL_CALL = "tool-call"
    MULTI_TOOL_CALL = "multi-tool-call"
    AGENT_THOUGHT = "agent-thought"
    VISION = "vision"


class DefaultParameterName(Enum):
    """
    Enum class for parameter template variable.
    """
    TEMPERATURE = "temperature"
    TOP_P = "top_p"
    PRESENCE_PENALTY = "presence_penalty"
    FREQUENCY_PENALTY = "frequency_penalty"
    MAX_TOKENS = "max_tokens"

    @classmethod
    def value_of(cls, value: Any) -> 'DefaultParameterName':
        """
        Get parameter name from value.

        :param value: parameter value
        :return: parameter name
        """
        for name in cls:
            if name.value == value:
                return name
        raise ValueError(f'invalid parameter name {value}')


class ParameterType(Enum):
    """
    Enum class for parameter type.
    """
    FLOAT = "float"
    INT = "int"
    STRING = "string"
    BOOLEAN = "boolean"


class ModelPropertyKey(Enum):
    """
    Enum class for model property key.
    """
    MODE = "mode"
    CONTEXT_SIZE = "context_size"
    MAX_CHUNKS = "max_chunks"
    FILE_UPLOAD_LIMIT = "file_upload_limit"
    SUPPORTED_FILE_EXTENSIONS = "supported_file_extensions"
    MAX_CHARACTERS_PER_CHUNK = "max_characters_per_chunk"


class ProviderModel(BaseModel):
    """
    Model class for provider model.
    """
    model: str
    label: I18nObject
    model_type: ModelType
    features: Optional[list[ModelFeature]] = None
    fetch_from: FetchFrom
    model_properties: dict[ModelPropertyKey, Any]
    deprecated: bool = False

    class Config:
        protected_namespaces = ()


class ParameterRule(BaseModel):
    """
    Model class for parameter rule.
    """
    name: str
    use_template: Optional[str] = None
    label: I18nObject
    type: ParameterType
    help: Optional[I18nObject] = None
    required: bool = False
    default: Optional[Any] = None
    min: Optional[float | int] = None
    max: Optional[float | int] = None
    precision: Optional[int] = None
    options: list[str] = []


class PriceConfig(BaseModel):
    """
    Model class for pricing info.
    """
    input: Decimal
    output: Optional[Decimal] = None
    unit: Decimal
    currency: str


class AIModelEntity(ProviderModel):
    """
    Model class for AI model.
    """
    parameter_rules: list[ParameterRule] = []
    pricing: Optional[PriceConfig] = None


class ModelUsage(BaseModel):
    pass


class PriceType(Enum):
    """
    Enum class for price type.
    """
    INPUT = "input"
    OUTPUT = "output"


class PriceInfo(BaseModel):
    """
    Model class for price info.
    """
    unit_price: Decimal
    unit: Decimal
    total_amount: Decimal
    currency: str
