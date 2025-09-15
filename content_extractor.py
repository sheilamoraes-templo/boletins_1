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

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
except Exception:
    webdriver = None

class FullContentExtractor:
    """Extrai o texto principal da página de notícia"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.cache = CacheManager()
        self.domain_selectors = {
            'g1.globo.com': ['article', '.mc-column', '.content-text', '.materia-conteudo', '.core-main__content'],
            'www.uol.com.br': ['article', '.c-list__item', '.news', '.text'],
            'www1.folha.uol.com.br': ['article', '.c-news__body', '.content', '.content-text'],
            'www.estadao.com.br': ['article', '.materia', '.noticia', '.content', '.content-body'],
            'www.cnnbrasil.com.br': ['article', '.article__content', '.post-content'],
            'www.tecmundo.com.br': ['article', '.tec--article__body', '.content'],
            'exame.com': ['article', '.content', '.article-content', '.content__body'],
            'canaltech.com.br': ['article', '.content', '.article-content'],
            'ainews.net.br': ['article', '.entry-content', '.single-content', '.post-content'],
            'tiinside.com.br': ['article', '.td-post-content', '.tdb_single_content', '.entry-content'],
            'www.bbc.com': ['article', 'main', '.ssrcss-uf6wea-RichTextComponentWrapper', '.ssrcss-1q0x1qg-Paragraph']
        }
        self.selenium_pages_used = 0
        self._driver = None

    def _get_driver(self):
        if not Config.USE_SELENIUM or webdriver is None:
            return None
        if self._driver:
            return self._driver
        try:
            opts = ChromeOptions()
            opts.add_argument('--headless=new')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-gpu')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--window-size=1920,1080')
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            self._driver = driver
            return driver
        except Exception as e:
            logger.warning(f"Falha ao iniciar Selenium: {e}")
            return None

    def get_full_text(self, url: str) -> Optional[str]:
        try:
            cached = self.cache.get_cache('analysis', key=url)
            if cached and cached.get('text'):
                return cached['text']

            html = self._fetch(url)
            text = None
            if html:
                text = self._extract_main_text(url, html)

            # fallback Selenium
            if (not text or len(text) < 200) and self._can_use_selenium(url):
                text = self._fetch_with_selenium(url)

            if text:
                self.cache.set_cache('analysis', {'text': text, 'url': url}, key=url)
            return text
        except Exception as e:
            logger.debug(f"Falha ao obter texto completo de {url}: {e}")
            return None

    def _can_use_selenium(self, url: str) -> bool:
        if not Config.USE_SELENIUM:
            return False
        if self.selenium_pages_used >= Config.SELENIUM_MAX_PAGES:
            return False
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower()
            return host in Config.SELENIUM_DOMAINS
        except Exception:
            return False

    def _fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            if resp.status_code == 200 and resp.text:
                return resp.text
            return None
        except Exception as e:
            logger.debug(f"Erro HTTP em {url}: {e}")
            return None

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        try:
            driver = self._get_driver()
            if not driver:
                return None
            driver.set_page_load_timeout(Config.SELENIUM_TIMEOUT)
            driver.get(url)
            # tentar aparecer main article por seletor
            selectors = self._selectors_for(url)
            try:
                WebDriverWait(driver, Config.SELENIUM_TIMEOUT).until(
                    EC.presence_of_any_elements_located((By.CSS_SELECTOR, ','.join(selectors)))
                )
            except Exception:
                pass
            html = driver.page_source
            self.selenium_pages_used += 1
            return self._extract_main_text(url, html)
        except Exception as e:
            logger.debug(f"Selenium falhou em {url}: {e}")
            return None

    def _selectors_for(self, url: str):
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower()
            return self.domain_selectors.get(host, ['article'])
        except Exception:
            return ['article']

    def _extract_main_text(self, url: str, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()

        host = ''
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower()
        except Exception:
            pass

        selectors = self.domain_selectors.get(host, [])
        if not selectors:
            selectors = ['article', '.article', '.content', '.post', '.news-content', '.materia', '.noticia', '.entry-content', '#content']

        blocks = []
        for sel in selectors:
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
            scored = [(len(clean_text(b)), b) for b in blocks]
            scored.sort(key=lambda x: x[0], reverse=True)
            best = clean_text(scored[0][1])
        else:
            best = clean_text(soup)

        best = re.sub(r"\n{3,}", "\n\n", best or "").strip()
        return best if best and len(best) > 200 else None

    def __del__(self):
        try:
            if self._driver:
                self._driver.quit()
        except Exception:
            pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    e = FullContentExtractor()
    print(e.get_full_text('https://example.com'))
