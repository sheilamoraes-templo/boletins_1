"""
Pipeline principal integrado para coleta, segmentação e geração de boletins
"""

import logging
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from config import Config
from collector import NewsCollector
from segmenter import NewsSegmenter
from generator import BulletinGenerator
from email_sender import EmailSender
from visualizer import start_visualizer

logger = logging.getLogger(__name__)

class BoletinsPipeline:
    """Pipeline principal integrado para geração de boletins"""
    
    def __init__(self):
        self.collector = NewsCollector()
        self.segmenter = NewsSegmenter()
        self.generator = None  # instanciado somente quando necessário
        self.email_sender = EmailSender() if Config.EMAIL_CONFIG['email_user'] else None
        
        # Estatísticas do pipeline
        self.pipeline_stats = {
            'start_time': None,
            'end_time': None,
            'total_time': 0,
            'collection_time': 0,
            'segmentation_time': 0,
            'generation_time': 0,
            'status': 'pending',
            'errors': []
        }
    
    def run_full_pipeline(self, days_back: int = None, max_articles_per_source: int = None) -> Dict[str, Any]:
        """Executa pipeline completo: coleta + segmentação + geração"""
        try:
            logger.info("INICIANDO PIPELINE COMPLETO")
            logger.info("="*60)
            logger.info("Fases: Coleta → Segmentação → Geração de Boletins")
            logger.info("="*60)
            
            self.pipeline_stats['start_time'] = time.time()
            self.pipeline_stats['status'] = 'running'
            
            # Usa configurações padrão se não especificado
            days_back = days_back or Config.DAYS_BACK
            max_articles_per_source = max_articles_per_source or Config.MAX_ARTICLES_PER_SOURCE
            
            logger.info(f"Configurações:")
            logger.info(f"  - Período: últimos {days_back} dias")
            logger.info(f"  - Máximo por fonte: {max_articles_per_source} artigos")
            logger.info(f"  - Segmentos: {list(Config.SEGMENTS.keys())}")
            
            # FASE 1: COLETA
            logger.info(f"\n{'='*20} FASE 1: COLETA {'='*20}")
            collection_start = time.time()
            
            collection_result = self.collector.collect_articles(
                days_back=days_back,
                max_articles_per_source=max_articles_per_source
            )
            
            self.pipeline_stats['collection_time'] = time.time() - collection_start
            
            if collection_result['status'] != 'success':
                error_msg = f"Erro na coleta: {collection_result.get('error', 'Erro desconhecido')}"
                logger.error(error_msg)
                self.pipeline_stats['errors'].append(error_msg)
                return self._create_error_result(error_msg)
            
            articles = collection_result['articles']
            logger.info(f"✅ Coleta concluída: {len(articles)} artigos coletados")
            logger.info(f"⏱️ Tempo de coleta: {self.pipeline_stats['collection_time']:.2f}s")
            
            # Salva resultados da coleta
            self.collector.save_results(collection_result)
            
            # FASE 2: SEGMENTAÇÃO
            logger.info(f"\n{'='*20} FASE 2: SEGMENTAÇÃO {'='*20}")
            segmentation_start = time.time()
            
            segmentation_result = self.segmenter.segment_articles(articles)
            
            self.pipeline_stats['segmentation_time'] = time.time() - segmentation_start
            
            if segmentation_result['status'] != 'success':
                error_msg = f"Erro na segmentação: {segmentation_result.get('error', 'Erro desconhecido')}"
                logger.error(error_msg)
                self.pipeline_stats['errors'].append(error_msg)
                return self._create_error_result(error_msg)
            
            segmented_results = segmentation_result['segmented_results']
            logger.info(f"✅ Segmentação concluída:")
            for segment, articles_list in segmented_results.items():
                if segment != 'outros':
                    logger.info(f"  - {segment}: {len(articles_list)} artigos")
            
            logger.info(f"⏱️ Tempo de segmentação: {self.pipeline_stats['segmentation_time']:.2f}s")
            
            # Salva resultados da segmentação
            self.segmenter.save_results(segmentation_result)
            
            # FASE 3: GERAÇÃO DE BOLETINS
            logger.info(f"\n{'='*20} FASE 3: GERAÇÃO DE BOLETINS {'='*20}")
            generation_start = time.time()

            # inicializa gerador apenas aqui (exige OPENROUTER_API_KEY)
            if self.generator is None:
                self.generator = BulletinGenerator()
            
            generation_result = self.generator.generate_bulletins(segmented_results)
            
            self.pipeline_stats['generation_time'] = time.time() - generation_start
            
            if generation_result['status'] != 'success':
                error_msg = f"Erro na geração: {generation_result.get('error', 'Erro desconhecido')}"
                logger.error(error_msg)
                self.pipeline_stats['errors'].append(error_msg)
                return self._create_error_result(error_msg)
            
            bulletins = generation_result['bulletins']
            successful_bulletins = sum(1 for b in bulletins.values() if b.get('status') == 'success')
            logger.info(f"✅ Geração concluída: {successful_bulletins} boletins gerados")
            logger.info(f"⏱️ Tempo de geração: {self.pipeline_stats['generation_time']:.2f}s")
            
            # Salva resultados da geração
            self.generator.save_results(generation_result)
            
            # FASE 4: ENVIO POR EMAIL (OPCIONAL)
            email_result = None
            if self.email_sender:
                logger.info(f"\n{'='*20} FASE 4: ENVIO POR EMAIL {'='*20}")
                email_start = time.time()
                
                try:
                    email_result = self.email_sender.send_bulletins(generation_result)
                    email_time = time.time() - email_start
                    
                    if email_result['status'] == 'success':
                        logger.info(f"✅ Emails enviados com sucesso para {email_result['total_recipients']} destinatários")
                    else:
                        logger.warning(f"⚠️ Erro no envio de emails: {email_result.get('error')}")
                    
                    logger.info(f"⏱️ Tempo de envio: {email_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"❌ Erro no envio de emails: {e}")
                    email_result = {'status': 'error', 'error': str(e)}
            else:
                logger.info(f"\n{'='*20} FASE 4: ENVIO POR EMAIL (PULADO) {'='*20}")
                logger.info("Configuração de email não encontrada. Pulando envio.")
            
            # FINALIZAÇÃO
            self.pipeline_stats['end_time'] = time.time()
            self.pipeline_stats['total_time'] = self.pipeline_stats['end_time'] - self.pipeline_stats['start_time']
            self.pipeline_stats['status'] = 'completed'
            
            # Combina todos os resultados
            combined_result = {
                'status': 'success',
                'pipeline_stats': self.pipeline_stats,
                'collection': collection_result,
                'segmentation': segmentation_result,
                'generation': generation_result,
                'email': email_result,
                'execution_date': datetime.now().isoformat(),
                'summary': self._create_summary(collection_result, segmentation_result, generation_result, email_result)
            }
            
            # Salva resultado completo do pipeline
            self._save_pipeline_result(combined_result)
            
            # Relatório final
            self._print_final_report(combined_result)
            
            return combined_result
            
        except Exception as e:
            error_msg = f"Erro no pipeline completo: {e}"
            logger.error(error_msg)
            self.pipeline_stats['errors'].append(error_msg)
            self.pipeline_stats['status'] = 'failed'
            return self._create_error_result(error_msg)
    
    def run_collection_only(self, days_back: int = None, max_articles_per_source: int = None) -> Dict[str, Any]:
        """Executa apenas a coleta de notícias"""
        try:
            logger.info("EXECUTANDO APENAS COLETA")
            logger.info("="*40)
            
            days_back = days_back or Config.DAYS_BACK
            max_articles_per_source = max_articles_per_source or Config.MAX_ARTICLES_PER_SOURCE
            
            result = self.collector.collect_articles(
                days_back=days_back,
                max_articles_per_source=max_articles_per_source
            )
            
            if result['status'] == 'success':
                self.collector.save_results(result)
                logger.info(f"✅ Coleta concluída: {result['stats']['ai_articles']} artigos")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na coleta: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def run_segmentation_only(self) -> Dict[str, Any]:
        """Executa apenas a segmentação dos últimos dados coletados"""
        try:
            logger.info("EXECUTANDO APENAS SEGMENTAÇÃO")
            logger.info("="*40)
            
            # Carrega últimos dados coletados
            latest_file = f"{Config.OUTPUT_DIR}/latest_collection.json"
            if not os.path.exists(latest_file):
                return {
                    'status': 'error',
                    'error': 'Nenhum dado de coleta encontrado. Execute uma coleta primeiro.'
                }
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                collection_data = json.load(f)
            
            articles = collection_data.get('articles', [])
            if not articles:
                return {
                    'status': 'error',
                    'error': 'Nenhum artigo encontrado nos dados de coleta.'
                }
            
            logger.info(f"Carregados {len(articles)} artigos para segmentação")
            
            # Executa segmentação
            result = self.segmenter.segment_articles(articles)
            
            if result['status'] == 'success':
                self.segmenter.save_results(result)
                logger.info(f"✅ Segmentação concluída")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na segmentação: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def run_generation_only(self) -> Dict[str, Any]:
        """Executa apenas a geração de boletins dos últimos dados segmentados"""
        try:
            logger.info("EXECUTANDO APENAS GERAÇÃO DE BOLETINS")
            logger.info("="*40)
            
            # Carrega últimos dados segmentados
            latest_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
            if not os.path.exists(latest_file):
                return {
                    'status': 'error',
                    'error': 'Nenhum dado de segmentação encontrado. Execute uma segmentação primeiro.'
                }
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                segmentation_data = json.load(f)
            
            segmented_results = segmentation_data.get('segmented_results', {})
            if not segmented_results:
                return {
                    'status': 'error',
                    'error': 'Nenhum resultado de segmentação encontrado.'
                }
            
            logger.info(f"Carregados dados de segmentação com {len(segmented_results)} segmentos")
            
            # inicializa gerador aqui (exige OPENROUTER_API_KEY)
            if self.generator is None:
                self.generator = BulletinGenerator()
            
            # Executa geração
            result = self.generator.generate_bulletins(segmented_results)
            
            if result['status'] == 'success':
                self.generator.save_results(result)
                logger.info(f"✅ Geração concluída")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na geração: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _create_summary(self, collection_result: Dict, segmentation_result: Dict, generation_result: Dict, email_result: Dict = None) -> Dict[str, Any]:
        """Cria resumo dos resultados do pipeline"""
        try:
            summary = {
                'total_articles_collected': collection_result.get('stats', {}).get('ai_articles', 0),
                'sources_processed': collection_result.get('total_sources', 0),
                'segmentation_stats': segmentation_result.get('stats', {}).get('segments_stats', {}),
                'bulletins_generated': generation_result.get('stats', {}).get('successful_bulletins', 0),
                'bulletins_failed': generation_result.get('stats', {}).get('failed_bulletins', 0),
                'emails_sent': email_result.get('total_recipients', 0) if email_result and email_result.get('status') == 'success' else 0,
                'email_status': email_result.get('status', 'not_configured') if email_result else 'not_configured',
                'execution_time': self.pipeline_stats['total_time'],
                'collection_time': self.pipeline_stats['collection_time'],
                'segmentation_time': self.pipeline_stats['segmentation_time'],
                'generation_time': self.pipeline_stats['generation_time']
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Erro ao criar resumo: {e}")
            return {}
    
    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """Cria resultado de erro"""
        return {
            'status': 'error',
            'error': error_msg,
            'pipeline_stats': self.pipeline_stats,
            'execution_date': datetime.now().isoformat()
        }
    
    def _save_pipeline_result(self, result: Dict[str, Any]):
        """Salva resultado completo do pipeline"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{Config.OUTPUT_DIR}/pipeline_result_{timestamp}.json"
            
            # Prepara dados para salvar
            save_data = {
                'execution_date': result.get('execution_date', datetime.now().isoformat()),
                'status': result.get('status', 'unknown'),
                'pipeline_stats': result.get('pipeline_stats', {}),
                'summary': result.get('summary', {}),
                'collection': result.get('collection', {}),
                'segmentation': result.get('segmentation', {}),
                'generation': result.get('generation', {}),
                'timestamp': timestamp
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Resultado completo do pipeline salvo em: {filename}")
            
            # Também salva como 'latest' para o visualizador
            latest_filename = f"{Config.OUTPUT_DIR}/latest_pipeline.json"
            with open(latest_filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Resultado também salvo como: {latest_filename}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultado do pipeline: {e}")
    
    def _print_final_report(self, result: Dict[str, Any]):
        """Imprime relatório final do pipeline"""
        logger.info("\n" + "="*80)
        logger.info("RELATÓRIO FINAL DO PIPELINE")
        logger.info("="*80)
        
        summary = result.get('summary', {})
        pipeline_stats = result.get('pipeline_stats', {})
        
        logger.info(f"Status: {result.get('status', 'unknown').upper()}")
        logger.info(f"Data de execução: {result.get('execution_date', 'N/A')}")
        logger.info(f"Tempo total: {pipeline_stats.get('total_time', 0):.2f}s")
        
        logger.info(f"\nESTATÍSTICAS:")
        logger.info(f"  Artigos coletados: {summary.get('total_articles_collected', 0)}")
        logger.info(f"  Fontes processadas: {summary.get('sources_processed', 0)}")
        logger.info(f"  Boletins gerados: {summary.get('bulletins_generated', 0)}")
        logger.info(f"  Boletins com erro: {summary.get('bulletins_failed', 0)}")
        
        logger.info(f"\nTEMPOS DE EXECUÇÃO:")
        logger.info(f"  Coleta: {summary.get('collection_time', 0):.2f}s")
        logger.info(f"  Segmentação: {summary.get('segmentation_time', 0):.2f}s")
        logger.info(f"  Geração: {summary.get('generation_time', 0):.2f}s")
        
        logger.info(f"\nSEGMENTAÇÃO:")
        segments_stats = summary.get('segmentation_stats', {})
        for segment, count in segments_stats.items():
            if segment != 'outros':
                logger.info(f"  {segment}: {count} artigos")
        
        if pipeline_stats.get('errors'):
            logger.info(f"\nERROS ENCONTRADOS:")
            for error in pipeline_stats['errors']:
                logger.info(f"  - {error}")
        
        logger.info("="*80)
    
    def get_latest_results(self) -> Dict[str, Any]:
        """Retorna os últimos resultados do pipeline"""
        try:
            latest_file = f"{Config.OUTPUT_DIR}/latest_pipeline.json"
            if os.path.exists(latest_file):
                with open(latest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {'status': 'no_data', 'message': 'Nenhum resultado encontrado'}
        except Exception as e:
            logger.error(f"Erro ao carregar resultados: {e}")
            return {'status': 'error', 'error': str(e)}

def main():
    """Função principal para executar o pipeline"""
    print("PIPELINE DE BOLETINS IA")
    print("="*50)
    print("Escolha uma opção:")
    print("1. Pipeline completo (coleta + segmentação + geração)")
    print("2. Apenas coleta")
    print("3. Apenas segmentação")
    print("4. Apenas geração de boletins")
    print("5. Exibir últimos resultados")
    print("="*50)
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/pipeline.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria diretórios necessários
    Config.create_directories()
    
    try:
        escolha = input("Digite sua escolha (1-5): ").strip()
        
        pipeline = BoletinsPipeline()
        
        if escolha == "1":
            print("\nExecutando pipeline completo...")
            result = pipeline.run_full_pipeline()
            
            if result['status'] == 'success':
                print(f"\n✅ SUCESSO! Pipeline completo executado")
                print(f"Tempo total: {result['summary']['execution_time']:.2f}s")
                print(f"Boletins gerados: {result['summary']['bulletins_generated']}")
            else:
                print(f"\n❌ Erro: {result.get('error', 'Erro desconhecido')}")
            
            print("\nAbrindo visualizador...")
            start_visualizer()
        
        elif escolha == "2":
            print("\nExecutando apenas coleta...")
            result = pipeline.run_collection_only()
            
            if result['status'] == 'success':
                print(f"\n✅ Sucesso! Coleta concluída")
                print(f"Artigos coletados: {result['stats']['ai_articles']}")
            else:
                print(f"\n❌ Erro: {result.get('error', 'Erro desconhecido')}")
            
            print("\nAbrindo visualizador...")
            start_visualizer()
        
        elif escolha == "3":
            print("\nExecutando apenas segmentação...")
            result = pipeline.run_segmentation_only()
            
            if result['status'] == 'success':
                print(f"\n✅ Sucesso! Segmentação concluída")
                print(f"Segmentos processados: {len(result['segmented_results'])}")
            else:
                print(f"\n❌ Erro: {result.get('error', 'Erro desconhecido')}")
            
            print("\nAbrindo visualizador...")
            start_visualizer()
        
        elif escolha == "4":
            print("\nExecutando apenas geração de boletins...")
            result = pipeline.run_generation_only()
            
            if result['status'] == 'success':
                print(f"\n✅ Sucesso! Geração concluída")
                print(f"Boletins gerados: {result['stats']['successful_bulletins']}")
            else:
                print(f"\n❌ Erro: {result.get('error', 'Erro desconhecido')}")
            
            print("\nAbrindo visualizador...")
            start_visualizer()
        
        elif escolha == "5":
            print("\nCarregando últimos resultados...")
            results = pipeline.get_latest_results()
            
            if results.get('status') == 'no_data':
                print("Nenhum resultado encontrado. Execute o pipeline primeiro.")
            else:
                print(f"Data: {results.get('execution_date', 'N/A')}")
                print(f"Status: {results.get('status', 'N/A')}")
                
                summary = results.get('summary', {})
                if summary:
                    print(f"Artigos coletados: {summary.get('total_articles_collected', 0)}")
                    print(f"Boletins gerados: {summary.get('bulletins_generated', 0)}")
                    print(f"Tempo total: {summary.get('execution_time', 0):.2f}s")
            
            print("\nAbrindo visualizador...")
            start_visualizer()
        
        else:
            print("Escolha inválida. Executando pipeline completo...")
            result = pipeline.run_full_pipeline()
            
            if result['status'] == 'success':
                print(f"\n✅ Sucesso! Pipeline completo executado")
                print(f"Tempo total: {result['summary']['execution_time']:.2f}s")
            
            print("\nAbrindo visualizador...")
            start_visualizer()
    
    except KeyboardInterrupt:
        print("\nPipeline interrompido pelo usuário")
    except Exception as e:
        print(f"\nErro inesperado: {e}")

if __name__ == "__main__":
    main()
