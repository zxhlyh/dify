import os

import pytest

from core.model_runtime.entities.text_embedding_entities import TextEmbeddingResult
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.openai_api_compatible.text_embedding.text_embedding import OAICompatEmbeddingModel

"""
Using OpenAI's API as testing endpoint
"""

def test_validate_credentials():
    model = OAICompatEmbeddingModel()

    with pytest.raises(CredentialsValidateFailedError):
        model.validate_credentials(
            model='text-embedding-ada-002',
            credentials={
                'api_key': 'invalid_key',
                'endpoint_url': 'https://api.openai.com/v1/embeddings',
                'context_size': 8184,
                'max_chunks': 32
                
            }
        )

    model.validate_credentials(
        model='text-embedding-ada-002',
        credentials={
            'api_key': os.environ.get('OPENAI_API_KEY'),
            'endpoint_url': 'https://api.openai.com/v1/embeddings',
            'context_size': 8184,
            'max_chunks': 32
        }
    )


def test_invoke_model():
    model = OAICompatEmbeddingModel()

    result = model.invoke(
        model='text-embedding-ada-002',
        credentials={
            'api_key': os.environ.get('OPENAI_API_KEY'),
            'endpoint_url': 'https://api.openai.com/v1/embeddings',
            'context_size': 8184,
            'max_chunks': 32
        },
        texts=[
            "hello",
            "world"
        ],
        user="abc-123"
    )

    assert isinstance(result, TextEmbeddingResult)
    assert len(result.embeddings) == 2
    assert result.usage.total_tokens == 2


def test_get_num_tokens():
    model = OAICompatEmbeddingModel()

    num_tokens = model.get_num_tokens(
        model='text-embedding-ada-002',
        credentials={
            'api_key': os.environ.get('OPENAI_API_KEY'),
            'endpoint_url': 'https://api.openai.com/v1/embeddings',
            'context_size': 8184,
            'max_chunks': 32
        },
        texts=[
            "hello",
            "world"
        ]
    )

    assert num_tokens == 2