"""
Gerador de boletins usando IA (OpenRouter/Gemini)
"""

import requests
import logging
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from config import Config
from monitoring_openrouter import OpenRouterGuard

logger = logging.getLogger(__name__)

class BulletinGenerator:
    """Gerador de boletins usando IA via OpenRouter"""
    
    def __init__(self):
        self.api_key = Config.get_openrouter_api_key()
        self.base_url = Config.OPENROUTER_BASE_URL
        self.model = Config.GEMINI_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        self.guard = OpenRouterGuard()
        
        # Templates para diferentes segmentos
        self.templates = {
            'tecnologia': {
                'title': 'Boletim de Tecnologia e IA',
                'intro': 'Principais desenvolvimentos em tecnologia e inteligência artificial',
                'focus': 'inovação tecnológica, startups, desenvolvimento de software, inteligência artificial'
            },
            'marketing': {
                'title': 'Boletim de Marketing e Comunicação',
                'intro': 'Tendências em marketing digital e comunicação corporativa',
                'focus': 'marketing digital, branding, comunicação, vendas, redes sociais'
            },
            'direito_corporativo': {
                'title': 'Boletim de Direito Corporativo',
                'intro': 'Atualizações jurídicas e regulamentações empresariais',
                'focus': 'direito corporativo, compliance, legislação, regulamentações'
            }
        }
    
    def generate_bulletins(self, segmented_articles: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Gera boletins para todos os segmentos"""
        try:
            logger.info("INICIANDO GERAÇÃO DE BOLETINS")
            logger.info("="*50)
            
            bulletins = {}
            stats = {
                'total_segments': len(segmented_articles),
                'successful_bulletins': 0,
                'failed_bulletins': 0,
                'generation_time': 0,
                'segments_stats': {}
            }
            
            start_time = time.time()
            
            # Processa cada segmento
            for segment_name, articles in segmented_articles.items():
                if segment_name == 'outros' or not articles:
                    continue
                
                try:
                    logger.info(f"\nGerando boletim para segmento: {segment_name}")
                    logger.info(f"Artigos disponíveis: {len(articles)}")
                    
                    # Seleciona os melhores artigos (máximo configurado)
                    selected_articles = self._select_best_articles(articles, Config.MAX_ARTICLES_PER_SEGMENT)
                    
                    if not selected_articles:
                        logger.warning(f"Nenhum artigo selecionado para {segment_name}")
                        bulletins[segment_name] = {
                            'status': 'error',
                            'error': 'Nenhum artigo selecionado'
                        }
                        stats['failed_bulletins'] += 1
                        continue
                    
                    # Gera boletim
                    bulletin_result = self._generate_single_bulletin(segment_name, selected_articles)
                    
                    if bulletin_result['status'] == 'success':
                        bulletins[segment_name] = bulletin_result
                        stats['successful_bulletins'] += 1
                        stats['segments_stats'][segment_name] = len(selected_articles)
                        logger.info(f"✅ Boletim gerado para {segment_name}")
                    else:
                        bulletins[segment_name] = bulletin_result
                        stats['failed_bulletins'] += 1
                        logger.error(f"❌ Erro ao gerar boletim para {segment_name}: {bulletin_result.get('error')}")
                    
                    # Pausa entre gerações para evitar rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar segmento {segment_name}: {e}")
                    bulletins[segment_name] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    stats['failed_bulletins'] += 1
                    continue
            
            # Calcula tempo total
            stats['generation_time'] = round(time.time() - start_time, 2)
            
            # Relatório final
            self._print_final_report(stats)
            
            return {
                'status': 'success',
                'bulletins': bulletins,
                'stats': stats,
                'generated_date': datetime.now().isoformat(),
                'method': 'ai_openrouter'
            }
            
        except Exception as e:
            logger.error(f"Erro na geração de boletins: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'bulletins': {},
                'stats': stats
            }
    
    def _select_best_articles(self, articles: List[Dict], max_count: int) -> List[Dict]:
        """Seleciona os melhores artigos para o boletim"""
        try:
            # Ordena por data de publicação (mais recentes primeiro)
            sorted_articles = sorted(
                articles, 
                key=lambda x: self._parse_date(x.get('published', '')), 
                reverse=True
            )
            
            # Retorna os primeiros N artigos
            return sorted_articles[:max_count]
            
        except Exception as e:
            logger.error(f"Erro ao selecionar artigos: {e}")
            return articles[:max_count]
    
    def _generate_single_bulletin(self, segment_name: str, articles: List[Dict]) -> Dict[str, Any]:
        """Gera um boletim para um segmento específico"""
        try:
            template = self.templates.get(segment_name, {
                'title': f'Boletim de {segment_name.title()}',
                'intro': f'Principais notícias sobre {segment_name}',
                'focus': segment_name
            })
            
            # Prepara contexto dos artigos
            articles_context = self._prepare_articles_context(articles)
            
            # Prompt para geração (adequado ao pedido do usuário)
            prompt = (
                f"Você é um jornalista sênior. Gere um boletim semanal em português para o segmento '{template['title']}'.\n"
                f"Inclua: título; resumo executivo com highlights; texto jornalístico coeso (início, meio e fim) em até 1000 caracteres,\n"
                f"relatando o que aconteceu na semana no segmento, com tom profissional e didático.\n\n"
                f"Use apenas os 15 links selecionados.\n\n"
                f"NOTÍCIAS:\n{articles_context}\n\nGere agora o boletim:"
            )
            
            # Chamada protegida via guard
            response = self.guard.generate_text(prompt)
            
            if response['status'] == 'success':
                formatted_text = self._format_bulletin_text(
                    response['content'], 
                    template, 
                    articles, 
                    segment_name
                )
                
                return {
                    'status': 'success',
                    'segment': segment_name,
                    'title': template['title'],
                    'articles_count': len(articles),
                    'generated_date': datetime.now().isoformat(),
                    'method': 'ai_openrouter',
                    'ai_generated_text': formatted_text,
                    'selected_articles': articles
                }
            else:
                return {
                    'status': 'error',
                    'error': response.get('error', 'Erro desconhecido na API')
                }
                
        except Exception as e:
            logger.error(f"Erro ao gerar boletim para {segment_name}: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _prepare_articles_context(self, articles: List[Dict]) -> str:
        """Prepara contexto dos artigos para o prompt"""
        context_parts = []
        
        for i, article in enumerate(articles, 1):
            context_parts.append(f"""
{i}. Título: {article.get('title', 'N/A')}
   Fonte: {article.get('source', 'N/A')}
   Data: {article.get('published', 'N/A')}
   URL: {article.get('url', 'N/A')}
""")
        
        return '\n'.join(context_parts)
    
    def _create_prompt(self, template: Dict, articles_context: str, segment_name: str) -> str:
        """Cria prompt para geração do boletim"""
        prompt = f"""
Você é um especialista em análise de notícias e criação de boletins informativos.

TAREFA: Criar um boletim informativo sobre {template['focus']} baseado nas notícias fornecidas.

INSTRUÇÕES:
1. Analise as notícias fornecidas abaixo
2. Identifique os temas principais e tendências
3. Crie um boletim bem estruturado e informativo
4. Use linguagem profissional mas acessível
5. Inclua insights e análises relevantes
6. Mantenha o foco em {template['focus']}

FORMATO DO BOLETIM:
- Título principal
- Introdução com contexto geral
- Seções temáticas com análises
- Conclusão com insights principais
- Máximo de {self.max_tokens} tokens

NOTÍCIAS PARA ANÁLISE:
{articles_context}

Gere o boletim agora:
"""
        return prompt
    
    def _call_openrouter_api(self, prompt: str) -> Dict[str, Any]:
        """Chama a API do OpenRouter"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://github.com/boletins-ia',
                'X-Title': 'Boletins IA Generator'
            }
            
            data = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'stream': False
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return {
                    'status': 'success',
                    'content': content
                }
            else:
                error_msg = f"Erro na API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'status': 'error',
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"Erro ao chamar API do OpenRouter: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _format_bulletin_text(self, ai_content: str, template: Dict, articles: List[Dict], segment_name: str) -> str:
        """Formata o texto do boletim"""
        try:
            # Cabeçalho do boletim
            header = f"""
# {template['title']}

**Data:** {datetime.now().strftime('%d/%m/%Y')}  
**Segmento:** {segment_name.title()}  
**Artigos analisados:** {len(articles)}

---

{template['intro']}

---

"""
            
            # Conteúdo gerado pela IA
            content = ai_content.strip()
            
            # Rodapé com links dos artigos
            footer = f"""

---

## Artigos Analisados

"""
            
            for i, article in enumerate(articles, 1):
                footer += f"{i}. **{article.get('title', 'N/A')}**  \n"
                footer += f"   Fonte: {article.get('source', 'N/A')}  \n"
                footer += f"   Link: {article.get('url', 'N/A')}  \n\n"
            
            footer += f"""
---

*Boletim gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M')}*
"""
            
            return header + content + footer
            
        except Exception as e:
            logger.error(f"Erro ao formatar boletim: {e}")
            return ai_content
    
    def _parse_date(self, date_str: str) -> datetime:
        """Converte string de data para datetime"""
        try:
            if not date_str:
                return datetime.min
            
            # Tenta diferentes formatos
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return datetime.min
            
        except Exception as e:
            logger.error(f"Erro ao parsear data '{date_str}': {e}")
            return datetime.min
    
    def _print_final_report(self, stats: Dict):
        """Imprime relatório final da geração"""
        logger.info("\n" + "="*60)
        logger.info("RELATÓRIO FINAL DA GERAÇÃO DE BOLETINS")
        logger.info("="*60)
        logger.info(f"Tempo total: {stats['generation_time']}s")
        logger.info(f"Boletins gerados com sucesso: {stats['successful_bulletins']}")
        logger.info(f"Boletins com erro: {stats['failed_bulletins']}")
        logger.info(f"Taxa de sucesso: {(stats['successful_bulletins']/(stats['successful_bulletins']+stats['failed_bulletins'])*100):.1f}%")
        
        logger.info(f"\nEstatísticas por segmento:")
        for segment, count in stats['segments_stats'].items():
            logger.info(f"  {segment}: {count} artigos")
        
        logger.info("="*60)
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Salva resultados da geração em arquivo JSON"""
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{Config.OUTPUT_DIR}/bulletins_{timestamp}.json"
            
            # Prepara dados para salvar
            save_data = {
                'generated_date': results.get('generated_date', datetime.now().isoformat()),
                'status': results.get('status', 'unknown'),
                'method': results.get('method', 'ai_openrouter'),
                'stats': results.get('stats', {}),
                'bulletins': results.get('bulletins', {}),
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Resultados da geração salvos em: {filename}")
            
            # Também salva como 'latest' para o pipeline
            latest_filename = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
            with open(latest_filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Resultados também salvos como: {latest_filename}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultados da geração: {e}")

def main():
    """Função principal para testar o gerador"""
    print("GERADOR DE BOLETINS IA")
    print("="*50)
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/generator.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria diretórios necessários
    Config.create_directories()
    
    # Valida configuração
    if not Config.validate_config():
        print("❌ Configuração inválida. Verifique as variáveis de ambiente.")
        return
    
    try:
        # Carrega dados de segmentação mais recentes
        latest_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
        
        if not os.path.exists(latest_file):
            print("❌ Nenhum dado de segmentação encontrado. Execute o segmentador primeiro.")
            return
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            segmentation_data = json.load(f)
        
        segmented_results = segmentation_data.get('segmented_results', {})
        if not segmented_results:
            print("❌ Nenhum resultado de segmentação encontrado.")
            return
        
        print(f"Carregados dados de segmentação com {len(segmented_results)} segmentos")
        
        # Executa geração
        generator = BulletinGenerator()
        results = generator.generate_bulletins(segmented_results)
        
        if results['status'] == 'success':
            print(f"\n✅ GERAÇÃO CONCLUÍDA COM SUCESSO!")
            print(f"Boletins gerados: {results['stats']['successful_bulletins']}")
            print(f"Tempo: {results['stats']['generation_time']}s")
            
            # Salva resultados
            generator.save_results(results)
            
        else:
            print(f"❌ Erro na geração: {results.get('error', 'Erro desconhecido')}")
    
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")

if __name__ == "__main__":
    main()
