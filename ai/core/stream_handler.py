# ai/core/stream_handler.py
# imports
import json
import time
from typing import Generator, Dict, Any, Callable
from datetime import datetime
import logging

# Base logger
logger = logging.getLogger("my_app")


# StreamHandler class
class StreamHandler:
    def __init__(self, api_checker):
        self.api_checker = api_checker
        self.is_streaming = False
        self.current_stream = None
        self.stream_thread = None
        self.callbacks = []
        self.buffer = ""
        self.last_chunk_time = None

    def stream_chat_completion(
        self,
        model: str,
        messages: list,
        on_token: Callable[[str], None] = None,
        on_complete: Callable[[str], None] = None,
        on_error: Callable[[Exception], None] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        import requests

        url = f"{self.api_checker.base_url}/chat/completions"
        headers = self.api_checker.session.headers.copy()
        headers["Accept"] = "text/event-stream"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        self.is_streaming = True
        self.buffer = ""
        full_response = ""
        chunk_count = 0
        try:
            start_time = time.time()
            logger.info(f"Starting stream for model: {model}")
            with requests.post(
                url, headers=headers, json=payload, stream=True, timeout=60
            ) as response:
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(
                        f"Stream failed: {response.status_code} - {error_text}"
                    )
                    if on_error:
                        on_error(
                            Exception(f"HTTP {response.status_code}: {error_text}")
                        )
                    yield f"[ERROR: {error_text}]"
                    return
                for line in response.iter_lines():
                    if not line or line == b"data: [DONE]":
                        continue
                    if line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunk_count += 1
                                    full_response += content
                                    self.buffer += content
                                    self.last_chunk_time = time.time()
                                    # Callback on token
                                    if on_token:
                                        on_token(content)
                                    yield content
                            # Check for finish reason
                            if "choices" in data and data["choices"]:
                                finish_reason = data["choices"][0].get("finish_reason")
                                if finish_reason:
                                    logger.info(f"Stream completed: {finish_reason}")
                                    break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse stream data: {e}")
                            continue
                elapsed = time.time() - start_time
                logger.info(f"Stream completed: {chunk_count} chunks in {elapsed:.2f}s")
                # Callback on complete
                if on_complete:
                    on_complete(full_response)
                self.is_streaming = False
                return full_response
        except requests.exceptions.Timeout:
            error = TimeoutError("Stream timeout")
            logger.error("Stream timeout")
            if on_error:
                on_error(error)
            yield "[ERROR: Timeout]"
            self.is_streaming = False
        except Exception as e:
            logger.error(f"Stream error: {e}")
            if on_error:
                on_error(e)
            yield f"[ERROR: {e}]"
            self.is_streaming = False

    def stream_with_progress(
        self,
        model: str,
        messages: list,
        show_progress: bool = True,
        progress_callback: Callable[[int, int], None] = None,
    ) -> str:
        full_response = ""
        chunk_count = 0
        estimated_total = 100  # Will be updated

        def on_token(token: str):
            nonlocal full_response, chunk_count
            full_response += token
            chunk_count += 1

            if progress_callback:
                progress_callback(chunk_count, estimated_total)

        def on_complete(response: str):
            nonlocal full_response
            full_response = response

        for token in self.stream_chat_completion(
            model=model, messages=messages, on_token=on_token, on_complete=on_complete
        ):
            pass
        return full_response

    def stream_to_console(
        self, model: str, messages: list, prefix: str = "AI: "
    ) -> str:
        import sys

        full_response = ""
        first_token = True
        chunk_count = 0

        def on_token(token: str):
            nonlocal first_token, full_response, chunk_count
            if first_token:
                sys.stdout.write(f"\n{prefix}")
                first_token = False
            sys.stdout.write(token)
            sys.stdout.flush()
            full_response += token
            chunk_count += 1

        def on_complete(response: str):
            sys.stdout.write("\n")
            sys.stdout.flush()
            logger.info(f"Stream completed: {chunk_count} tokens")

        def on_error(error: Exception):
            sys.stdout.write(f"\n[ERROR: {error}]\n")
            sys.stdout.flush()

        for token in self.stream_chat_completion(
            model=model,
            messages=messages,
            on_token=on_token,
            on_complete=on_complete,
            on_error=on_error,
        ):
            pass
        return full_response

    def stream_with_color(
        self, model: str, messages: list, color: str = "\033[92m"
    ) -> str:
        import sys

        full_response = ""
        chunk_count = 0
        reset_color = "\033[0m"

        def on_token(token: str):
            nonlocal full_response, chunk_count
            if chunk_count == 0:
                sys.stdout.write(f"\n{color}")
            sys.stdout.write(token)
            sys.stdout.flush()
            full_response += token
            chunk_count += 1

        def on_complete(response: str):
            sys.stdout.write(reset_color)
            sys.stdout.write("\n")
            sys.stdout.flush()

        for token in self.stream_chat_completion(
            model=model, messages=messages, on_token=on_token, on_complete=on_complete
        ):
            pass
        return full_response

    def stop(self):
        """Stop the current stream"""
        self.is_streaming = False
        logger.info("Stream stopped")

    def is_active(self) -> bool:
        """Check if a stream is currently active"""
        return self.is_streaming

    def get_stats(self) -> Dict[str, Any]:
        """Get stream statistics"""
        return {
            "is_streaming": self.is_streaming,
            "buffer_size": len(self.buffer),
            "last_chunk": self.last_chunk_time,
        }


class StreamingChatSession:
    def __init__(self, stream_handler: StreamHandler, model: str):
        self.stream_handler = stream_handler
        self.model = model
        self.messages = []
        self.history = []
        self.streaming_enabled = True

    def send_message(self, message: str, streaming: bool = True) -> str:
        self.messages.append({"role": "user", "content": message})

        if streaming and self.streaming_enabled:
            response = self.stream_handler.stream_to_console(
                model=self.model, messages=self.messages
            )
        else:
            # Non-streaming fallback
            response = self.stream_handler.api_checker.chat_completion_with_history(
                self.model, self.messages
            )
            if response:
                print(f"\n🤖 AI: {response}")
            else:
                print("\n[ERROR: No response]")
                response = ""
        if response:
            self.messages.append({"role": "assistant", "content": response})
            self.history.append(
                {
                    "user": message,
                    "assistant": response,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        return response

    def get_history(self) -> list:
        """Get chat history"""
        return self.history

    def clear(self):
        """Clear chat history"""
        self.messages = []
        self.history = []

    def toggle_streaming(self):
        """Toggle streaming on/off"""
        self.streaming_enabled = not self.streaming_enabled
        status = "enabled" if self.streaming_enabled else "disabled"
        print(f"\nStreaming {status}")
