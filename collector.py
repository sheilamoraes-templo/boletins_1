"""
Coletor híbrido: RSS + Scraping leve (sites brasileiros)
"""

import feedparser
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json
from difflib import SequenceMatcher

from config import Config
from web_scraper import WebScrapingCollector
from content_extractor import FullContentExtractor

logger = logging.getLogger(__name__)

class NewsCollector:
    """Coletor híbrido para notícias sobre IA"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.scraper = WebScrapingCollector()
        self.extractor = FullContentExtractor()
        
        # Estatísticas
        self.stats = {
            'total_feeds_tested': 0,
            'successful_feeds': 0,
            'total_articles': 0,
            'ai_articles': 0,
            'sources_stats': {},
            'collection_time': 0,
            'scraping_articles': 0,
            'rss_articles': 0,
            'duplicates_removed_url': 0,
            'duplicates_removed_title': 0
        }
    
    def collect_articles(self, days_back: int = None, max_articles_per_source: int = None) -> Dict[str, Any]:
        """Coleta artigos via RSS e scraping leve"""
        try:
            logger.info("INICIANDO COLETA DE NOTÍCIAS (HÍBRIDO)")
            logger.info("="*50)
            
            # Usa configurações padrão se não especificado
            days_back = days_back or Config.DAYS_BACK
            max_articles_per_source = max_articles_per_source or Config.MAX_ARTICLES_PER_SOURCE
            
            logger.info(f"Período: últimos {days_back} dias")
            logger.info(f"Máximo por fonte: {max_articles_per_source} artigos")
            logger.info(f"Fontes RSS: {len(Config.NEWS_SOURCES)} | Fontes scraping: {len(Config.SCRAPING_SOURCES)}")
            
            start_time = time.time()
            all_articles: List[Dict[str, Any]] = []
            sources_processed = []
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # 1) RSS
            rss_articles = self._collect_rss(cutoff_date, max_articles_per_source)
            self.stats['rss_articles'] = len(rss_articles)
            all_articles.extend(rss_articles)
            
            # 2) Scraping leve
            scraping_result = self.scraper.collect_articles(days_back=days_back, max_articles_per_source=max_articles_per_source)
            if scraping_result.get('status') == 'success':
                scraping_articles = scraping_result.get('articles', [])
                self.stats['scraping_articles'] = len(scraping_articles)
                all_articles.extend(scraping_articles)
                sources_processed.extend(scraping_result.get('sources_processed', []))
            
            # Remoção de duplicatas por URL e por título
            before = len(all_articles)
            dedup_url = self._remove_duplicates_by_url(all_articles)
            self.stats['duplicates_removed_url'] = before - len(dedup_url)
            dedup_title = self._remove_duplicates_by_title(dedup_url)
            self.stats['duplicates_removed_title'] = len(dedup_url) - len(dedup_title)
            unique_articles = dedup_title
            
            # Relatório por fonte (contagem + títulos e URLs)
            report_by_source: Dict[str, Dict[str, Any]] = {}
            for a in unique_articles:
                src = a.get('source', 'Desconhecida')
                if src not in report_by_source:
                    report_by_source[src] = {'count': 0, 'articles': []}
                report_by_source[src]['count'] += 1
                report_by_source[src]['articles'].append({
                    'title': a.get('title', ''),
                    'url': a.get('url', '')
                })
            
            # Atualiza estatísticas
            collection_time = time.time() - start_time
            self.stats.update({
                'total_articles': len(unique_articles),
                'ai_articles': len(unique_articles),
                'collection_time': round(collection_time, 2),
                'successful_feeds': len(Config.NEWS_SOURCES),
                'total_feeds_tested': len(Config.NEWS_SOURCES)
            })
            
            self._print_final_report()
            
            return {
                'status': 'success',
                'articles': unique_articles,
                'stats': self.stats,
                'report_by_source': report_by_source,
                'sources_processed': sources_processed,
                'collection_date': datetime.now().isoformat(),
                'total_sources': len(sources_processed) + len(Config.NEWS_SOURCES)
            }
            
        except Exception as e:
            logger.error(f"Erro na coleta híbrida: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'articles': [],
                'stats': self.stats
            }
    
    def _collect_rss(self, cutoff_date: datetime, max_articles_per_source: int) -> List[Dict[str, Any]]:
        articles: List[Dict[str, Any]] = []
        for source_name, source_config in Config.NEWS_SOURCES.items():
            try:
                logger.info(f"\nProcessando fonte RSS: {source_name}")
                for feed_url in source_config['rss_feeds']:
                    logger.info(f"  Feed: {feed_url}")
                    feed = feedparser.parse(feed_url)
                    if feed.bozo:
                        logger.warning(f"  Feed com problemas: {feed_url}")
                        continue
                    for entry in feed.entries[:max_articles_per_source]:
                        try:
                            article = self._process_entry(entry, source_name, source_config['base_url'])
                            if article and self._is_ai_related(article):
                                article_date = self._parse_date(article.get('published', ''))
                                if not article_date or article_date >= cutoff_date:
                                    # extrai texto completo e adiciona em 'content'
                                    full_text = self.extractor.get_full_text(article['url'])
                                    if full_text:
                                        article['content'] = full_text
                                    articles.append(article)
                        except Exception as e:
                            logger.debug(f"  Erro em entrada: {e}")
                            continue
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Erro na fonte {source_name}: {e}")
                continue
        return articles
    
    def _process_entry(self, entry, source_name: str, base_url: str) -> Optional[Dict]:
        try:
            title = entry.get('title', '').strip()
            link = entry.get('link', '')
            summary = entry.get('summary', '') or entry.get('description', '')
            published = entry.get('published', '')
            if not title or not link:
                return None
            if summary:
                soup = BeautifulSoup(summary, 'html.parser')
                summary = soup.get_text().strip()
            if not self._is_valid_url(link):
                return None
            return {
                'title': title,
                'url': link,
                'summary': summary,
                'source': source_name,
                'published': published,
                'collected_at': datetime.now().isoformat(),
                'base_url': base_url,
                'method': 'rss'
            }
        except Exception:
            return None
    
    def _is_ai_related(self, article: Dict) -> bool:
        text_to_check = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        for keyword in Config.AI_KEYWORDS:
            if keyword.lower() in text_to_check:
                return True
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            if not date_str:
                return None
            fmts = [
                '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'
            ]
            for fmt in fmts:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            import feedparser as fp
            parsed = fp._parse_date(date_str)
            return datetime(*parsed[:6]) if parsed else None
        except Exception:
            return None
    
    def _normalize_title(self, title: str) -> str:
        """Normaliza o título para comparação (casefold, remove pontuação e espaços extras)."""
        if not title:
            return ''
        t = title.casefold()
        t = re.sub(r"[\W_]+", " ", t, flags=re.UNICODE)  # remove pontuação
        t = re.sub(r"\s+", " ", t).strip()
        return t
    
    def _remove_duplicates_by_url(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        unique: List[Dict] = []
        for a in articles:
            u = a.get('url', '')
            if u and u not in seen_urls:
                seen_urls.add(u)
                unique.append(a)
        return unique
    
    def _remove_duplicates_by_title(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicatas com base no título normalizado e similaridade alta (>= 0.9)."""
        unique: List[Dict[str, Any]] = []
        normalized_seen: List[str] = []
        for a in articles:
            title = a.get('title', '')
            nt = self._normalize_title(title)
            if not nt:
                unique.append(a)
                continue
            is_dup = False
            # checagem rápida por igualdade exata
            if nt in normalized_seen:
                is_dup = True
            else:
                # checagem aproximada leve
                for prev in normalized_seen:
                    if len(nt) > 20 and len(prev) > 20:
                        if SequenceMatcher(None, nt, prev).ratio() >= 0.9:
                            is_dup = True
                            break
            if not is_dup:
                normalized_seen.append(nt)
                unique.append(a)
        return unique
    
    def _print_final_report(self):
        logger.info("\n" + "="*60)
        logger.info("RELATÓRIO FINAL DA COLETA (HÍBRIDO)")
        logger.info("="*60)
        logger.info(f"Tempo total: {self.stats['collection_time']}s")
        logger.info(f"RSS: {self.stats['rss_articles']} | Scraping: {self.stats['scraping_articles']}")
        logger.info(f"Removidos (URL): {self.stats['duplicates_removed_url']} | Removidos (título): {self.stats['duplicates_removed_title']}")
        logger.info(f"Total de artigos de IA: {self.stats['ai_articles']}")
        logger.info("="*60)

    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Salva resultados em arquivo JSON"""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{Config.OUTPUT_DIR}/collection_{timestamp}.json"
            
            # Prepara dados para salvar
            save_data = {
                'collection_date': results.get('collection_date', datetime.now().isoformat()),
                'status': results.get('status', 'unknown'),
                'stats': results.get('stats', {}),
                'report_by_source': results.get('report_by_source', {}),
                'sources_processed': results.get('sources_processed', []),
                'total_sources': results.get('total_sources', 0),
                'articles': results.get('articles', []),
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Resultados salvos em: {filename}")
            
            # Também salva como 'latest' para o pipeline
            latest_filename = f"{Config.OUTPUT_DIR}/latest_collection.json"
            with open(latest_filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Resultados também salvos como: {latest_filename}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {e}")

    def _passes_ia_and_blocked_filters(self, item: dict) -> bool:
        from config import Config
        ai_terms = [k.lower() for k in Config.AI_KEYWORDS]
        blocked = [k.lower() for k in Config.BLOCKED_KEYWORDS]
        text = ' '.join([item.get('title',''), item.get('summary',''), item.get('content','')]).lower()
        if Config.COLLECT_IA_ONLY and not any(k in text for k in ai_terms):
            return False
        if any(b in text for b in blocked):
            return False
        return True

    def _postprocess_items(self, items: list) -> list:
        cleaned = []
        seen_urls = set()
        seen_titles = set()
        for it in items:
            if not self._passes_ia_and_blocked_filters(it):
                continue
            url = it.get('url')
            title = (it.get('title') or '').strip()
            if not url or not title:
                continue
            if url in seen_urls:
                continue
            norm_title = self._normalize_title(title)
            if norm_title in seen_titles:
                continue
            seen_urls.add(url)
            seen_titles.add(norm_title)
            cleaned.append(it)
        return cleaned

def main():
    """Função principal para testar o coletor"""
    print("COLETOR DE NOTÍCIAS IA")
    print("="*50)
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/collector.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria diretórios necessários
    Config.create_directories()
    
    # Valida configuração
    if not Config.validate_config(require_api=False):
        print("❌ Configuração inválida. Verifique as variáveis de ambiente.")
        return
    
    try:
        collector = NewsCollector()
        results = collector.collect_articles()
        
        if results['status'] == 'success':
            print(f"\n✅ COLETA CONCLUÍDA COM SUCESSO!")
            print(f"Total de artigos: {results['stats']['ai_articles']}")
            print(f"Fontes processadas: {results['total_sources']}")
            print(f"Tempo: {results['stats']['collection_time']}s")
            
            # Salva resultados
            collector.save_results(results)
            
        else:
            print(f"❌ Erro na coleta: {results.get('error', 'Erro desconhecido')}")
    
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")

if __name__ == "__main__":
    main()
