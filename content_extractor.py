"""
Extrator de conteúdo completo de notícias com heurísticas simples
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import re

import requests
from bs4 import BeautifulSoup

from config import Config
from cache_manager import CacheManager

logger = logging.getLogger(__name__)

class FullContentExtractor:
    """Extrai o texto principal da página de notícia"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.cache = CacheManager()

    def get_full_text(self, url: str) -> Optional[str]:
        """Retorna o texto completo, usando cache quando disponível"""
        try:
            # Cache por URL
            cached = self.cache.get_cache('analysis', key=url)
            if cached and cached.get('text'):
                return cached['text']

            html = self._fetch(url)
            if not html:
                return None

            text = self._extract_main_text(html)
            if text:
                self.cache.set_cache('analysis', {'text': text, 'url': url}, key=url)
            return text
        except Exception as e:
            logger.debug(f"Falha ao obter texto completo de {url}: {e}")
            return None

    def _fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            if resp.status_code == 200 and resp.text:
                return resp.text
            return None
        except Exception as e:
            logger.debug(f"Erro HTTP em {url}: {e}")
            return None

    def _extract_main_text(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')

        # Remove elementos ruidosos
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()

        # Heurística: buscar contêineres de artigo
        candidates = [
            'article', '.article', '.content', '.post', '.news-content', '.materia', '.noticia',
            '.story-body', '.entry-content', '#content', '.g1-core-content'
        ]
        blocks = []
        for sel in candidates:
            blocks.extend(soup.select(sel))

        def clean_text(node) -> str:
            paragraphs = node.find_all(['p', 'h2', 'li'])
            texts = []
            for p in paragraphs:
                t = p.get_text(" ", strip=True)
                if t and len(t) > 40:
                    texts.append(t)
            return "\n\n".join(texts)

        best = ""
        if blocks:
            # Seleciona o bloco com mais texto
            scored = [(len(clean_text(b)), b) for b in blocks]
            scored.sort(key=lambda x: x[0], reverse=True)
            best = clean_text(scored[0][1])
        else:
            # Fallback: todos <p>
            best = clean_text(soup)

        # Sanitização final
        best = re.sub(r"\n{3,}", "\n\n", best or "").strip()
        return best if best and len(best) > 200 else None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    e = FullContentExtractor()
    print(e.get_full_text('https://example.com'))
