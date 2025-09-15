"""
Visualizador web para resultados dos boletins
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS

from config import Config
from email_sender import EmailSender

logger = logging.getLogger(__name__)

class BoletinsVisualizer:
    """Visualizador web para resultados dos boletins"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        
        # Configura CORS
        CORS(self.app)
        
        # Configura rotas
        self._setup_routes()
        
        logger.info(f"Visualizador inicializado em {host}:{port}")
    
    def _setup_routes(self):
        """Configura rotas da aplicação"""
        
        @self.app.route('/')
        def index():
            """Página principal"""
            return render_template('index.html')
        
        @self.app.route('/api/pipeline_results')
        def get_pipeline_results():
            """API para obter resultados do pipeline"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_pipeline.json"
                
                if not os.path.exists(latest_file):
                    # Fallback: sintetiza relatório a partir de arquivos existentes
                    collection_file = f"{Config.OUTPUT_DIR}/latest_collection.json"
                    segmentation_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
                    bulletins_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
                    collection = {}
                    segmentation = {}
                    bulletins = {}
                    if os.path.exists(collection_file):
                        try:
                            with open(collection_file, 'r', encoding='utf-8') as f:
                                collection = json.load(f)
                        except Exception:
                            collection = {}
                    if os.path.exists(segmentation_file):
                        try:
                            with open(segmentation_file, 'r', encoding='utf-8') as f:
                                segmentation = json.load(f)
                        except Exception:
                            segmentation = {}
                    if os.path.exists(bulletins_file):
                        try:
                            with open(bulletins_file, 'r', encoding='utf-8') as f:
                                bulletins = json.load(f)
                        except Exception:
                            bulletins = {}

                    bulletins_map = bulletins.get('bulletins', {}) if isinstance(bulletins, dict) else {}
                    successful_bulletins = 0
                    segments_stats = {}
                    if bulletins_map:
                        for seg_key, info in bulletins_map.items():
                            if isinstance(info, dict) and info.get('status') == 'success':
                                successful_bulletins += 1
                                # Conta artigos usados por segmento
                                segments_stats[seg_key] = info.get('articles_count', 0)

                    # Determina status
                    if successful_bulletins > 0:
                        status = 'success'
                    elif segmentation:
                        status = 'partial'
                    elif collection:
                        status = 'partial'
                    else:
                        status = 'no_data'

                    # Data de execução (usa o mais recente dos arquivos disponíveis)
                    times = []
                    for p in [collection_file, segmentation_file, bulletins_file]:
                        if os.path.exists(p):
                            try:
                                times.append(datetime.fromtimestamp(os.path.getmtime(p)))
                            except Exception:
                                pass
                    execution_date = (max(times).isoformat() if times else datetime.now().isoformat())

                    # Monta resposta compatível
                    data = {
                        'status': status,
                        'summary': {
                            'execution_time': 0,
                            'bulletins_generated': successful_bulletins,
                        },
                        'pipeline_stats': {
                            'collected_articles': (collection.get('stats', {}) or {}).get('ai_articles', 0),
                            'segmented_articles': (segmentation.get('segmentation', {}) or {}).get('total', None) or (segmentation.get('stats', {}) or {}).get('total_articles', 0),
                            'segments_stats': segments_stats
                        },
                        'execution_date': execution_date
                    }

                    return jsonify({
                        'success': True,
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    })
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Erro ao obter resultados do pipeline: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/collection_results')
        def get_collection_results():
            """API para obter resultados da coleta"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_collection.json"
                
                if not os.path.exists(latest_file):
                    return jsonify({
                        'success': False,
                        'error': 'Nenhum resultado de coleta encontrado'
                    })
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Erro ao obter resultados da coleta: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/segmentation_results')
        def get_segmentation_results():
            """API para obter resultados da segmentação"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
                
                if not os.path.exists(latest_file):
                    return jsonify({
                        'success': False,
                        'error': 'Nenhum resultado de segmentação encontrado'
                    })
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Erro ao obter resultados da segmentação: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/bulletins')
        def get_bulletins():
            """API para obter boletins gerados"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
                
                if not os.path.exists(latest_file):
                    return jsonify({
                        'success': False,
                        'error': 'Nenhum boletim encontrado'
                    })
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return jsonify({
                    'success': True,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Erro ao obter boletins: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/bulletins/download/<segment>')
        def download_bulletin(segment):
            """API para download de boletim em formato TXT"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
                
                if not os.path.exists(latest_file):
                    return jsonify({
                        'success': False,
                        'error': 'Nenhum boletim encontrado'
                    }), 404
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                bulletins = data.get('bulletins', {})
                bulletin_info = bulletins.get(segment)
                
                if not bulletin_info or bulletin_info.get('status') != 'success':
                    return jsonify({
                        'success': False,
                        'error': f'Boletim não encontrado para o segmento: {segment}'
                    }), 404
                
                # Prepara o conteúdo do boletim para download
                formatted_text = bulletin_info.get('ai_generated_text', '')
                
                # Cria nome do arquivo
                date_str = datetime.now().strftime("%Y%m%d")
                filename = f"boletim_{segment}_{date_str}.txt"
                
                # Cria resposta com arquivo TXT
                response = Response(
                    formatted_text,
                    mimetype='text/plain',
                    headers={
                        'Content-Disposition': f'attachment; filename="{filename}"',
                        'Content-Type': 'text/plain; charset=utf-8'
                    }
                )
                
                logger.info(f"Download do boletim '{segment}' solicitado")
                return response
                
            except Exception as e:
                logger.error(f"Erro ao fazer download do boletim '{segment}': {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/bulletins/view/<segment>')
        def view_bulletin(segment):
            """API para visualização detalhada de boletim"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
                
                if not os.path.exists(latest_file):
                    return jsonify({
                        'success': False,
                        'error': 'Nenhum boletim encontrado'
                    }), 404
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                bulletins = data.get('bulletins', {})
                bulletin_info = bulletins.get(segment)
                
                if not bulletin_info or bulletin_info.get('status') != 'success':
                    return jsonify({
                        'success': False,
                        'error': f'Boletim não encontrado para o segmento: {segment}'
                    }), 404
                
                # Prepara dados detalhados do boletim
                formatted_text = bulletin_info.get('ai_generated_text', '')
                html_content = self._convert_text_to_html(formatted_text)
                
                return jsonify({
                    'success': True,
                    'bulletin': {
                        'segment': bulletin_info.get('segment', ''),
                        'title': bulletin_info.get('title', ''),
                        'articles_count': bulletin_info.get('articles_count', 0),
                        'generated_date': bulletin_info.get('generated_date', ''),
                        'method': bulletin_info.get('method', 'ai_openrouter'),
                        'formatted_text': formatted_text,
                        'html_content': html_content,
                        'status': 'success',
                        'selected_articles': bulletin_info.get('selected_articles', []),
                        'article_summaries': bulletin_info.get('article_summaries', [])
                    }
                })
                
            except Exception as e:
                logger.error(f"Erro ao visualizar boletim '{segment}': {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/stats')
        def get_stats():
            """API para obter estatísticas gerais"""
            try:
                stats = {
                    'collection_stats': self._get_collection_stats(),
                    'segmentation_stats': self._get_segmentation_stats(),
                    'generation_stats': self._get_generation_stats(),
                    'pipeline_stats': self._get_pipeline_stats(),
                    'source_quality': self._get_source_quality(),
                    'timestamp': datetime.now().isoformat()
                }
                
                return jsonify({
                    'success': True,
                    'stats': stats
                })
                
            except Exception as e:
                logger.error(f"Erro ao obter estatísticas: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/email/send-latest', methods=['POST'])
        def send_latest_email():
            """Envia por email os últimos boletins gerados"""
            try:
                latest_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
                if not os.path.exists(latest_file):
                    return jsonify({'success': False, 'error': 'Nenhum boletim encontrado'}), 404
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                try:
                    sender = EmailSender()
                except Exception as e:
                    return jsonify({'success': False, 'error': f'Configuração de email inválida: {e}'}), 400
                result = sender.send_bulletins(data)
                if result.get('status') == 'success':
                    return jsonify({'success': True, 'result': result})
                return jsonify({'success': False, 'error': result.get('error','Erro no envio')}), 500
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
    
    def _get_collection_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas da coleta"""
        try:
            latest_file = f"{Config.OUTPUT_DIR}/latest_collection.json"
            if os.path.exists(latest_file):
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('stats', {})
            return {}
        except:
            return {}
    
    def _get_segmentation_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas da segmentação"""
        try:
            latest_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
            if os.path.exists(latest_file):
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('stats', {})
            return {}
        except:
            return {}
    
    def _get_generation_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas da geração"""
        try:
            latest_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
            if os.path.exists(latest_file):
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('stats', {})
            return {}
        except:
            return {}
    
    def _get_pipeline_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do pipeline"""
        try:
            latest_file = f"{Config.OUTPUT_DIR}/latest_pipeline.json"
            if os.path.exists(latest_file):
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('pipeline_stats', {})
            return {}
        except:
            return {}

    def _get_source_quality(self) -> Dict[str, Any]:
        """Calcula métricas de qualidade por fonte: coletados vs selecionados Top15"""
        try:
            latest_collection = f"{Config.OUTPUT_DIR}/latest_collection.json"
            latest_selection = f"{Config.OUTPUT_DIR}/latest_selection.json"
            collected_by_source = {}
            selected_by_source = {}
            if os.path.exists(latest_collection):
                with open(latest_collection, 'r', encoding='utf-8') as f:
                    col = json.load(f)
                for art in col.get('articles', []):
                    src = art.get('source', 'Desconhecida')
                    collected_by_source[src] = collected_by_source.get(src, 0) + 1
            if os.path.exists(latest_selection):
                with open(latest_selection, 'r', encoding='utf-8') as f:
                    sel = json.load(f)
                selection = sel.get('selection_by_segment', {})
                for seg_list in selection.values():
                    for art in seg_list or []:
                        src = art.get('source', 'Desconhecida')
                        selected_by_source[src] = selected_by_source.get(src, 0) + 1
            sources = set().union(collected_by_source.keys(), selected_by_source.keys())
            quality = {}
            for src in sorted(sources):
                collected = collected_by_source.get(src, 0)
                selected = selected_by_source.get(src, 0)
                rate = (selected / collected) if collected else 0.0
                quality[src] = {
                    'collected': collected,
                    'selected_top15': selected,
                    'selection_rate': round(rate, 3)
                }
            return quality
        except Exception:
            return {}
    
    def _convert_text_to_html(self, text):
        """Converte texto formatado para HTML"""
        if not text:
            return ""
        
        # Converte markdown básico para HTML
        html = text
        
        # Títulos
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Negrito
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)
        
        # Listas
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Quebras de linha
        html = html.replace('\n', '<br>')
        
        # Agrupa listas
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        return html
    
    def start(self, debug: bool = False):
        """Inicia o servidor web"""
        try:
            logger.info(f"Iniciando servidor web em {self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)
        except Exception as e:
            logger.error(f"Erro ao iniciar servidor web: {e}")
            raise

def create_html_template():
    """Cria template HTML para o visualizador"""
    html_content = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boletins IA - Visualizador</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .stat-card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        
        .stat-card .value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        
        .stat-card .label {
            color: #666;
            font-size: 0.9em;
        }
        
        .tabs {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .tab-headers {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
        }
        
        .tab-header {
            padding: 15px 25px;
            cursor: pointer;
            border-right: 1px solid #ddd;
            transition: background-color 0.3s;
            font-weight: 600;
            flex: 1;
            text-align: center;
        }
        
        .tab-header:hover {
            background: #e9ecef;
        }
        
        .tab-header.active {
            background: white;
            border-bottom: 3px solid #667eea;
        }
        
        .tab-content {
            padding: 30px;
            min-height: 400px;
        }
        
        .tab-panel {
            display: none;
        }
        
        .tab-panel.active {
            display: block;
        }
        
        .bulletins-list {
            max-height: 600px;
            overflow-y: auto;
        }
        
        .bulletin-item {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #28a745;
            transition: transform 0.2s;
        }
        
        .bulletin-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .bulletin-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }
        
        .bulletin-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #666;
        }
        
        .bulletin-segment {
            background: #667eea;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }
        
        .bulletin-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: background-color 0.3s;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5a6fd8;
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 1.1em;
        }
        
        .loading::after {
            content: '';
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #667eea;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #dc3545;
        }
        
        .success {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 20px;
            transition: transform 0.2s;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 20px;
            border-radius: 10px;
            width: 90%;
            max-width: 800px;
            max-height: 80%;
            overflow-y: auto;
        }
        
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .close:hover {
            color: #000;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Boletins IA</h1>
        <p>Sistema de Coleta, Segmentação e Geração de Boletins sobre Inteligência Artificial</p>
    </div>
    
    <div class="container">
        <button class="refresh-btn" onclick="loadData()">🔄 Atualizar Dados</button>
        
        <div class="stats-grid" id="statsGrid">
            <div class="loading">Carregando estatísticas...</div>
        </div>
        
        <div class="tabs">
            <div class="tab-headers">
                <div class="tab-header active" onclick="showTab('collection', this)">Coleta</div>
                <div class="tab-header" onclick="showTab('direito', this)">Direito</div>
                <div class="tab-header" onclick="showTab('comunicacao', this)">Comunicação</div>
                <div class="tab-header" onclick="showTab('rh', this)">RH</div>
                <div class="tab-header" onclick="showTab('pipeline', this)">Pipeline</div>
                <div class="tab-header" onclick="showTab('email', this)">Email</div>
            </div>
            
            <div class="tab-content">
                <div id="collection" class="tab-panel active">
                    <h3>Resultados da Coleta</h3>
                    <div id="collectionResults">
                        <div class="loading">Carregando dados de coleta...</div>
                    </div>
                </div>
                
                <div id="direito" class="tab-panel">
                    <h3>Direito Corporativo, Tributário, Trabalhista</h3>
                    <div id="direitoContent"><div class="loading">Carregando...</div></div>
                </div>
                
                <div id="comunicacao" class="tab-panel">
                    <h3>Marketing, Comunicação e Jornalismo</h3>
                    <div id="comunicacaoContent"><div class="loading">Carregando...</div></div>
                </div>
                
                <div id="rh" class="tab-panel">
                    <h3>Recursos Humanos e Gestão de Pessoas</h3>
                    <div id="rhContent"><div class="loading">Carregando...</div></div>
                </div>
                
                <div id="pipeline" class="tab-panel">
                    <h3>Resultados do Pipeline</h3>
                    <div id="pipelineResults">
                        <div class="loading">Carregando dados do pipeline...</div>
                    </div>
                </div>
                
                <div id="email" class="tab-panel">
                    <h3>Envio por Email</h3>
                    <div>
                        <p>Enviar os últimos boletins gerados para os destinatários configurados.</p>
                        <button class="btn btn-primary" onclick="sendEmail()">Enviar últimos boletins por email</button>
                        <div id="emailResult" style="margin-top:10px;"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Modal para visualização de boletim -->
    <div id="bulletinModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modalContent"></div>
        </div>
    </div>
    
    <script>
        let currentData = null;
        
        function showTab(tabName, el) {
            // Remove active class from all headers and panels
            document.querySelectorAll('.tab-header').forEach(header => {
                header.classList.remove('active');
            });
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            
            // Add active class to selected tab
            if (el) { el.classList.add('active'); }
            document.getElementById(tabName).classList.add('active');
            
            // Load data for the tab
            loadTabData(tabName);
        }
        
        function loadTabData(tabName) {
            switch(tabName) {
                case 'collection':
                    loadCollectionData();
                    break;
                case 'direito':
                    loadSegmentTab('direito_corporativo_tributario_trabalhista', 'direitoContent');
                    break;
                case 'comunicacao':
                    loadSegmentTab('marketing_comunicacao_jornalismo', 'comunicacaoContent');
                    break;
                case 'rh':
                    loadSegmentTab('recursos_humanos_gestao_pessoas', 'rhContent');
                    break;
                case 'pipeline':
                    loadPipelineData();
                    break;
                case 'email':
                    break;
            }
        }
        
        async function loadBulletins() {
            const container = document.getElementById('bulletinsList');
            
            try {
                const response = await fetch('/api/bulletins');
                const result = await response.json();
                
                if (!result.success) {
                    container.innerHTML = `<div class="error">Erro ao carregar boletins: ${result.error}</div>`;
                    return;
                }
                
                const data = result.data;
                const bulletins = data.bulletins || {};
                
                if (Object.keys(bulletins).length === 0) {
                    container.innerHTML = '<div class="error">Nenhum boletim encontrado</div>';
                    return;
                }
                
                let html = '';
                Object.keys(bulletins).forEach(segment => {
                    const bulletin = bulletins[segment];
                    if (bulletin.status === 'success') {
                        html += `
                            <div class="bulletin-item">
                                <div class="bulletin-title">${bulletin.title}</div>
                                <div class="bulletin-meta">
                                    <span class="bulletin-segment">${segment}</span>
                                    <span>${bulletin.articles_count} artigos • ${new Date(bulletin.generated_date).toLocaleString('pt-BR')}</span>
                                </div>
                                <div class="bulletin-actions">
                                    <button class="btn btn-primary" onclick="viewBulletin('${segment}')">Ver Boletim</button>
                                    <button class="btn btn-secondary" onclick="downloadBulletin('${segment}')">Download TXT</button>
                                </div>
                            </div>
                        `;
                    } else {
                        html += `
                            <div class="bulletin-item" style="border-left-color: #dc3545;">
                                <div class="bulletin-title">Erro: ${segment}</div>
                                <div class="error">${bulletin.error}</div>
                            </div>
                        `;
                    }
                });
                
                container.innerHTML = html;
                
            } catch (error) {
                container.innerHTML = `<div class="error">Erro de conexão: ${error.message}</div>`;
            }
        }
        
        async function viewBulletin(segment) {
            try {
                const response = await fetch(`/api/bulletins/view/${segment}`);
                const result = await response.json();
                
                if (!result.success) {
                    alert(`Erro ao carregar boletim: ${result.error}`);
                    return;
                }
                
                const bulletin = result.bulletin;
                const modal = document.getElementById('bulletinModal');
                const modalContent = document.getElementById('modalContent');
                
                // Renderiza conteúdo principal
                let html = `
                    <h2>${bulletin.title}</h2>
                    <p><strong>Segmento:</strong> ${bulletin.segment}</p>
                    <p><strong>Artigos analisados:</strong> ${bulletin.articles_count}</p>
                    <p><strong>Data de geração:</strong> ${new Date(bulletin.generated_date).toLocaleString('pt-BR')}</p>
                    <hr>
                    <div style=\"margin-top: 20px;\">
                        ${bulletin.html_content}
                    </div>
                `;

                // Top 15 com resumos
                const summaries = bulletin.article_summaries || [];
                if (summaries.length) {
                    html += '<hr><h3 style=\"margin-top:20px;\">Top 15 com Resumos</h3>';
                    html += '<ol style=\"margin-top:10px;\">';
                    summaries.forEach(s => {
                        const t = (s.title||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        const u = s.url || '#';
                        const src = s.source || '';
                        const dt = s.published || '';
                        const sm = (s.summary||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        html += `<li style=\"margin-bottom:10px;\">`
                             + `<a href=\"${u}\" target=\"_blank\">${t}</a>`
                             + `<div style=\"font-size:12px;color:#666;\">Fonte: ${src} • Data: ${dt}</div>`
                             + (sm ? `<details style=\"margin-top:4px;\"><summary>ver resumo</summary><div style=\"margin-top:6px;\">${sm}</div></details>` : '')
                             + `</li>`;
                    });
                    html += '</ol>';
                }

                modalContent.innerHTML = html;
                
                modal.style.display = 'block';
                
            } catch (error) {
                alert(`Erro ao visualizar boletim: ${error.message}`);
            }
        }
        
        function downloadBulletin(segment) {
            window.open(`/api/bulletins/download/${segment}`, '_blank');
        }
        
        function closeModal() {
            document.getElementById('bulletinModal').style.display = 'none';
        }
        
        async function loadCollectionData() {
            const container = document.getElementById('collectionResults');
            
            try {
                const response = await fetch('/api/collection_results');
                const result = await response.json();
                
                if (!result.success) {
                    container.innerHTML = `<div class="error">Erro ao carregar dados de coleta: ${result.error}</div>`;
                    return;
                }
                
                const data = result.data;
                const stats = data.stats || {};
                const report = data.report_by_source || {};
                
                let html = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>Total de Artigos</h3>
                            <div class="value">${stats.ai_articles || 0}</div>
                            <div class="label">artigos coletados</div>
                        </div>
                        <div class="stat-card">
                            <h3>Fontes Processadas</h3>
                            <div class="value">${stats.successful_feeds || 0}</div>
                            <div class="label">fontes de notícias</div>
                        </div>
                        <div class="stat-card">
                            <h3>Tempo de Coleta</h3>
                            <div class="value">${stats.collection_time || 0}s</div>
                            <div class="label">tempo de execução</div>
                        </div>
                        <div class="stat-card">
                            <h3>Remoções</h3>
                            <div class="value">URL: ${stats.duplicates_removed_url||0} / Título: ${stats.duplicates_removed_title||0}</div>
                            <div class="label">duplicatas removidas</div>
                        </div>
                    </div>
                    <h4 style="margin-top:20px;">Relatório por Fonte</h4>
                `;
                
                // Tabela de fontes com títulos/links
                html += '<div style="margin-top:10px;">';
                Object.keys(report).forEach(src => {
                    const entry = report[src];
                    html += `<div class="stat-card" style="margin-bottom:15px;">`;
                    html += `<h3>${src} — ${entry.count} artigos</h3>`;
                    html += `<ul style="margin-top:10px;">`;
                    (entry.articles||[]).slice(0,50).forEach(a => {
                        const t = (a.title||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        const u = a.url || '#';
                        html += `<li><a href="${u}" target="_blank">${t}</a></li>`;
                    });
                    html += `</ul>`;
                    html += `</div>`;
                });
                html += '</div>';
                
                container.innerHTML = html;
                
            } catch (error) {
                container.innerHTML = `<div class="error">Erro de conexão: ${error.message}</div>`;
            }
        }
        
        async function loadSegmentTab(segKey, containerId) {
            const container = document.getElementById(containerId);
            container.innerHTML = '<div class="loading">Carregando...</div>';
            try {
                const [bulletinResp, segResp] = await Promise.all([
                    fetch(`/api/bulletins/view/${segKey}`),
                    fetch('/api/segmentation_results')
                ]);
                const bulletinResult = await bulletinResp.json();
                const segResult = await segResp.json();
                if (!bulletinResult.success) {
                    container.innerHTML = `<div class="error">${bulletinResult.error || 'Boletim não encontrado'}</div>`;
                    return;
                }
                if (!segResult.success) {
                    container.innerHTML = `<div class="error">${segResult.error || 'Dados de segmentação não encontrados'}</div>`;
                    return;
                }
                const bulletin = bulletinResult.bulletin;
                const data = segResult.data;
                const selection = (data.selection_by_segment || {});
                const segmented = (data.segmented_results || {});
                const selectedList = selection[segKey] || [];
                const segmentedList = segmented[segKey] || [];

                let html = '';
                // Boletim (inline, copiável)
                html += '<h4>Boletim</h4>';
                html += `<div class="stat-card" style="margin-bottom:15px; border-left-color:#28a745;">${bulletin.html_content}</div>`;

                // Top 15, texto integral (sem dropdown)
                html += '<h4 style="margin-top:20px;">Top 15 Selecionados (texto integral)</h4>';
                if (!selectedList.length) {
                    html += '<div class="error">Nenhum selecionado</div>';
                } else {
                    selectedList.forEach(a => {
                        const t = (a.title||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        const u = a.url || '#';
                        const src = a.source || '';
                        const dt = a.published || '';
                        const content = (a.content||'').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>');
                        html += `<div class=\"stat-card\" style=\"margin-bottom:15px;\">`;
                        html += `<h3><a href=\"${u}\" target=\"_blank\">${t}</a></h3>`;
                        html += `<div style=\"font-size:12px;color:#666;\">Fonte: ${src} • Data: ${dt}</div>`;
                        html += `<div style=\"margin-top:8px;\">${content}</div>`;
                        html += `</div>`;
                    });
                }

                // Todas segmentadas (títulos e links)
                html += '<h4 style="margin-top:20px;">Todas as segmentadas (títulos e links)</h4>';
                if (!segmentedList.length) {
                    html += '<div class="error">Sem itens</div>';
                } else {
                    html += '<div class="stat-card" style="margin-bottom:15px;"><ul>';
                    segmentedList.forEach(a => {
                        const t = (a.title||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        const u = a.url || '#';
                        html += `<li><a href=\"${u}\" target=\"_blank\">${t}</a></li>`;
                    });
                    html += '</ul></div>';
                }

                container.innerHTML = html;
            } catch (error) {
                container.innerHTML = `<div class=\"error\">Erro: ${error.message}</div>`;
            }
        }
        
        async function sendEmail() {
            const el = document.getElementById('emailResult');
            el.innerHTML = '<div class="loading">Enviando...</div>';
            try {
                const resp = await fetch('/api/email/send-latest', { method: 'POST' });
                const result = await resp.json();
                if (result.success) {
                    const count = (result.result && result.result.total_recipients) || 0;
                    el.innerHTML = `<div class=\"success\">Email enviado com sucesso para ${count} destinatários</div>`;
                } else {
                    el.innerHTML = `<div class=\"error\">Erro: ${result.error || 'Falha no envio'}</div>`;
                }
            } catch (e) {
                el.innerHTML = `<div class=\"error\">Erro: ${e.message}</div>`;
            }
        }
        
        
        
        async function loadPipelineData() {
            const container = document.getElementById('pipelineResults');
            
            try {
                const response = await fetch('/api/pipeline_results');
                const result = await response.json();
                
                if (!result.success) {
                    container.innerHTML = `<div class="error">Erro ao carregar dados do pipeline: ${result.error}</div>`;
                    return;
                }
                
                const data = result.data;
                const summary = data.summary || {};
                const pipelineStats = data.pipeline_stats || {};
                
                let html = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>Status</h3>
                            <div class="value">${data.status === 'success' ? '✅ Sucesso' : '❌ Erro'}</div>
                            <div class="label">status da execução</div>
                        </div>
                        <div class="stat-card">
                            <h3>Tempo Total</h3>
                            <div class="value">${summary.execution_time || 0}s</div>
                            <div class="label">tempo de execução</div>
                        </div>
                        <div class="stat-card">
                            <h3>Boletins Gerados</h3>
                            <div class="value">${summary.bulletins_generated || 0}</div>
                            <div class="label">boletins criados</div>
                        </div>
                        <div class="stat-card">
                            <h3>Data de Execução</h3>
                            <div class="value">${new Date(data.execution_date).toLocaleDateString('pt-BR')}</div>
                            <div class="label">última execução</div>
                        </div>
                    </div>
                `;
                
                container.innerHTML = html;
                
            } catch (error) {
                container.innerHTML = `<div class="error">Erro de conexão: ${error.message}</div>`;
            }
        }
        
        async function loadStats() {
            const container = document.getElementById('statsGrid');
            
            try {
                const response = await fetch('/api/stats');
                const result = await response.json();
                
                if (!result.success) {
                    container.innerHTML = `<div class="error">Erro ao carregar estatísticas: ${result.error}</div>`;
                    return;
                }
                
                const stats = result.stats;
                const collectionStats = stats.collection_stats || {};
                const generationStats = stats.generation_stats || {};
                
                let html = `
                    <div class="stat-card">
                        <h3>Artigos Coletados</h3>
                        <div class="value">${collectionStats.ai_articles || 0}</div>
                        <div class="label">última coleta</div>
                    </div>
                    <div class="stat-card">
                        <h3>Boletins Gerados</h3>
                        <div class="value">${generationStats.successful_bulletins || 0}</div>
                        <div class="label">última geração</div>
                    </div>
                    <div class="stat-card">
                        <h3>Fontes Processadas</h3>
                        <div class="value">${collectionStats.successful_feeds || 0}</div>
                        <div class="label">fontes ativas</div>
                    </div>
                    <div class="stat-card">
                        <h3>Status do Sistema</h3>
                        <div class="value">${collectionStats.ai_articles > 0 ? '✅ Ativo' : '⚠️ Inativo'}</div>
                        <div class="label">status geral</div>
                    </div>
                `;
                
                container.innerHTML = html;
                
            } catch (error) {
                container.innerHTML = `<div class="error">Erro de conexão: ${error.message}</div>`;
            }
        }
        
        function loadData() {
            loadStats();
            loadCollectionData();
        }
        
        // Carrega dados automaticamente quando a página carrega
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
        });
        
        // Atualiza dados a cada 30 segundos
        setInterval(loadData, 30000);
        
        // Fecha modal ao clicar fora dele
        window.onclick = function(event) {
            const modal = document.getElementById('bulletinModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""
    
    # Cria diretório templates se não existir
    os.makedirs(Config.TEMPLATES_DIR, exist_ok=True)
    
    # Salva o template
    with open(f'{Config.TEMPLATES_DIR}/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info("Template HTML criado com sucesso")

def start_visualizer(host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Inicia o visualizador web"""
    try:
        # Sempre recria o template HTML para refletir alterações
        logger.info("(Re)criando template HTML...")
        create_html_template()
        
        # Inicia visualizador
        visualizer = BoletinsVisualizer(host, port)
        visualizer.start(debug)
        
    except Exception as e:
        logger.error(f"Erro ao iniciar visualizador: {e}")
        raise

def main():
    """Função principal para iniciar o visualizador"""
    print("Iniciando Visualizador Web...")
    print("Acesse: http://127.0.0.1:5000")
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/visualizer.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria diretórios necessários
    Config.create_directories()
    
    start_visualizer()

if __name__ == "__main__":
    main()
