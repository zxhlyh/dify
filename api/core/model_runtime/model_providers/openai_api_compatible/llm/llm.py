import logging
from decimal import Decimal
from urllib.parse import urljoin

import requests
import json

from typing import Optional, Generator, Union, List, cast

from core.model_runtime.entities.common_entities import I18nObject
from core.model_runtime.utils import helper

from core.model_runtime.entities.message_entities import ImagePromptMessageContent, PromptMessage, \
    AssistantPromptMessage, PromptMessageContent, \
    PromptMessageContentType, PromptMessageFunction, PromptMessageTool, UserPromptMessage, SystemPromptMessage, \
    ToolPromptMessage
from core.model_runtime.entities.model_entities import ModelPropertyKey, ModelType, PriceConfig, ParameterRule, \
    DefaultParameterName, \
    ParameterType, ModelPropertyKey, FetchFrom, AIModelEntity
from core.model_runtime.entities.llm_entities import LLMMode, LLMResult, LLMResultChunk, LLMResultChunkDelta
from core.model_runtime.errors.invoke import InvokeError
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.__base.large_language_model import LargeLanguageModel
from core.model_runtime.model_providers.openai_api_compatible._common import _CommonOAI_API_Compat

logger = logging.getLogger(__name__)


class OAIAPICompatLargeLanguageModel(_CommonOAI_API_Compat, LargeLanguageModel):
    """
    Model class for OpenAI large language model.
    """

    def _invoke(self, model: str, credentials: dict,
                prompt_messages: list[PromptMessage], model_parameters: dict,
                tools: Optional[list[PromptMessageTool]] = None, stop: Optional[List[str]] = None,
                stream: bool = True, user: Optional[str] = None) \
            -> Union[LLMResult, Generator]:
        """
        Invoke large language model

        :param model: model name
        :param credentials: model credentials
        :param prompt_messages: prompt messages
        :param model_parameters: model parameters
        :param tools: tools for tool calling
        :param stop: stop words
        :param stream: is stream response
        :param user: unique user id
        :return: full response or stream response chunk generator result
        """

        # text completion model
        return self._generate(
            model=model,
            credentials=credentials,
            prompt_messages=prompt_messages,
            model_parameters=model_parameters,
            tools=tools,
            stop=stop,
            stream=stream,
            user=user
        )

    def get_num_tokens(self, model: str, credentials: dict, prompt_messages: list[PromptMessage],
                       tools: Optional[list[PromptMessageTool]] = None) -> int:
        """
        Get number of tokens for given prompt messages

        :param model:
        :param credentials:
        :param prompt_messages:
        :param tools: tools for tool calling
        :return:
        """
        return self._num_tokens_from_messages(model, prompt_messages, tools)

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials using requests to ensure compatibility with all providers following OpenAI's API standard.

        :param model: model name
        :param credentials: model credentials
        :return:
        """
        try:
            headers = {
                'Content-Type': 'application/json'
            }

            api_key = credentials.get('api_key')
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            endpoint_url = credentials['endpoint_url']
            if not endpoint_url.endswith('/'):
                endpoint_url += '/'

            # prepare the payload for a simple ping to the model
            data = {
                'model': model,
                'max_tokens': 5
            }

            completion_type = LLMMode.value_of(credentials['mode'])

            if completion_type is LLMMode.CHAT:
                data['messages'] = [
                    {
                        "role": "user",
                        "content": "ping"
                    },
                ]
                endpoint_url = urljoin(endpoint_url, 'chat/completions')
            elif completion_type is LLMMode.COMPLETION:
                data['prompt'] = 'ping'
                endpoint_url = urljoin(endpoint_url, 'completions')
            else:
                raise ValueError("Unsupported completion type for model configuration.")

            # send a post request to validate the credentials
            response = requests.post(
                endpoint_url,
                headers=headers,
                json=data,
                timeout=(10, 60)
            )

            if response.status_code != 200:
                raise CredentialsValidateFailedError(
                    f'Credentials validation failed with status code {response.status_code}')

            try:
                json_result = response.json()
            except json.JSONDecodeError as e:
                raise CredentialsValidateFailedError(f'Credentials validation failed: JSON decode error')

            if (completion_type is LLMMode.CHAT
                    and ('object' not in json_result or json_result['object'] != 'chat.completion')):
                raise CredentialsValidateFailedError(
                    f'Credentials validation failed: invalid response object, must be \'chat.completion\'')
            elif (completion_type is LLMMode.COMPLETION
                  and ('object' not in json_result or json_result['object'] != 'text_completion')):
                raise CredentialsValidateFailedError(
                    f'Credentials validation failed: invalid response object, must be \'text_completion\'')
        except CredentialsValidateFailedError:
            raise
        except Exception as ex:
            raise CredentialsValidateFailedError(f'An error occurred during credentials validation: {str(ex)}')

    def get_customizable_model_schema(self, model: str, credentials: dict) -> AIModelEntity:
        """
            generate custom model entities from credentials
        """
        entity = AIModelEntity(
            model=model,
            label=I18nObject(en_US=model),
            model_type=ModelType.LLM,
            fetch_from=FetchFrom.CUSTOMIZABLE_MODEL,
            model_properties={
                ModelPropertyKey.CONTEXT_SIZE: int(credentials.get('context_size')),
                ModelPropertyKey.MODE: credentials.get('mode'),
            },
            parameter_rules=[
                ParameterRule(
                    name=DefaultParameterName.TEMPERATURE.value,
                    label=I18nObject(en_US="Temperature"),
                    type=ParameterType.FLOAT,
                    default=float(credentials.get('temperature', 0.7)),
                    min=0,
                    max=2
                ),
                ParameterRule(
                    name=DefaultParameterName.TOP_P.value,
                    label=I18nObject(en_US="Top P"),
                    type=ParameterType.FLOAT,
                    default=float(credentials.get('top_p', 1)),
                    min=0,
                    max=1
                ),
                ParameterRule(
                    name="top_k",
                    label=I18nObject(en_US="Top K"),
                    type=ParameterType.INT,
                    default=int(credentials.get('top_k', 1)),
                    min=1,
                    max=100
                ),
                ParameterRule(
                    name=DefaultParameterName.FREQUENCY_PENALTY.value,
                    label=I18nObject(en_US="Frequency Penalty"),
                    type=ParameterType.FLOAT,
                    default=float(credentials.get('frequency_penalty', 0)),
                    min=-2,
                    max=2
                ),
                ParameterRule(
                    name=DefaultParameterName.PRESENCE_PENALTY.value,
                    label=I18nObject(en_US="PRESENCE Penalty"),
                    type=ParameterType.FLOAT,
                    default=float(credentials.get('PRESENCE_penalty', 0)),
                    min=-2,
                    max=2
                ),
                ParameterRule(
                    name=DefaultParameterName.MAX_TOKENS.value,
                    label=I18nObject(en_US="Max Tokens"),
                    type=ParameterType.INT,
                    default=512,
                    min=1,
                    max=int(credentials.get('max_tokens_to_sample', 4096)),
                )
            ],
            pricing=PriceConfig(
                input=Decimal(credentials.get('input_price', 0)),
                output=Decimal(credentials.get('output_price', 0)),
                unit=Decimal(credentials.get('unit', 0)),
                currency=credentials.get('currency', "USD")
            )
        )

        return entity

    # validate_credentials method has been rewritten to use the requests library for compatibility with all providers following OpenAI's API standard.
    def _generate(self, model: str, credentials: dict, prompt_messages: list[PromptMessage], model_parameters: dict,
                  tools: Optional[list[PromptMessageTool]] = None, stop: Optional[List[str]] = None,
                  stream: bool = True, \
                  user: Optional[str] = None) -> Union[LLMResult, Generator]:
        """
        Invoke llm completion model

        :param model: model name
        :param credentials: credentials
        :param prompt_messages: prompt messages
        :param model_parameters: model parameters
        :param stop: stop words
        :param stream: is stream response
        :param user: unique user id
        :return: full response or stream response chunk generator result
        """
        headers = {
            'Content-Type': 'application/json'
        }

        api_key = credentials.get('api_key')
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        endpoint_url = credentials["endpoint_url"]
        if not endpoint_url.endswith('/'):
            endpoint_url += '/'

        data = {
            "model": model,
            "stream": stream,
            **model_parameters
        }

        completion_type = LLMMode.value_of(credentials['mode'])

        if completion_type is LLMMode.CHAT:
            endpoint_url = urljoin(endpoint_url, 'chat/completions')
            data['messages'] = [self._convert_prompt_message_to_dict(m) for m in prompt_messages]
        elif completion_type == LLMMode.COMPLETION:
            endpoint_url = urljoin(endpoint_url, 'completions')
            data['prompt'] = prompt_messages[0].content
        else:
            raise ValueError("Unsupported completion type for model configuration.")

        # annotate tools with names, descriptions, etc.
        formatted_tools = []
        if tools:
            data["tool_choice"] = "auto"

            for tool in tools:
                formatted_tools.append(helper.dump_model(PromptMessageFunction(function=tool)))

            data["tools"] = formatted_tools

        if stop:
            data["stop"] = stop

        if user:
            data["user"] = user

        response = requests.post(
            endpoint_url,
            headers=headers,
            json=data,
            timeout=(10, 60),
            stream=stream
        )

        # Debug: Print request headers and json data
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request JSON data: {data}")

        if response.status_code != 200:
            raise InvokeError(f"API request failed with status code {response.status_code}: {response.text}")

        if stream:
            return self._handle_generate_stream_response(model, credentials, response, prompt_messages)

        return self._handle_generate_response(model, credentials, response, prompt_messages)

    def _handle_generate_stream_response(self, model: str, credentials: dict, response: requests.Response,
                                         prompt_messages: list[PromptMessage]) -> Generator:
        """
        Handle llm stream response

        :param model: model name
        :param credentials: model credentials
        :param response: streamed response
        :param prompt_messages: prompt messages
        :return: llm response chunk generator
        """
        full_assistant_content = ''
        chunk_index = 0

        def create_final_llm_result_chunk(index: int, message: AssistantPromptMessage, finish_reason: str) \
                -> LLMResultChunk:
            # calculate num tokens
            prompt_tokens = self._num_tokens_from_string(model, prompt_messages[0].content)
            completion_tokens = self._num_tokens_from_string(model, full_assistant_content)

            # transform usage
            usage = self._calc_response_usage(model, credentials, prompt_tokens, completion_tokens)

            return LLMResultChunk(
                model=model,
                prompt_messages=prompt_messages,
                delta=LLMResultChunkDelta(
                    index=index,
                    message=message,
                    finish_reason=finish_reason,
                    usage=usage
                )
            )

        for chunk in response.iter_content(chunk_size=2048):
            if chunk:
                decoded_chunk = chunk.decode('utf-8').strip().lstrip('data: ').lstrip()

                chunk_json = None
                try:
                    chunk_json = json.loads(decoded_chunk)
                # stream ended
                except json.JSONDecodeError as e:
                    yield create_final_llm_result_chunk(
                        index=chunk_index + 1,
                        message=AssistantPromptMessage(content=""),
                        finish_reason="Non-JSON encountered."
                    )

                if not chunk_json or len(chunk_json['choices']) == 0:
                    continue

                choice = chunk_json['choices'][0]
                chunk_index = choice['index'] if 'index' in choice else chunk_index

                if 'delta' in choice:
                    delta = choice['delta']
                    if delta.get('content') is None or delta.get('content') == '':
                        continue

                    assistant_message_tool_calls = delta.get('tool_calls', None)
                    # assistant_message_function_call = delta.delta.function_call

                    # extract tool calls from response
                    if assistant_message_tool_calls:
                        tool_calls = self._extract_response_tool_calls(assistant_message_tool_calls)
                    # function_call = self._extract_response_function_call(assistant_message_function_call)
                    # tool_calls = [function_call] if function_call else []

                    # transform assistant message to prompt message
                    assistant_prompt_message = AssistantPromptMessage(
                        content=delta.get('content', ''),
                        tool_calls=tool_calls if assistant_message_tool_calls else []
                    )

                    full_assistant_content += delta.get('content', '')
                elif 'text' in choice:
                    if choice.get('text') is None or choice.get('text') == '':
                        continue

                    # transform assistant message to prompt message
                    assistant_prompt_message = AssistantPromptMessage(
                        content=choice.get('text', '')
                    )

                    full_assistant_content += choice.get('text', '')
                else:
                    continue

                # check payload indicator for completion
                if chunk_json['choices'][0].get('finish_reason') is not None:
                    yield create_final_llm_result_chunk(
                        index=chunk_index,
                        message=assistant_prompt_message,
                        finish_reason=chunk_json['choices'][0]['finish_reason']
                    )
                else:
                    yield LLMResultChunk(
                        model=model,
                        prompt_messages=prompt_messages,
                        delta=LLMResultChunkDelta(
                            index=chunk_index,
                            message=assistant_prompt_message,
                        )
                    )
            else:
                yield create_final_llm_result_chunk(
                    index=chunk_index + 1,
                    message=AssistantPromptMessage(content=""),
                    finish_reason="End of stream."
                )

            chunk_index += 1

    def _handle_generate_response(self, model: str, credentials: dict, response: requests.Response,
                                  prompt_messages: list[PromptMessage]) -> LLMResult:

        response_json = response.json()

        completion_type = LLMMode.value_of(credentials['mode'])

        output = response_json['choices'][0]

        response_content = ''
        tool_calls = None

        if completion_type is LLMMode.CHAT:
            response_content = output.get('message', {})['content']
            tool_calls = output.get('message', {}).get('tool_calls')

        elif completion_type is LLMMode.COMPLETION:
            response_content = output['text']

        assistant_message = AssistantPromptMessage(content=response_content, tool_calls=[])

        if tool_calls:
            assistant_message.tool_calls = self._extract_response_tool_calls(tool_calls)

        usage = response_json.get("usage")
        if usage:
            # transform usage
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
        else:
            # calculate num tokens
            prompt_tokens = self._num_tokens_from_string(model, prompt_messages[0].content)
            completion_tokens = self._num_tokens_from_string(model, assistant_message.content)

        # transform usage
        usage = self._calc_response_usage(model, credentials, prompt_tokens, completion_tokens)

        # transform response
        result = LLMResult(
            model=response_json["model"],
            prompt_messages=prompt_messages,
            message=assistant_message,
            usage=usage,
        )

        return result

    def _convert_prompt_message_to_dict(self, message: PromptMessage) -> dict:
        """
        Convert PromptMessage to dict for OpenAI API format
        """
        if isinstance(message, UserPromptMessage):
            message = cast(UserPromptMessage, message)
            if isinstance(message.content, str):
                message_dict = {"role": "user", "content": message.content}
            else:
                sub_messages = []
                for message_content in message.content:
                    if message_content.type == PromptMessageContentType.TEXT:
                        message_content = cast(PromptMessageContent, message_content)
                        sub_message_dict = {
                            "type": "text",
                            "text": message_content.data
                        }
                        sub_messages.append(sub_message_dict)
                    elif message_content.type == PromptMessageContentType.IMAGE:
                        message_content = cast(ImagePromptMessageContent, message_content)
                        sub_message_dict = {
                            "type": "image_url",
                            "image_url": {
                                "url": message_content.data,
                                "detail": message_content.detail.value
                            }
                        }
                        sub_messages.append(sub_message_dict)

                message_dict = {"role": "user", "content": sub_messages}
        elif isinstance(message, AssistantPromptMessage):
            message = cast(AssistantPromptMessage, message)
            message_dict = {"role": "assistant", "content": message.content}
            if message.tool_calls:
                message_dict["tool_calls"] = [helper.dump_model(PromptMessageFunction(function=tool_call)) for tool_call
                                              in
                                              message.tool_calls]
                # function_call = message.tool_calls[0]
                # message_dict["function_call"] = {
                #     "name": function_call.function.name,
                #     "arguments": function_call.function.arguments,
                # }
        elif isinstance(message, SystemPromptMessage):
            message = cast(SystemPromptMessage, message)
            message_dict = {"role": "system", "content": message.content}
        elif isinstance(message, ToolPromptMessage):
            message = cast(ToolPromptMessage, message)
            message_dict = {
                "role": "tool",
                "content": message.content,
                "tool_call_id": message.tool_call_id
            }
            # message_dict = {
            #     "role": "function",
            #     "content": message.content,
            #     "name": message.tool_call_id
            # }
        else:
            raise ValueError(f"Got unknown type {message}")

        if message.name is not None:
            message_dict["name"] = message.name

        return message_dict

    def _num_tokens_from_string(self, model: str, text: str,
                                tools: Optional[list[PromptMessageTool]] = None) -> int:
        """
        Approximate num tokens for model with gpt2 tokenizer.

        :param model: model name
        :param text: prompt text
        :param tools: tools for tool calling
        :return: number of tokens
        """
        num_tokens = self._get_num_tokens_by_gpt2(text)

        if tools:
            num_tokens += self._num_tokens_for_tools(tools)

        return num_tokens

    def _num_tokens_from_messages(self, model: str, messages: List[PromptMessage],
                                  tools: Optional[list[PromptMessageTool]] = None) -> int:
        """
        Approximate num tokens with GPT2 tokenizer.
        """

        tokens_per_message = 3
        tokens_per_name = 1

        num_tokens = 0
        messages_dict = [self._convert_prompt_message_to_dict(m) for m in messages]
        for message in messages_dict:
            num_tokens += tokens_per_message
            for key, value in message.items():
                # Cast str(value) in case the message value is not a string
                # This occurs with function messages
                # TODO: The current token calculation method for the image type is not implemented,
                #  which need to download the image and then get the resolution for calculation,
                #  and will increase the request delay
                if isinstance(value, list):
                    text = ''
                    for item in value:
                        if isinstance(item, dict) and item['type'] == 'text':
                            text += item['text']

                    value = text

                if key == "tool_calls":
                    for tool_call in value:
                        for t_key, t_value in tool_call.items():
                            num_tokens += self._get_num_tokens_by_gpt2(t_key)
                            if t_key == "function":
                                for f_key, f_value in t_value.items():
                                    num_tokens += self._get_num_tokens_by_gpt2(f_key)
                                    num_tokens += self._get_num_tokens_by_gpt2(f_value)
                            else:
                                num_tokens += self._get_num_tokens_by_gpt2(t_key)
                                num_tokens += self._get_num_tokens_by_gpt2(t_value)
                else:
                    num_tokens += self._get_num_tokens_by_gpt2(str(value))

                if key == "name":
                    num_tokens += tokens_per_name

        # every reply is primed with <im_start>assistant
        num_tokens += 3

        if tools:
            num_tokens += self._num_tokens_for_tools(tools)

        return num_tokens

    def _num_tokens_for_tools(self, tools: list[PromptMessageTool]) -> int:
        """
        Calculate num tokens for tool calling with tiktoken package.

        :param tools: tools for tool calling
        :return: number of tokens
        """
        num_tokens = 0
        for tool in tools:
            num_tokens += self._get_num_tokens_by_gpt2('type')
            num_tokens += self._get_num_tokens_by_gpt2('function')
            num_tokens += self._get_num_tokens_by_gpt2('function')

            # calculate num tokens for function object
            num_tokens += self._get_num_tokens_by_gpt2('name')
            num_tokens += self._get_num_tokens_by_gpt2(tool.name)
            num_tokens += self._get_num_tokens_by_gpt2('description')
            num_tokens += self._get_num_tokens_by_gpt2(tool.description)
            parameters = tool.parameters
            num_tokens += self._get_num_tokens_by_gpt2('parameters')
            if 'title' in parameters:
                num_tokens += self._get_num_tokens_by_gpt2('title')
                num_tokens += self._get_num_tokens_by_gpt2(parameters.get("title"))
            num_tokens += self._get_num_tokens_by_gpt2('type')
            num_tokens += self._get_num_tokens_by_gpt2(parameters.get("type"))
            if 'properties' in parameters:
                num_tokens += self._get_num_tokens_by_gpt2('properties')
                for key, value in parameters.get('properties').items():
                    num_tokens += self._get_num_tokens_by_gpt2(key)
                    for field_key, field_value in value.items():
                        num_tokens += self._get_num_tokens_by_gpt2(field_key)
                        if field_key == 'enum':
                            for enum_field in field_value:
                                num_tokens += 3
                                num_tokens += self._get_num_tokens_by_gpt2(enum_field)
                        else:
                            num_tokens += self._get_num_tokens_by_gpt2(field_key)
                            num_tokens += self._get_num_tokens_by_gpt2(str(field_value))
            if 'required' in parameters:
                num_tokens += self._get_num_tokens_by_gpt2('required')
                for required_field in parameters['required']:
                    num_tokens += 3
                    num_tokens += self._get_num_tokens_by_gpt2(required_field)

        return num_tokens

    def _extract_response_tool_calls(self,
                                     response_tool_calls: list[dict]) \
            -> list[AssistantPromptMessage.ToolCall]:
        """
        Extract tool calls from response

        :param response_tool_calls: response tool calls
        :return: list of tool calls
        """
        tool_calls = []
        if response_tool_calls:
            for response_tool_call in response_tool_calls:
                function = AssistantPromptMessage.ToolCall.ToolCallFunction(
                    name=response_tool_call["function"]["name"],
                    arguments=response_tool_call["function"]["arguments"]
                )

                tool_call = AssistantPromptMessage.ToolCall(
                    id=response_tool_call["id"],
                    type=response_tool_call["type"],
                    function=function
                )
                tool_calls.append(tool_call)

        return tool_calls
