"""
Sistema de cache robusto para evitar reprocessamento
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import hashlib
import time

from config import Config

logger = logging.getLogger(__name__)

class CacheManager:
    """Gerenciador de cache robusto"""
    
    def __init__(self):
        self.cache_dir = Config.CACHE_CONFIG['cache_dir']
        self.enabled = Config.CACHE_CONFIG['enabled']
        self.expiry_hours = Config.CACHE_CONFIG['expiry_hours']
        
        # Cria diretório de cache se não existir
        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_file_path(self, cache_type: str) -> str:
        """Retorna o caminho do arquivo de cache"""
        cache_files = {
            'email_links': Config.CACHE_CONFIG['email_cache_file'],
            'segmentation': Config.CACHE_CONFIG['segmentation_cache_file'],
            'analysis': Config.CACHE_CONFIG['analysis_cache_file']
        }
        
        filename = cache_files.get(cache_type, f'{cache_type}_cache.json')
        return os.path.join(self.cache_dir, filename)
    
    def _generate_cache_key(self, data: Any) -> str:
        """Gera chave única para cache baseada nos dados"""
        try:
            # Converte dados para string e gera hash
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Erro ao gerar chave de cache: {e}")
            return str(hash(str(data)))
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Verifica se o cache ainda é válido"""
        try:
            if not cache_data.get('timestamp'):
                return False
            
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            expiry_time = cache_time + timedelta(hours=self.expiry_hours)
            
            return datetime.now() < expiry_time
        except Exception as e:
            logger.error(f"Erro ao verificar validade do cache: {e}")
            return False
    
    def get_cache(self, cache_type: str, key: str = None) -> Optional[Dict[str, Any]]:
        """Recupera dados do cache"""
        if not self.enabled:
            return None
        
        try:
            cache_file = self._get_cache_file_path(cache_type)
            
            if not os.path.exists(cache_file):
                logger.info(f"Arquivo de cache não encontrado: {cache_file}")
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Se não especificou chave, retorna dados gerais
            if not key:
                if self._is_cache_valid(cache_data):
                    logger.info(f"Cache válido encontrado para {cache_type}")
                    return cache_data
                else:
                    logger.info(f"Cache expirado para {cache_type}")
                    return None
            
            # Busca por chave específica
            if key in cache_data.get('entries', {}):
                entry = cache_data['entries'][key]
                if self._is_cache_valid(entry):
                    logger.info(f"Cache válido encontrado para {cache_type}:{key}")
                    return entry
                else:
                    logger.info(f"Cache expirado para {cache_type}:{key}")
                    return None
            
            logger.info(f"Chave não encontrada no cache: {cache_type}:{key}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao recuperar cache {cache_type}: {e}")
            return None
    
    def set_cache(self, cache_type: str, data: Dict[str, Any], key: str = None) -> bool:
        """Salva dados no cache"""
        if not self.enabled:
            return False
        
        try:
            cache_file = self._get_cache_file_path(cache_type)
            
            # Adiciona timestamp
            data['timestamp'] = datetime.now().isoformat()
            data['cache_type'] = cache_type
            
            if key:
                # Cache com chave específica
                if os.path.exists(cache_file):
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                else:
                    cache_data = {'entries': {}, 'metadata': {}}
                
                cache_data['entries'][key] = data
                cache_data['metadata']['last_updated'] = datetime.now().isoformat()
                cache_data['metadata']['total_entries'] = len(cache_data['entries'])
                
            else:
                # Cache geral
                cache_data = data
            
            # Salva arquivo
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cache salvo com sucesso: {cache_type}" + (f":{key}" if key else ""))
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache {cache_type}: {e}")
            return False
    
    def clear_cache(self, cache_type: str = None) -> bool:
        """Limpa cache específico ou todos"""
        try:
            if cache_type:
                # Limpa cache específico
                cache_file = self._get_cache_file_path(cache_type)
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    logger.info(f"Cache limpo: {cache_type}")
                    return True
            else:
                # Limpa todos os caches
                if os.path.exists(self.cache_dir):
                    for filename in os.listdir(self.cache_dir):
                        if filename.endswith('_cache.json'):
                            file_path = os.path.join(self.cache_dir, filename)
                            os.remove(file_path)
                    logger.info("Todos os caches foram limpos")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        try:
            stats = {
                'enabled': self.enabled,
                'cache_dir': self.cache_dir,
                'expiry_hours': self.expiry_hours,
                'cache_files': {},
                'total_size': 0
            }
            
            if not os.path.exists(self.cache_dir):
                return stats
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('_cache.json'):
                    file_path = os.path.join(self.cache_dir, filename)
                    file_size = os.path.getsize(file_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        cache_type = filename.replace('_cache.json', '')
                        stats['cache_files'][cache_type] = {
                            'filename': filename,
                            'size_bytes': file_size,
                            'size_mb': round(file_size / (1024 * 1024), 2),
                            'entries_count': len(cache_data.get('entries', {})) if 'entries' in cache_data else 1,
                            'last_updated': cache_data.get('metadata', {}).get('last_updated', cache_data.get('timestamp', 'N/A')),
                            'is_valid': self._is_cache_valid(cache_data)
                        }
                        
                        stats['total_size'] += file_size
                        
                    except Exception as e:
                        logger.error(f"Erro ao analisar cache {filename}: {e}")
            
            stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
            return stats
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do cache: {e}")
            return {'error': str(e)}

class TimeoutManager:
    """Gerenciador de timeouts para evitar loops infinitos"""
    
    def __init__(self):
        self.timeouts = {
            'request': Config.REQUEST_TIMEOUT,
            'processing': Config.PROCESSING_TIMEOUT,
            'email_fetch': Config.EMAIL_FETCH_TIMEOUT
        }
        self.active_timeouts = {}
    
    def start_timeout(self, operation: str, timeout_seconds: int = None) -> str:
        """Inicia um timeout para uma operação"""
        timeout_id = f"{operation}_{int(time.time())}"
        timeout_duration = timeout_seconds or self.timeouts.get(operation, 30)
        
        self.active_timeouts[timeout_id] = {
            'operation': operation,
            'start_time': time.time(),
            'timeout_duration': timeout_duration,
            'expiry_time': time.time() + timeout_duration
        }
        
        logger.info(f"Timeout iniciado: {operation} ({timeout_duration}s)")
        return timeout_id
    
    def check_timeout(self, timeout_id: str) -> bool:
        """Verifica se o timeout ainda é válido"""
        if timeout_id not in self.active_timeouts:
            return True
        
        timeout_info = self.active_timeouts[timeout_id]
        current_time = time.time()
        
        if current_time > timeout_info['expiry_time']:
            logger.warning(f"Timeout expirado: {timeout_info['operation']}")
            del self.active_timeouts[timeout_id]
            return False
        
        return True
    
    def end_timeout(self, timeout_id: str) -> float:
        """Finaliza um timeout e retorna o tempo decorrido"""
        if timeout_id not in self.active_timeouts:
            return 0
        
        timeout_info = self.active_timeouts[timeout_id]
        elapsed_time = time.time() - timeout_info['start_time']
        
        logger.info(f"Timeout finalizado: {timeout_info['operation']} ({elapsed_time:.2f}s)")
        del self.active_timeouts[timeout_id]
        
        return elapsed_time
    
    def get_remaining_time(self, timeout_id: str) -> float:
        """Retorna o tempo restante do timeout"""
        if timeout_id not in self.active_timeouts:
            return 0
        
        timeout_info = self.active_timeouts[timeout_id]
        remaining = timeout_info['expiry_time'] - time.time()
        return max(0, remaining)
    
    def cleanup_expired_timeouts(self):
        """Remove timeouts expirados"""
        current_time = time.time()
        expired_ids = []
        
        for timeout_id, timeout_info in self.active_timeouts.items():
            if current_time > timeout_info['expiry_time']:
                expired_ids.append(timeout_id)
        
        for timeout_id in expired_ids:
            logger.warning(f"Removendo timeout expirado: {self.active_timeouts[timeout_id]['operation']}")
            del self.active_timeouts[timeout_id]

def main():
    """Função principal para testar o sistema de cache"""
    print("TESTE DO SISTEMA DE CACHE")
    print("="*40)
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/cache_manager.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria diretórios necessários
    Config.create_directories()
    
    try:
        # Testa cache manager
        cache_manager = CacheManager()
        
        # Testa salvamento
        test_data = {
            'test_key': 'test_value',
            'timestamp': datetime.now().isoformat()
        }
        
        success = cache_manager.set_cache('test', test_data, 'test_key')
        print(f"Salvamento no cache: {'✅ Sucesso' if success else '❌ Erro'}")
        
        # Testa recuperação
        retrieved_data = cache_manager.get_cache('test', 'test_key')
        print(f"Recuperação do cache: {'✅ Sucesso' if retrieved_data else '❌ Erro'}")
        
        if retrieved_data:
            print(f"Dados recuperados: {retrieved_data}")
        
        # Testa estatísticas
        stats = cache_manager.get_cache_stats()
        print(f"Estatísticas do cache: {stats}")
        
        # Testa timeout manager
        timeout_manager = TimeoutManager()
        timeout_id = timeout_manager.start_timeout('test_operation', 5)
        
        print(f"Timeout iniciado: {timeout_id}")
        print(f"Tempo restante: {timeout_manager.get_remaining_time(timeout_id):.2f}s")
        
        # Simula operação
        time.sleep(1)
        
        elapsed = timeout_manager.end_timeout(timeout_id)
        print(f"Operação finalizada em: {elapsed:.2f}s")
        
        print("\n✅ Sistema de cache funcionando corretamente!")
        
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")

if __name__ == "__main__":
    main()
