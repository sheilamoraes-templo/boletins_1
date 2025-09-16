"""
Proteção da API do OpenRouter: rate limiting, backoff, monitoramento e modo demo
"""

import threading
import time
import logging
import queue
from typing import Dict, Any, Optional, Callable
import requests

from config import Config

logger = logging.getLogger(__name__)

class OpenRouterRateLimiter:
    """Rate limiter conservador para chamadas ao OpenRouter"""

    def __init__(self,
                 max_per_minute: int = 3,
                 max_per_hour: int = 100,
                 min_delay_seconds: float = 5.0,
                 max_retries: int = 2):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.min_delay_seconds = min_delay_seconds
        self.max_retries = max_retries

        self._lock = threading.Lock()
        self._last_call_ts = 0.0
        self._minute_window = []  # timestamps
        self._hour_window = []    # timestamps

    def _prune(self, now: float):
        one_minute_ago = now - 60
        one_hour_ago = now - 3600
        self._minute_window = [t for t in self._minute_window if t > one_minute_ago]
        self._hour_window = [t for t in self._hour_window if t > one_hour_ago]

    def acquire(self) -> float:
        with self._lock:
            now = time.time()
            self._prune(now)

            # Enforce min delay between calls
            wait_min_delay = max(0.0, self.min_delay_seconds - (now - self._last_call_ts))

            # Enforce RPM/RPH windows
            if len(self._minute_window) >= self.max_per_minute:
                earliest = self._minute_window[0]
                wait_rpm = max(0.0, 60 - (now - earliest))
            else:
                wait_rpm = 0.0

            if len(self._hour_window) >= self.max_per_hour:
                earliest_h = self._hour_window[0]
                wait_rph = max(0.0, 3600 - (now - earliest_h))
            else:
                wait_rph = 0.0

            wait_time = max(wait_min_delay, wait_rpm, wait_rph)
            if wait_time > 0:
                logger.info(f"Rate limiter: aguardando {wait_time:.1f}s para respeitar limites")
                time.sleep(wait_time)

            # Register call
            now2 = time.time()
            self._last_call_ts = now2
            self._minute_window.append(now2)
            self._hour_window.append(now2)
            return now2

class OpenRouterClient:
    """Cliente protegido do OpenRouter com rate limiting, backoff e monitoramento"""

    def __init__(self):
        self.api_key = Config.get_openrouter_api_key() if Config.OPENROUTER_API_KEY else None
        self.base_url = Config.OPENROUTER_BASE_URL
        self.model = Config.GEMINI_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        self.rate_limiter = OpenRouterRateLimiter()
        self._lock = threading.Lock()

        # Estatísticas
        self.stats = {
            'total_requests': 0,
            'success_requests': 0,
            'failed_requests': 0,
            'last_error': None,
            'avg_latency_ms': 0.0,
            'rolling_latencies_ms': [],  # limitado a 100 últimos
        }

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}' if self.api_key else '',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/boletins-ia',
            'X-Title': 'Boletins IA Generator'
        }

    def chat_completion(self, messages: list, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        """Chama a API /chat/completions de forma protegida"""
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY não configurada. Retornando modo demo.")
            demo_text = "[DEMO] Texto de boletim gerado em modo demonstração por falta de API key."
            return {'status': 'success', 'content': demo_text, 'demo': True}

        max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': False
        }

        retries = 0
        backoff = 10.0

        while retries <= self.rate_limiter.max_retries:
            self.rate_limiter.acquire()
            start = time.time()
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                    timeout=60
                )
                latency_ms = (time.time() - start) * 1000
                self._record_latency(latency_ms)
                self._inc('total_requests')

                # Retry-After header handling
                if resp.status_code in (429, 503):
                    retry_after = resp.headers.get('Retry-After')
                    wait_time = float(retry_after) if retry_after else backoff
                    logger.warning(f"OpenRouter throttle {resp.status_code}. Aguardando {wait_time:.1f}s e tentando novamente...")
                    time.sleep(wait_time)
                    retries += 1
                    backoff = min(backoff * 2, 180.0)
                    continue

                if resp.status_code != 200:
                    self._inc('failed_requests')
                    self.stats['last_error'] = f"{resp.status_code}: {resp.text[:200]}"
                    return {'status': 'error', 'error': self.stats['last_error']}

                data = resp.json()
                content = data['choices'][0]['message']['content']
                self._inc('success_requests')
                return {'status': 'success', 'content': content}

            except requests.RequestException as e:
                self._inc('failed_requests')
                self.stats['last_error'] = str(e)
                logger.error(f"Erro de rede OpenRouter: {e}")
                time.sleep(backoff)
                retries += 1
                backoff = min(backoff * 2, 180.0)
            except Exception as e:
                self._inc('failed_requests')
                self.stats['last_error'] = str(e)
                logger.error(f"Erro inesperado OpenRouter: {e}")
                return {'status': 'error', 'error': str(e)}

        return {'status': 'error', 'error': 'Falha após múltiplas tentativas no OpenRouter'}

    def _inc(self, key: str):
        with self._lock:
            self.stats[key] += 1

    def _record_latency(self, latency_ms: float):
        with self._lock:
            rl = self.stats['rolling_latencies_ms']
            rl.append(latency_ms)
            if len(rl) > 100:
                rl.pop(0)
            self.stats['avg_latency_ms'] = sum(rl) / len(rl)

# Facade simples para uso no generator
class OpenRouterGuard:
    """Facade para proteger chamadas ao OpenRouter no projeto"""

    def __init__(self):
        self.client = OpenRouterClient()

    def generate_text(self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None) -> Dict[str, Any]:
        messages = [{ 'role': 'user', 'content': prompt }]
        return self.client.chat_completion(messages, max_tokens=max_tokens, temperature=temperature)
