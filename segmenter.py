"""
Segmentador de notícias - Fluxo: IA/LLMs → Palavras bloqueadas → Segmentação temática
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from difflib import SequenceMatcher

from config import Config

logger = logging.getLogger(__name__)

class NewsSegmenter:
    """Segmentador baseado em palavras-chave configuradas em Config.SEGMENTS"""
    
    def __init__(self):
        self.segments_config = Config.SEGMENTS
        self.blocked = [k.lower() for k in Config.BLOCKED_KEYWORDS]
        self.ai_keywords = [k.lower() for k in Config.AI_KEYWORDS]
        # Pesos e parâmetros do ranking
        self.weights = {
            'ia': 0.35,
            'segment': 0.35,
            'fresh': 0.15,
            'source': 0.10,
        }
        self.domain_caps = 4  # máximo por domínio inicialmente
        self.similarity_threshold = 0.9  # similaridade de título para descartar
        self.source_score = {
            'g1.globo.com': 0.9,
            'www.uol.com.br': 0.8,
            'economia.uol.com.br': 0.8,
            'www1.folha.uol.com.br': 0.9,
            'www.estadao.com.br': 0.85,
            'www.cnnbrasil.com.br': 0.8,
            'www.tecmundo.com.br': 0.8,
            'canaltech.com.br': 0.8,
            'exame.com': 0.85,
            'olhardigital.com.br': 0.75,
        }
    
    def segment_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            logger.info(f"Iniciando segmentação de {len(articles)} itens")
            # 1) filtro IA
            ai_filtered = [a for a in articles if self._is_ai_related(a)]
            # 2) bloqueados
            clean = [a for a in ai_filtered if not self._has_blocked(a)]
            # 3) segmentação
            segmented = { key: [] for key in self.segments_config.keys() }
            segmented['outros'] = []
            for a in clean:
                best_key, best_score = self._best_segment(a)
                if best_score > 0.0:
                    segmented[best_key].append(a)
                else:
                    segmented['outros'].append(a)

            # 4) ranking e seleção Top 15 por segmento real
            selection_by_segment = {}
            for seg_key in self.segments_config.keys():
                ranked = self._rank_segment(seg_key, segmented.get(seg_key, []))
                selection_by_segment[seg_key] = ranked[:Config.MAX_ARTICLES_PER_SEGMENT]

            stats = {
                'total_articles': len(articles),
                'ai_filtered': len(ai_filtered),
                'filtered_articles': len(clean),
                'segments_stats': {k: len(v) for k, v in segmented.items()},
                'segmentation_date': datetime.now().isoformat()
            }
            logger.info("Segmentação concluída")
            return {
                'status': 'success',
                'segmented_results': segmented,
                'selection_by_segment': selection_by_segment,
                'stats': stats,
                'segmentation_date': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro na segmentação: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'segmented_results': {'outros': articles},
                'selection_by_segment': {},
                'stats': {'total_articles': len(articles)}
            }
    
    # ---------- Scoring helpers ----------
    def _text(self, a: Dict[str, Any]) -> str:
        parts = [a.get('title',''), a.get('summary',''), a.get('content','')]
        return (' '.join([p for p in parts if p])).lower()
    
    def _is_ai_related(self, a: Dict[str, Any]) -> bool:
        t = self._text(a)
        return any(k in t for k in self.ai_keywords)
    
    def _has_blocked(self, a: Dict[str, Any]) -> bool:
        t = self._text(a)
        return any(b in t for b in self.blocked)
    
    def _best_segment(self, a: Dict[str, Any]) -> Tuple[str, float]:
        t_title = (a.get('title') or '').lower()
        t_summary = (a.get('summary') or '').lower()
        t_content = (a.get('content') or '').lower()
        best_key = None
        best_score = 0.0
        for key, cfg in self.segments_config.items():
            kws = [k.lower() for k in cfg.get('keywords', [])]
            # título vale 2, resumo 1, conteúdo 0.5
            hits = 0.0
            for k in kws:
                if k in t_title:
                    hits += 2.0
                if k in t_summary:
                    hits += 1.0
                if k in t_content:
                    hits += 0.5
            denom = max(1.0, 2.0*len(kws) + 1.0*len(kws) + 0.5*len(kws))
            score = hits / denom
            if score > best_score:
                best_key, best_score = key, score
        return best_key or 'outros', best_score
    
    def _score_ia(self, a: Dict[str, Any]) -> float:
        t_title = (a.get('title') or '').lower()
        t_summary = (a.get('summary') or '').lower()
        t_content = (a.get('content') or '').lower()
        hits = 0.0
        for k in self.ai_keywords:
            if k in t_title:
                hits += 2.0
            if k in t_summary:
                hits += 1.0
            if k in t_content:
                hits += 0.5
        denom = max(1.0, 2.0*len(self.ai_keywords) + 1.0*len(self.ai_keywords) + 0.5*len(self.ai_keywords))
        return min(1.0, hits / denom)
    
    def _score_segment(self, seg_key: str, a: Dict[str, Any]) -> float:
        cfg = self.segments_config.get(seg_key, {})
        kws = [k.lower() for k in cfg.get('keywords', [])]
        t_title = (a.get('title') or '').lower()
        t_summary = (a.get('summary') or '').lower()
        t_content = (a.get('content') or '').lower()
        hits = 0.0
        for k in kws:
            if k in t_title:
                hits += 2.0
            if k in t_summary:
                hits += 1.0
            if k in t_content:
                hits += 0.5
        denom = max(1.0, 2.0*len(kws) + 1.0*len(kws) + 0.5*len(kws))
        return min(1.0, hits / denom)
    
    def _score_fresh(self, a: Dict[str, Any]) -> float:
        date_str = a.get('published') or ''
        if not date_str:
            return 0.5
        try:
            # tenta vários formatos
            fmts = [
                '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y'
            ]
            pub = None
            for fmt in fmts:
                try:
                    pub = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            if not pub:
                return 0.5
            days = max(0.0, (datetime.now() - pub).days)
            return max(0.0, 1.0 - min(days / float(Config.DAYS_BACK or 5), 1.0))
        except Exception:
            return 0.5
    
    def _score_source(self, a: Dict[str, Any]) -> float:
        url = a.get('url') or ''
        host = ''
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower()
        except Exception:
            pass
        return self.source_score.get(host, 0.5)
    
    def _normalize_title(self, title: str) -> str:
        t = (title or '').casefold()
        t = re.sub(r"[\W_]+", " ", t, flags=re.UNICODE)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    
    def _rank_segment(self, seg_key: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return []
        # calcula score base
        scored = []
        for a in items:
            s_ia = self._score_ia(a)
            s_seg = self._score_segment(seg_key, a)
            s_fr = self._score_fresh(a)
            s_src = self._score_source(a)
            s_base = (self.weights['ia']*s_ia +
                      self.weights['segment']*s_seg +
                      self.weights['fresh']*s_fr +
                      self.weights['source']*s_src)
            scored.append((s_base, a))
        # ordena por score desc
        scored.sort(key=lambda x: x[0], reverse=True)
        # seleção com diversidade de domínio e de título
        selected: List[Dict[str, Any]] = []
        domain_count: Dict[str, int] = {}
        seen_titles: List[str] = []
        for s, a in scored:
            # similaridade por título
            nt = self._normalize_title(a.get('title',''))
            is_dup = False
            for prev in seen_titles:
                if len(nt) > 20 and len(prev) > 20 and SequenceMatcher(None, nt, prev).ratio() >= self.similarity_threshold:
                    is_dup = True
                    break
            if is_dup:
                continue
            # cap por domínio + penalização progressiva
            host = ''
            try:
                from urllib.parse import urlparse
                host = urlparse(a.get('url','')).netloc.lower()
            except Exception:
                pass
            cnt = domain_count.get(host, 0)
            if cnt >= self.domain_caps:
                # tenta guardar para relaxar depois se precisar
                continue
            domain_count[host] = cnt + 1
            seen_titles.append(nt)
            selected.append(a)
            if len(selected) >= Config.MAX_ARTICLES_PER_SEGMENT:
                break
        # se não atingiu 15, relaxa cap e preenche
        if len(selected) < Config.MAX_ARTICLES_PER_SEGMENT:
            for s, a in scored:
                if a in selected:
                    continue
                nt = self._normalize_title(a.get('title',''))
                dup = False
                for prev in seen_titles:
                    if len(nt) > 20 and len(prev) > 20 and SequenceMatcher(None, nt, prev).ratio() >= self.similarity_threshold:
                        dup = True
                        break
                if dup:
                    continue
                selected.append(a)
                seen_titles.append(nt)
                if len(selected) >= Config.MAX_ARTICLES_PER_SEGMENT:
                    break
        return selected
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        try:
            if not filename:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{Config.OUTPUT_DIR}/segmentation_{ts}.json"
            save_data = {
                'segmentation_date': results.get('segmentation_date', datetime.now().isoformat()),
                'status': results.get('status', 'unknown'),
                'stats': results.get('stats', {}),
                'segmented_results': results.get('segmented_results', {}),
                'selection_by_segment': results.get('selection_by_segment', {}),
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            latest = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
            with open(latest, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            # também salva seleção dedicada
            latest_sel = f"{Config.OUTPUT_DIR}/latest_selection.json"
            with open(latest_sel, 'w', encoding='utf-8') as f:
                json.dump({
                    'selection_by_segment': save_data['selection_by_segment'],
                    'timestamp': save_data['timestamp']
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Resultados da segmentação salvos em: {filename}")
        except Exception as e:
            logger.error(f"Erro ao salvar segmentação: {e}")

def main():
    print("SEGMENTADOR")
    import os
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/segmenter.log'),
            logging.StreamHandler()
        ]
    )
    Config.create_directories()
    try:
        latest_file = f"{Config.OUTPUT_DIR}/latest_collection.json"
        if not os.path.exists(latest_file):
            print("❌ Nenhum dado de coleta encontrado.")
            return
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        articles = data.get('articles', [])
        seg = NewsSegmenter()
        res = seg.segment_articles(articles)
        if res['status'] == 'success':
            seg.save_results(res)
            print("✅ Segmentação ok")
        else:
            print(f"❌ Erro: {res.get('error')}")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
