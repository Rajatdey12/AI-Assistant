"""
LLM (Large Language Model) Module for Chiku: pluggable backend adapter

Features:
- Configurable backend support for Ollama or remote HTTP model servers
- Support for Mistral, Llama, Falcon, and other open-source models
- Streaming responses for lower latency
- System prompt with Jarvis-like personality
- Context-aware responses with conversation history
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any
import requests
import config

logger = logging.getLogger(__name__)

# ============ GLOBALS ============
BACKEND = config.LLM.get("backend", "ollama").lower()
MODEL = config.LLM["model"]
API_KEY = config.LLM.get("api_key", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

HUGGINGFACE_API_BASE = "https://api-inference.huggingface.co/models"
OPENAI_API_BASE = "https://api.openai.com/v1/chat/completions"


def _get_request_url(model: str) -> str:
    if BACKEND == "ollama":
        return f"{OLLAMA_HOST.rstrip('/')}/api/generate"
    if BACKEND in ("huggingface", "hf"):
        return f"{HUGGINGFACE_API_BASE}/{model}"
    if BACKEND in ("openai", "chatgpt"):
        return OPENAI_API_BASE
    raise ValueError(f"Unsupported LLM backend: {BACKEND}")


def _get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if BACKEND in ("huggingface", "hf", "openai", "chatgpt") and API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _parse_remote_response(result: Any) -> str:
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        return (
            result.get("response") or
            result.get("generated_text") or
            result.get("text") or
            result.get("generated_text") or
            result.get("output") or
            ""
        ).strip()
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            return (
                first.get("response") or
                first.get("generated_text") or
                first.get("text") or
                first.get("output") or
                ""
            ).strip()
        if isinstance(first, str):
            return first.strip()
    return ""


def _ollama_check_health() -> bool:
    try:
        response = requests.get(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=2, headers=_get_headers())
        if response.status_code == 200:
            logger.info(f"✅ Ollama server is healthy ({OLLAMA_HOST})")
            return True
        logger.error(f"❌ Ollama returned status {response.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to Ollama at {OLLAMA_HOST}")
        logger.info("   Make sure Ollama is running: ollama serve")
        return False
    except Exception as e:
        logger.error(f"❌ Ollama health check failed: {e}")
        return False


def _huggingface_check_health() -> bool:
    health_url = _get_request_url(MODEL)
    try:
        response = requests.head(health_url, timeout=2, headers=_get_headers())
        if response.status_code in (200, 401, 403, 404):
            logger.info(f"✅ Hugging Face model endpoint is reachable ({health_url})")
            return True
        logger.warning(f"⚠️ Hugging Face endpoint returned {response.status_code} for health check")
        return False
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to Hugging Face endpoint at {health_url}")
        return False
    except Exception as e:
        logger.error(f"❌ Hugging Face health check failed: {e}")
        return False


def _openai_check_health() -> bool:
    try:
        response = requests.get("https://api.openai.com/v1/models", timeout=2, headers=_get_headers())
        if response.status_code == 200:
            logger.info("✅ OpenAI API is reachable")
            return True
        logger.warning(f"⚠️ OpenAI endpoint returned {response.status_code} for health check")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to OpenAI API")
        return False
    except Exception as e:
        logger.error(f"❌ OpenAI health check failed: {e}")
        return False


def check_health() -> bool:
    if BACKEND == "ollama":
        return _ollama_check_health()
    if BACKEND in ("huggingface", "hf"):
        return _huggingface_check_health()
    if BACKEND in ("openai", "chatgpt"):
        return _openai_check_health()
    logger.error(f"❌ Unsupported LLM backend: {BACKEND}")
    return False


def list_available_models() -> List[str]:
    if BACKEND == "ollama":
        try:
            response = requests.get(f"{OLLAMA_HOST.rstrip('/')}/api/tags", timeout=5, headers=_get_headers())
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m["name"] for m in models]
        except Exception as e:
            logger.error(f"❌ Failed to list Ollama models: {e}")
            return []
    logger.warning("Model listing is not supported for the remote LLM backend")
    return []


def verify_model_exists(model_name: str = MODEL) -> bool:
    if BACKEND == "ollama":
        available_models = list_available_models()
        return any(model_name in m for m in available_models)
    return True


def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = MODEL,
    temperature: float = config.LLM["temperature"],
    top_p: float = config.LLM["top_p"],
    num_predict: int = config.LLM["num_predict"],
    stream: bool = False,
    verbose: bool = False
) -> str:
    """
    Generate text using the configured LLM backend.
    
    Args:
        prompt: User input/question
        system_prompt: System prompt (default: Jarvis personality)
        model: Model name (default: mistral:7b)
        temperature: Creativity level (0-1, default 0.7)
        top_p: Nucleus sampling (0-1, default 0.9)
        num_predict: Max tokens to generate (default 256)
        stream: Use streaming response (faster perceived latency)
        verbose: Print progress
    
    Returns:
        Generated text response
    """
    
    if system_prompt is None:
        system_prompt = config.SYSTEM_PROMPT
    
    if verbose:
        print(f"🤖 Generating response with {BACKEND} backend ({model})...")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "system": system_prompt,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": num_predict,
            "num_ctx": config.LLM["num_ctx"],
        }
    }
    
    if BACKEND == "ollama":
        request_url = _get_request_url(model)
        request_body = payload
        stream_request = stream
    elif BACKEND in ("huggingface", "hf"):
        request_url = _get_request_url(model)
        request_body = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "top_p": top_p,
                "max_new_tokens": num_predict,
            }
        }
        stream_request = False
    elif BACKEND in ("openai", "chatgpt"):
        request_url = _get_request_url(model)
        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": num_predict,
        }
        stream_request = False
    else:
        raise ValueError(f"Unsupported LLM backend: {BACKEND}")

    try:
        response = requests.post(
            request_url,
            json=request_body,
            headers=_get_headers(),
            timeout=(config.LLM["connect_timeout"], config.LLM["request_timeout"]),
            stream=stream_request
        )
        response.raise_for_status()

        if BACKEND == "ollama" and stream:
            full_response = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    text_chunk = _parse_remote_response(chunk)
                    full_response += text_chunk
                    if verbose:
                        print(text_chunk, end="", flush=True)
            
            if verbose:
                print()
            return full_response.strip()

        result = response.json()
        if BACKEND in ("openai", "chatgpt"):
            result = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        text = _parse_remote_response(result)
        
        if verbose:
            print(f"✅ Response: {text[:100]}...")
        return text
    except requests.exceptions.ConnectTimeout:
        error_msg = f"Cannot connect to LLM backend at {request_url} (connect timeout={config.LLM['connect_timeout']}s)."
        logger.error(f"❌ {error_msg}")
        raise ConnectionError(error_msg)
    except requests.exceptions.ReadTimeout:
        error_msg = f"LLM request timed out after {config.LLM['request_timeout']} seconds."
        logger.error(f"❌ {error_msg}")
        raise TimeoutError(error_msg)
    except requests.exceptions.Timeout as e:
        error_msg = f"LLM request timed out: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise TimeoutError(error_msg)
    except requests.exceptions.ConnectionError:
        error_msg = f"Cannot connect to LLM backend at {request_url}."
        logger.error(f"❌ {error_msg}")
        raise ConnectionError(error_msg)
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, 'status_code', None)
        if BACKEND == "ollama" and status == 404:
            logger.error(f"❌ Model '{model}' not found in Ollama")
            logger.info(f"   Available: {list_available_models()}")
            raise ValueError(f"Model '{model}' not found")
        raise
    except Exception as e:
        logger.error(f"❌ LLM error: {e}")
        raise


async def generate_streaming(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = MODEL,
    temperature: float = config.LLM["temperature"],
    top_p: float = config.LLM["top_p"],
    num_predict: int = config.LLM["num_predict"],
    verbose: bool = False
):
    """
    Generate text using streaming response for lower latency.
    
    Args:
        prompt: User input/question
        system_prompt: System prompt (default: Jarvis personality)
        model: Model name (default: mistral:7b)
        temperature: Creativity level (0-1, default 0.7)
        top_p: Nucleus sampling (0-1, default 0.9)
        num_predict: Max tokens to generate (default 256)
        verbose: Print progress
    
    Yields:
        Text chunks as they become available
    """
    
    if system_prompt is None:
        system_prompt = config.SYSTEM_PROMPT
    
    if verbose:
        print(f"🤖 Streaming response with {BACKEND} backend ({model})...")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "system": system_prompt,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "num_predict": num_predict,
            "num_ctx": config.LLM["num_ctx"],
        }
    }
    
    if BACKEND == "ollama":
        request_url = _get_request_url(model)
        request_body = payload
    else:
        # For non-streaming backends, fall back to regular generation
        result = generate(prompt, system_prompt, model, temperature, top_p, num_predict, stream=False, verbose=verbose)
        yield result
        return

    try:
        # Use asyncio.to_thread for the blocking requests call
        response = await asyncio.to_thread(
            lambda: requests.post(
                request_url,
                json=request_body,
                headers=_get_headers(),
                timeout=(config.LLM["connect_timeout"], config.LLM["request_timeout"]),
                stream=True
            )
        )
        response.raise_for_status()

        # Process streaming response
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                text_chunk = _parse_remote_response(chunk)
                if text_chunk:
                    yield text_chunk
                    if verbose:
                        print(text_chunk, end="", flush=True)
        
        if verbose:
            print()
            
    except Exception as e:
        logger.error(f"❌ Streaming LLM error: {e}")
        raise


async def generate_with_context_streaming(
    user_message: str,
    conversation_history: List[Dict],
    system_prompt: Optional[str] = None,
    model: str = MODEL,
    **kwargs
):
    """
    Generate streaming response with full conversation context.
    
    Args:
        user_message: Latest user input
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts
        system_prompt: System prompt
        model: Model to use
        **kwargs: Additional args for generate_streaming()
    
    Yields:
        Text chunks as they become available
    """
    
    # Format history for prompt
    context_str = ""
    for msg in conversation_history[-config.SESSION["max_history_turns"]:]:
        role = msg["role"].capitalize()
        content = msg["content"]
        context_str += f"{role}: {content}\n"
    
    # Add user message
    full_prompt = context_str + f"User: {user_message}\nAssistant:"
    
    async for chunk in generate_streaming(full_prompt, system_prompt=system_prompt, model=model, **kwargs):
        yield chunk


def generate_with_context(
    user_message: str,
    conversation_history: List[Dict],
    system_prompt: Optional[str] = None,
    model: str = MODEL,
    **kwargs
) -> str:
    """
    Generate response with full conversation context.
    
    Args:
        user_message: Latest user input
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts
        system_prompt: System prompt
        model: Model to use
        **kwargs: Additional args for generate()
    
    Returns:
        Generated response
    
    Example:
        >>> history = [
        ...     {"role": "user", "content": "What's your name?"},
        ...     {"role": "assistant", "content": "I'm Chiku"}
        ... ]
        >>> response = generate_with_context("Nice to meet you!", history)
    """
    
    # Format history for prompt
    context_str = ""
    for msg in conversation_history[-config.SESSION["max_history_turns"]:]:
        role = msg["role"].capitalize()
        content = msg["content"]
        context_str += f"{role}: {content}\n"
    
    # Add user message
    full_prompt = context_str + f"User: {user_message}\nAssistant:"
    
    return generate(full_prompt, system_prompt=system_prompt, model=model, **kwargs)


if __name__ == "__main__":
    print(f"Testing LLM backend: {BACKEND}\n")

    if not check_health():
        print("❌ LLM backend is not reachable!")
        if BACKEND == "ollama":
            print("   Start it with: ollama serve")
        exit(1)

    if BACKEND == "ollama":
        models = list_available_models()
        print(f"✅ Available models: {models}\n")
        if verify_model_exists(MODEL):
            print(f"Testing {MODEL}...\n")
            response = generate(
                "What is your name?",
                verbose=True
            )
            print(f"\n🎯 Full response:\n{response}")
        else:
            print(f"❌ Model {MODEL} not found!")
            print(f"   Available: {models}")
            print(f"   Install with: ollama pull {MODEL}")
    else:
        print("✅ Remote LLM backend reachable.")
        print(f"Testing model {MODEL} via remote endpoint...\n")
        response = generate(
            "What is your name?",
            verbose=True
        )
        print(f"\n🎯 Full response:\n{response}")
