"""
Coletor de scraping leve (requests + BeautifulSoup) para sites brasileiros
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

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

    def _extract_articles_from_html(self, html: str, source_name: str, page_url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        # Seletores genéricos razoáveis
        candidates = soup.select('article a, .post a, .news-item a, h2 a, h3 a')
        articles: List[Dict[str, Any]] = []
        seen = set()
        for a in candidates[:80]:
            try:
                href = a.get('href')
                title = a.get_text(strip=True)
                if not href or not title or len(title) < 8:
                    continue
                # normaliza url
                full = urljoin(page_url, href)
                if full in seen:
                    continue
                seen.add(full)
                # filtro IA
                low = title.lower()
                if any(k.lower() in low for k in Config.AI_KEYWORDS):
                    content = self.extractor.get_full_text(full)
                    articles.append({
                        'title': title,
                        'url': full,
                        'summary': '',
                        'source': source_name,
                        'published': '',
                        'collected_at': datetime.now().isoformat(),
                        'base_url': page_url,
                        'method': 'scraping',
                        'content': content or ''
                    })
            except Exception:
                continue
        return articles

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    c = WebScrapingCollector()
    r = c.collect_articles()
    print(f"Artigos: {len(r['articles'])}")
