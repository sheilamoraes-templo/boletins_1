"""
Segmentador de notícias - Fluxo: IA/LLMs → Palavras bloqueadas → Segmentação temática
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from config import Config

logger = logging.getLogger(__name__)

class NewsSegmenter:
    """Segmentador baseado em palavras-chave configuradas em Config.SEGMENTS"""
    
    def __init__(self):
        self.segments_config = Config.SEGMENTS
        self.blocked = [k.lower() for k in Config.BLOCKED_KEYWORDS]
        self.ai_keywords = [k.lower() for k in Config.AI_KEYWORDS]
    
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
                'stats': stats,
                'segmentation_date': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erro na segmentação: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'segmented_results': {'outros': articles},
                'stats': {'total_articles': len(articles)}
            }
    
    def _text(self, a: Dict[str, Any]) -> str:
        parts = [a.get('title',''), a.get('summary',''), a.get('content','')]
        return (' '.join([p for p in parts if p])).lower()
    
    def _is_ai_related(self, a: Dict[str, Any]) -> bool:
        t = self._text(a)
        return any(k in t for k in self.ai_keywords)
    
    def _has_blocked(self, a: Dict[str, Any]) -> bool:
        t = self._text(a)
        return any(b in t for b in self.blocked)
    
    def _best_segment(self, a: Dict[str, Any]) -> (str, float):
        t = self._text(a)
        best_key = None
        best_score = 0.0
        for key, cfg in self.segments_config.items():
            kws = [k.lower() for k in cfg.get('keywords', [])]
            hits = sum(1 for k in kws if k in t)
            score = hits / max(1, len(kws))
            if score > best_score:
                best_key, best_score = key, score
        return best_key or 'outros', best_score
    
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
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            latest = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
            with open(latest, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
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
