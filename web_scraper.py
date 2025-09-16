"""
Coletor de scraping leve (requests + BeautifulSoup) para sites brasileiros
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re

import requests
from bs4 import BeautifulSoup

from config import Config
from content_extractor import FullContentExtractor

logger = logging.getLogger(__name__)

class WebScrapingCollector:
    """Scraper leve para fontes sem Selenium"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        })
        self.extractor = FullContentExtractor()
        # regras por domínio (regex de notícia)
        self.domain_allow = {
            'g1.globo.com': re.compile(r"/(tecnologia|economia|ciencia|ciencia-e-saude|noticia)/", re.I),
            'www.uol.com.br': re.compile(r"/(tilt|economia)/", re.I),
            'exame.com': re.compile(r"/(tecnologia|negocios)/", re.I),
            'canaltech.com.br': re.compile(r"/(inteligencia-artificial|tecnologia|ciencia)/", re.I),
            'ainews.net.br': re.compile(r"/(inteligencia-artificial|artigos)/", re.I),
            'tiinside.com.br': re.compile(r"/(top-news|inteligencia-artificial)/", re.I),
            'www.bbc.com': re.compile(r"/portuguese/", re.I),
            'www.infomoney.com.br': re.compile(r"/", re.I),
            'iaexpert.academy': re.compile(r"/", re.I),
            'gauchazh.clicrbs.com.br': re.compile(r"/", re.I),
            'neofeed.com.br': re.compile(r"/", re.I),
            'www.cnnbrasil.com.br': re.compile(r"/tecnologia/|/tecnologia/.*", re.I),
            'itforum.com.br': re.compile(r"/noticias/|/noticia/", re.I),
            'forbes.com.br': re.compile(r"/noticias-sobre/ia/|/forbes-tech/|/tecnologia/", re.I),
        }
        self.block_paths = re.compile(r"/(tag|topics|maispopulares|folha-topicos|page|live|flash|ao-vivo|video|videos|podcast|webstories|guia|oferta|ofertas|podcasts|videos|elementor-action)/", re.I)
        self.ai_terms = [k.lower() for k in Config.AI_KEYWORDS]
        self.block_terms = [k.lower() for k in Config.BLOCKED_KEYWORDS]

    def collect_articles(self, days_back: int = 5, max_articles_per_source: int = 50) -> Dict[str, Any]:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        all_articles: List[Dict[str, Any]] = []
        sources_stats: Dict[str, Any] = {}

        for source_name, cfg in Config.SCRAPING_SOURCES.items():
            try:
                source_articles = []
                for section in cfg['sections']:
                    url = urljoin(cfg['base_url'], section)
                    html = self._fetch(url)
                    if not html:
                        continue
                    page_articles = self._extract_articles_from_html(html, source_name, url)
                    source_articles.extend(page_articles)
                    time.sleep(0.5)

                # Dedup e limite
                seen = set()
                dedup = []
                for a in source_articles:
                    u = a.get('url')
                    if u and u not in seen:
                        seen.add(u)
                        dedup.append(a)
                source_articles = dedup[:max_articles_per_source]

                all_articles.extend(source_articles)
                sources_stats[source_name] = {
                    'sections': len(cfg['sections']),
                    'total_articles': len(source_articles)
                }
                logger.info(f"{source_name}: {len(source_articles)} artigos")
            except Exception as e:
                logger.error(f"Erro em {source_name}: {e}")
                sources_stats[source_name] = {
                    'sections': len(cfg.get('sections', [])),
                    'total_articles': 0,
                    'error': str(e)
                }

        return {
            'status': 'success',
            'articles': all_articles,
            'stats': {
                'sources_stats': sources_stats,
                'total_articles': len(all_articles),
                'ai_articles': len(all_articles)
            },
            'collection_date': datetime.now().isoformat(),
            'sources_processed': list(Config.SCRAPING_SOURCES.keys())
        }

    def _fetch(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            if resp.status_code == 200 and resp.text:
                return resp.text
            return None
        except Exception as e:
            logger.debug(f"Falha ao buscar {url}: {e}")
            return None

    def _is_news_url(self, url: str) -> bool:
        try:
            host = urlparse(url).netloc.lower()
            path = urlparse(url).path.lower()
            if self.block_paths.search(path):
                return False
            # especificidades por domínio
            if 'tiinside.com.br' in host:
                if not re.search(r"/top-news/", path):
                    return False
                if re.search(r"/(featured|popular|popular7|review_high)/", path):
                    return False
            if 'ainews.net.br' in host:
                if not re.search(r"/(c/artigos/|/inteligencia-artificial/)", path):
                    return False
            pattern = self.domain_allow.get(host)
            return bool((pattern and pattern.search(path)) or 'tiinside.com.br' in host or 'ainews.net.br' in host)
        except Exception:
            return False

    def _text_has_ai_strict(self, title: str, content: Optional[str]) -> bool:
        title_l = (title or '').lower()
        content_l = (content or '').lower()
        # corta para os 2 primeiros parágrafos
        first_pars = '\n'.join((content_l.split('\n\n')[:2])) if content_l else ''
        return any(k in title_l for k in self.ai_terms) or any(k in first_pars for k in self.ai_terms)

    def _text_has_ai(self, title: str, content: Optional[str]) -> bool:
        # mantém função antiga para possíveis usos, mas passa a usar a strict
        return self._text_has_ai_strict(title, content)

    def _text_has_blocked(self, title: str, content: Optional[str]) -> bool:
        t = (title or '').lower() + ' ' + (content or '').lower()
        return any(k in t for k in self.block_terms)

    def _extract_articles_from_html(self, html: str, source_name: str, page_url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        try:
            host = urlparse(page_url).netloc.lower()
            path = urlparse(page_url).path.lower()
        except Exception:
            host = ''
            path = ''

        # Seleção base
        candidates = soup.select('article a, .post a, .news-item a, h2 a, h3 a, a[href]')
        # Ajuste por domínio (melhor assertividade)
        try:
            if 'tiinside.com.br' in host:
                domain_specific = soup.select('.td-module-title a, h3.entry-title a, article .entry-title a')
                if domain_specific:
                    candidates = domain_specific
            if 'g1.globo.com' in host:
                domain_specific = soup.select('a.feed-post-link, .feed-post-body-title a, h2 a')
                if domain_specific:
                    candidates = domain_specific
            
        except Exception:
            pass
        articles: List[Dict[str, Any]] = []
        seen = set()
        for a in candidates[:300]:
            try:
                href = a.get('href')
                title = a.get_text(strip=True)
                if not href:
                    continue
                full = urljoin(page_url, href)
                if full in seen:
                    continue
                seen.add(full)
                if not self._is_news_url(full):
                    continue
                # título: preferir H1/og:title, nunca body content
                h1_title = self._fetch_title_from_page(full)
                if h1_title and len(h1_title) >= 8:
                    title = h1_title
                if not title or len(title) < 8:
                    continue
                content = self.extractor.get_full_text(full)
                # IA primeiro
                if Config.COLLECT_IA_ONLY and not self._text_has_ai(title, content):
                    continue
                # Bloqueados
                if self._text_has_blocked(title, content):
                    continue
                if not content or len(content) < 200:
                    continue
                articles.append({
                    'title': title,
                    'url': full,
                    'summary': '',
                    'source': source_name,
                    'published': '',
                    'collected_at': datetime.now().isoformat(),
                    'base_url': page_url,
                    'method': 'scraping',
                    'content': content
                })
            except Exception:
                continue
        return articles

    def _fetch_title_from_page(self, url: str) -> Optional[str]:
        try:
            html = self._fetch(url)
            if not html:
                return None
            soup = BeautifulSoup(html, 'html.parser')
            # 1) og:title / twitter:title
            meta = soup.select_one('meta[property="og:title"][content]') or soup.select_one('meta[name="twitter:title"][content]')
            if meta:
                mt = meta.get('content')
                if mt and 8 <= len(mt) <= 220:
                    return mt.strip()
            # 2) h1 puro
            h1 = soup.find('h1')
            if h1:
                t = h1.get_text(strip=True)
                if t and 8 <= len(t) <= 220:
                    return t
            return None
        except Exception:
            return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    c = WebScrapingCollector()
    r = c.collect_articles()
    print(f"Artigos: {len(r['articles'])}")
