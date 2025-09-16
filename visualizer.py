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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_cors import CORS

from config import Config

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
        
        # Removido: pipeline_results (IA desligada)
        
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
                # 1) Tenta abrir boletins (IA) se existir
                latest_bulletins = f"{Config.OUTPUT_DIR}/latest_bulletins.json"
                if os.path.exists(latest_bulletins):
                    with open(latest_bulletins, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    bulletins = data.get('bulletins', {})
                    bulletin_info = bulletins.get(segment)
                    if bulletin_info and bulletin_info.get('status') == 'success':
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

                # 2) Fallback Sem IA: monta exibição a partir da seleção Top15
                latest_selection = f"{Config.OUTPUT_DIR}/latest_selection.json"
                sel_map = {}
                if os.path.exists(latest_selection):
                    with open(latest_selection, 'r', encoding='utf-8') as f:
                        sel_map = (json.load(f) or {}).get('selection_by_segment', {}) or {}
                if not sel_map:
                    # tentativa a partir do arquivo de segmentação completo
                    latest_seg = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
                    if os.path.exists(latest_seg):
                        with open(latest_seg, 'r', encoding='utf-8') as f:
                            seg_data = json.load(f) or {}
                        sel_map = seg_data.get('selection_by_segment', {}) or {}

                selected = sel_map.get(segment) or []
                if selected:
                    # Gera um HTML simples com os 15 integrais como fallback
                    def esc(t: str) -> str:
                        return (t or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
                    seg_name = (Config.SEGMENTS.get(segment, {}).get('name')) or segment
                    parts: List[str] = []
                    parts.append(f"<h2>Top 15 — {esc(seg_name)}</h2>")
                    parts.append('<div style="margin-top:10px;">')
                    for i, a in enumerate(selected, 1):
                        title = esc(a.get('title') or '')
                        src = esc(a.get('source') or '')
                        dt = esc(a.get('published') or '')
                        url = a.get('url') or '#'
                        content = esc(a.get('content') or '')
                        parts.append('<div class="stat-card" style="margin-bottom:12px;">')
                        parts.append(f'<div class="title">{i}. <a href="{url}" target="_blank">{title}</a></div>')
                        parts.append(f'<div class="meta">Fonte: {src} • Data: {dt}</div>')
                        parts.append(f'<div class="content" style="margin-top:6px; white-space:pre-wrap;">{content}</div>')
                        parts.append('</div>')
                    parts.append('</div>')
                    html_content = '\n'.join(parts)
                    return jsonify({
                        'success': True,
                        'bulletin': {
                            'segment': segment,
                            'title': f'Sem IA — {seg_name}',
                            'articles_count': len(selected),
                            'generated_date': datetime.now().isoformat(),
                            'method': 'sem_ia_fallback',
                            'formatted_text': '',
                            'html_content': html_content,
                            'status': 'success',
                            'selected_articles': selected,
                            'article_summaries': []
                        }
                    })

                # 3) Nada encontrado
                return jsonify({
                    'success': False,
                    'error': f'Boletim não encontrado para o segmento: {segment}'
                }), 404
                
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
                    'keywords_by_segment': self._get_keywords_by_segment(),
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

        @self.app.route('/api/logs/collector')
        def api_log_collector():
            try:
                log_path = f"{Config.LOGS_DIR}/collector.log"
                if not os.path.exists(log_path):
                    return Response("(collector.log ainda não existe)", mimetype='text/plain; charset=utf-8')
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return Response(f.read(), mimetype='text/plain; charset=utf-8')
            except Exception as e:
                return Response(f"Erro ao ler collector.log: {e}", mimetype='text/plain; charset=utf-8', status=500)

        @self.app.route('/api/logs/pipeline')
        def api_log_pipeline():
            try:
                log_path = f"{Config.LOGS_DIR}/pipeline.log"
                if not os.path.exists(log_path):
                    return Response("(pipeline.log ainda não existe)", mimetype='text/plain; charset=utf-8')
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return Response(f.read(), mimetype='text/plain; charset=utf-8')
            except Exception as e:
                return Response(f"Erro ao ler pipeline.log: {e}", mimetype='text/plain; charset=utf-8', status=500)

        @self.app.route('/api/email/preview', methods=['GET'])
        def preview_email():
            """Gera uma prévia HTML do email com resumo do pipeline e boletins"""
            try:
                collection_file = f"{Config.OUTPUT_DIR}/latest_collection.json"
                segmentation_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
                bulletins_file = f"{Config.OUTPUT_DIR}/latest_bulletins.json"

                collection = {}
                segmentation = {}
                bulletins = {}
                if os.path.exists(collection_file):
                    with open(collection_file, 'r', encoding='utf-8') as f:
                        collection = json.load(f)
                if os.path.exists(segmentation_file):
                    with open(segmentation_file, 'r', encoding='utf-8') as f:
                        segmentation = json.load(f)
                if os.path.exists(bulletins_file):
                    with open(bulletins_file, 'r', encoding='utf-8') as f:
                        bulletins = json.load(f)

                col_stats = (collection.get('stats', {}) if isinstance(collection, dict) else {}) or {}
                seg_stats = (segmentation.get('stats', {}) if isinstance(segmentation, dict) else {}) or {}
                bulletins_map = (bulletins.get('bulletins', {}) if isinstance(bulletins, dict) else {}) or {}

                total_coletadas = col_stats.get('total_articles', 0)
                aprovadas_ia = col_stats.get('ai_articles', seg_stats.get('total_articles', 0)) or 0
                filtradas = seg_stats.get('filtered_articles', max(0, total_coletadas - aprovadas_ia))
                dedup_url = col_stats.get('duplicates_removed_url', 0)
                dedup_title = col_stats.get('duplicates_removed_title', 0)
                segmentadas = seg_stats.get('total_articles', aprovadas_ia) or 0
                selecionadas = 0
                for info in bulletins_map.values():
                    if isinstance(info, dict) and info.get('status') == 'success':
                        selecionadas += int(info.get('articles_count', 0))

                # Monta HTML de prévia
                html = []
                html.append('<div class="stat-card" style="margin-bottom:15px;">')
                html.append('<h2 style="margin-bottom:10px;">Prévia do Email - Boletins IA</h2>')
                html.append('<div style="color:#666; font-size:14px;">Resumo do pipeline</div>')
                html.append('<ul style="margin-left:18px; margin-top:10px;">')
                html.append(f'<li><strong>Coletadas</strong>: {total_coletadas}</li>')
                html.append(f'<li><strong>Filtradas</strong>: {filtradas} (eliminação + bloqueios + ruído)</li>')
                html.append(f'<li><strong>Aprovadas (IA)</strong>: {aprovadas_ia}</li>')
                html.append(f'<li><strong>Segmentadas</strong>: {segmentadas}</li>')
                html.append(f'<li><strong>Selecionadas (Top 15)</strong>: {selecionadas}</li>')
                html.append(f'<li><strong>Deduplicação</strong>: por URL {dedup_url} • por Título {dedup_title}</li>')
                html.append('</ul>')
                html.append('</div>')

                # Boletins por segmento (texto + lista de links usados)
                for seg_key, info in bulletins_map.items():
                    if not isinstance(info, dict) or info.get('status') != 'success':
                        continue
                    title = info.get('title', seg_key)
                    generated_date = info.get('generated_date', '')
                    html_content = self._convert_text_to_html(info.get('ai_generated_text', ''))
                    selected = info.get('selected_articles', []) or []

                    html.append('<div class="stat-card" style="margin-bottom:15px; border-left-color:#667eea;">')
                    html.append(f'<div class="bulletin-title">{title}</div>')
                    html.append(f'<div class="bulletin-meta" style="margin:6px 0 12px 0; color:#666; font-size:12px;">Gerado em: {generated_date} • Artigos: {info.get("articles_count", 0)}</div>')
                    html.append(f'<div style="margin-top:8px;">{html_content}</div>')
                    # Lista de artigos (apenas título + link)
                    if selected:
                        html.append('<div style="margin-top:12px;"><strong>Artigos utilizados</strong></div>')
                        html.append('<ol style="margin-top:6px;">')
                        for a in selected:
                            t = (a.get('title','') or '').replace('<','&lt;').replace('>','&gt;')
                            u = a.get('url','') or '#'
                            html.append(f'<li><a href="{u}" target="_blank">{t}</a></li>')
                        html.append('</ol>')
                    html.append('</div>')

                return jsonify({'success': True, 'html': ''.join(html)})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/email/send-latest', methods=['POST'])
        def send_latest_email():
            """Envia por email os Top 15 integrais por segmento (Sem IA),
            montando o HTML a partir do latest_selection.json.
            Body opcional: { "recipients": ["a@x","b@y"] }
            """
            try:
                selection_file = f"{Config.OUTPUT_DIR}/latest_selection.json"
                segmentation_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"

                selection = {}
                if os.path.exists(selection_file):
                    with open(selection_file, 'r', encoding='utf-8') as f:
                        sel_data = json.load(f) or {}
                    selection = sel_data.get('selection_by_segment') or {}

                # Fallback por segmento a partir do arquivo de segmentação, se necessário
                seg_selection = {}
                if os.path.exists(segmentation_file):
                    try:
                        with open(segmentation_file, 'r', encoding='utf-8') as f:
                            seg_data = json.load(f) or {}
                        seg_selection = seg_data.get('selection_by_segment', {}) or {}
                    except Exception:
                        seg_selection = {}

                if not selection and not seg_selection:
                    return jsonify({'success': False, 'error': 'Nenhuma seleção Top15 encontrada. Rode a segmentação antes.'}), 404

                payload = request.get_json(silent=True) or {}
                recs_override = payload.get('recipients')

                # Destinatários e credenciais
                smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
                smtp_port = int(os.getenv('SMTP_PORT', '587'))
                email_user = os.getenv('EMAIL_USER')
                email_password = os.getenv('EMAIL_PASSWORD')
                if isinstance(recs_override, list) and recs_override:
                    recipients = [str(x).strip() for x in recs_override if str(x).strip()]
                else:
                    recipients = [r.strip() for r in (os.getenv('EMAIL_RECIPIENTS') or '').split(',') if r.strip()]

                missing = []
                if not email_user: missing.append('EMAIL_USER')
                if not email_password: missing.append('EMAIL_PASSWORD')
                if not recipients: missing.append('EMAIL_RECIPIENTS')
                if missing:
                    return jsonify({'success': False, 'error': 'Configuração de email inválida: ' + ', '.join(missing)}), 400

                def esc(t: str) -> str:
                    return (t or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

                # Monta HTML com 15 integrais por segmento (layout organizado)
                seg_order = [
                    'marketing_comunicacao_jornalismo',
                    'direito_corporativo_tributario_trabalhista',
                    'recursos_humanos_gestao_pessoas',
                ]
                seg_names = {k: (Config.SEGMENTS.get(k, {}).get('name') or k) for k in seg_order}

                # Envia um email por segmento para evitar clipping e garantir inclusão do RH
                from datetime import datetime as _dt
                date_str = _dt.now().strftime('%d/%m/%Y %H:%M')
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(email_user, email_password)

                segments_sent = 0
                for seg in seg_order:
                    arts = selection.get(seg) or seg_selection.get(seg) or []
                    if not arts:
                        continue
                    seg_title = esc(seg_names[seg])
                    parts: List[str] = []
                    parts.append('<!DOCTYPE html>')
                    parts.append('<html lang="pt-BR">')
                    parts.append('<head>')
                    parts.append('<meta charset="UTF-8">')
                    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
                    parts.append(f'<title>Top 15 integrais — {seg_title}</title>')
                    parts.append('<style>')
                    parts.append('body{font-family:Segoe UI,Arial,sans-serif;line-height:1.6;color:#222;margin:0;padding:0;background:#ffffff;}')
                    parts.append('.container{max-width:860px;margin:0 auto;padding:24px;}')
                    parts.append('.header{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:20px;border-radius:10px;margin-bottom:18px;}')
                    parts.append('.header h1{margin:0 0 6px 0;font-size:22px;} .header .meta{font-size:12px;opacity:.9;}')
                    parts.append('.card{background:#f8f9fa;border-left:4px solid #667eea;padding:12px 14px;margin:10px 0;border-radius:6px;}')
                    parts.append('.title{font-weight:700;margin-bottom:4px;} .meta{color:#666;font-size:12px;}')
                    parts.append('.content{margin-top:8px;white-space:pre-wrap;font-family:Segoe UI,Arial,sans-serif;}')
                    parts.append('.refs{margin-top:10px;} .refs ol{margin:6px 0 0 18px;} .refs li{margin:3px 0;}')
                    parts.append('.footer{color:#666;font-size:12px;margin-top:18px;text-align:center;}')
                    parts.append('</style>')
                    parts.append('</head>')
                    parts.append('<body>')
                    parts.append('<div class="container">')
                    parts.append('<div class="header">')
                    parts.append(f'<h1>Notícias coletadas {esc(date_str)} - {seg_title}</h1>')
                    parts.append(f'<div class="meta">Gerado em {esc(date_str)} — pronto para copiar e colar em uma LLM</div>')
                    parts.append('</div>')

                    for i, a in enumerate(arts, 1):
                        title = esc(a.get('title') or '')
                        src = esc(a.get('source') or '')
                        dt = esc(a.get('published') or '')
                        url = a.get('url') or ''
                        content = esc(a.get('content') or '')
                        parts.append('<div class="card">')
                        parts.append(f'<div class="title">{i}. {title}</div>')
                        parts.append(f'<div class="meta">Fonte: {src} • Data: {dt} • <a href="{url}" target="_blank">{esc(url)}</a></div>')
                        parts.append(f'<div class="content">{content}</div>')
                        parts.append('</div>')

                    parts.append('<div class="refs"><strong>Referências</strong><ol>')
                    for i, a in enumerate(arts, 1):
                        title = esc(a.get('title') or '')
                        url = a.get('url') or ''
                        src = esc(a.get('source') or '')
                        dt = esc(a.get('published') or '')
                        parts.append(f'<li>{title} — {src} — {dt} — <a href="{url}" target="_blank">{esc(url)}</a></li>')
                    parts.append('</ol></div>')
                    parts.append('<div class="footer">Boletins IA (Sem IA) — este email contém o conteúdo integral dos 15 artigos do segmento, em formato copiável.</div>')
                    parts.append('</div>')
                    parts.append('</body></html>')
                    html_body = '\n'.join(parts)

                    msg = MIMEMultipart('alternative')
                    msg['From'] = email_user
                    msg['To'] = ', '.join(recipients)
                    msg['Subject'] = f'Notícias coletadas {date_str} - {seg_title}'
                    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                    server.sendmail(email_user, recipients, msg.as_string())
                    segments_sent += 1

                server.quit()

                return jsonify({'success': True, 'result': {'total_recipients': len(recipients), 'segments_sent': segments_sent}})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

        @self.app.route('/api/export/plaintext')
        def export_plaintext():
            """Gera um texto único com os 15 artigos por segmento (conteúdo completo),
            seguido de títulos e links, para copiar e colar manualmente em um LLM.
            Query param: segment = { 'direito_corporativo_tributario_trabalhista' | 'marketing_comunicacao_jornalismo' | 'recursos_humanos_gestao_pessoas' | 'all' }
            """
            try:
                segment_req = (request.args.get('segment') or 'all').strip().lower()
                selection_file = f"{Config.OUTPUT_DIR}/latest_selection.json"
                segmentation_file = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
                selection = {}
                if os.path.exists(selection_file):
                    with open(selection_file, 'r', encoding='utf-8') as f:
                        selection = (json.load(f) or {}).get('selection_by_segment', {})
                else:
                    # Fallback: tentar do arquivo de segmentação
                    if os.path.exists(segmentation_file):
                        with open(segmentation_file, 'r', encoding='utf-8') as f:
                            seg_data = json.load(f) or {}
                        selection = seg_data.get('selection_by_segment', {}) or {}

                if not selection:
                    return jsonify({'success': False, 'error': 'Nenhuma seleção Top15 encontrada.'}), 404

                segments_order = [
                    'direito_corporativo_tributario_trabalhista',
                    'marketing_comunicacao_jornalismo',
                    'recursos_humanos_gestao_pessoas'
                ]
                if segment_req != 'all':
                    segments_order = [s for s in segments_order if s == segment_req]

                parts: List[str] = []
                for seg_key in segments_order:
                    articles = selection.get(seg_key) or []
                    if not articles:
                        continue
                    seg_conf = Config.SEGMENTS.get(seg_key, {'name': seg_key})
                    seg_title = seg_conf.get('name', seg_key)
                    parts.append(f"### SEGMENTO: {seg_title}\n")

                    # Conteúdo integral dos 15
                    for i, a in enumerate(articles, 1):
                        title = a.get('title','') or ''
                        src = a.get('source','') or ''
                        dt = a.get('published','') or ''
                        url = a.get('url','') or ''
                        content = a.get('content','') or ''
                        parts.append(f"{i}. {title}\nFonte: {src}\nData: {dt}\nLink: {url}\n\n{content}\n\n---\n")

                    # Lista de títulos e links ao final
                    parts.append("Referências (títulos e links):")
                    for i, a in enumerate(articles, 1):
                        title = a.get('title','') or ''
                        url = a.get('url','') or ''
                        src = a.get('source','') or ''
                        dt = a.get('published','') or ''
                        parts.append(f"- {i}. {title} — {src} — {dt} — {url}")

                    parts.append("\n\n")

                text = "\n".join(parts).strip()
                return jsonify({'success': True, 'text': text})
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

    def _get_keywords_by_segment(self) -> Dict[str, List[List[Any]]]:
        """Gera top palavras por segmento a partir do Top 15 (latest_selection.json)."""
        try:
            latest_selection = f"{Config.OUTPUT_DIR}/latest_selection.json"
            if not os.path.exists(latest_selection):
                return {}
            with open(latest_selection, 'r', encoding='utf-8') as f:
                sel = json.load(f) or {}
            selection = sel.get('selection_by_segment', {}) or {}
            stop = {
                'de','da','do','das','dos','a','o','os','as','e','é','em','para','por','com','um','uma','no','na','nos','nas','que','se','sua','seu','suas','seus','ao','à','às','aos','mais','menos','entre','sobre','como','já','não','sim','ou','também','foi','são','ser','tem','há','após','até','desde','quando','onde','qual','quais','porque','porquê','isso','isto','aquele','aquela','aquilo','lo','la','lhe','eles','elas','ele','ela','d','p','r','t','s','&','–','-'
            }
            import re as _re
            from collections import Counter
            result: Dict[str, List[List[Any]]] = {}
            for seg_key in Config.SEGMENTS.keys():
                arts = selection.get(seg_key) or []
                if not arts:
                    result[seg_key] = []
                    continue
                text_parts: List[str] = []
                for a in arts:
                    text_parts.append(a.get('title') or '')
                    text_parts.append(a.get('content') or '')
                text = ' '.join(text_parts).lower()
                tokens = _re.findall(r"\b\w+\b", text, flags=_re.UNICODE)
                tokens = [w for w in tokens if len(w) >= 3 and w not in stop]
                counts = Counter(tokens)
                top = counts.most_common(50)
                result[seg_key] = [[w, int(c)] for w, c in top]
            return result
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
    <div class="container">
        <button class="refresh-btn" onclick="loadData()">🔄 Atualizar Dados</button>

        <div class="tabs">
            <div class="tab-headers">
                <div class="tab-header active" onclick="showTab('collection', this)">Coleta</div>
                <div class="tab-header" onclick="showTab('direito', this)">Direito</div>
                <div class="tab-header" onclick="showTab('comunicacao', this)">Comunicação</div>
                <div class="tab-header" onclick="showTab('rh', this)">RH</div>
                <div class="tab-header" onclick="showTab('pipeline', this)">Pipeline</div>
                <div class="tab-header" onclick="showTab('email', this)">Email</div>
                <div class="tab-header" onclick="showTab('semia', this)">Sem IA</div>
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
                        <label for="emailRecipients" style="font-weight:600;display:block;margin-top:10px;">Destinatários (separados por vírgula)</label>
                        <input id="emailRecipients" type="text" placeholder="destino1@dominio.com, destino2@dominio.com" style="width:100%; padding:8px; margin:8px 0;" />
                        <div style="font-size:12px;color:#666; margin-bottom:10px;">Se vazio, usará EMAIL_RECIPIENTS do .env</div>
                        <button class="btn btn-primary" onclick="sendEmail()">Enviar últimos boletins por email</button>
                        <div id="emailResult" style="margin-top:10px;"></div>
                    </div>
                </div>

                <div id="semia" class="tab-panel">
                    <h3>Sem IA — Lousa para copiar e colar no GPT</h3>
                    <div class="stat-card" style="margin-top:10px;">
                        <label for="semIaSegment" style="font-weight:600;">Segmento</label>
                        <select id="semIaSegment" style="margin: 6px 0; padding:6px;">
                            <option value="all">Todos os segmentos</option>
                            <option value="direito_corporativo_tributario_trabalhista">Direito Corporativo, Tributário, Trabalhista</option>
                            <option value="marketing_comunicacao_jornalismo">Marketing, Comunicação e Jornalismo</option>
                            <option value="recursos_humanos_gestao_pessoas">Recursos Humanos e Gestão de Pessoas</option>
                        </select>
                        <button class="btn btn-primary" onclick="loadSemIaText()">Carregar texto</button>
                        <button class="btn btn-secondary" onclick="copySemIaText()" style="margin-left:8px;">Copiar</button>
                        <div style="margin-top:10px;">
                            <textarea id="semIaTextarea" style="width:100%; height:380px; font-family: Consolas, 'Courier New', monospace; font-size: 13px;" placeholder="Clique em Carregar texto para preencher com os artigos selecionados (Top 15) em formato copiável..."></textarea>
                        </div>
                        <div id="semIaStatus" style="margin-top:8px; color:#666; font-size:12px;"></div>
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
                case 'semia':
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
        
        async function loadSemIaText() {
            const sel = document.getElementById('semIaSegment');
            const out = document.getElementById('semIaTextarea');
            const statusEl = document.getElementById('semIaStatus');
            out.value = '';
            statusEl.innerText = 'Carregando...';
            try {
                const seg = sel ? sel.value : 'all';
                const resp = await fetch(`/api/export/plaintext?segment=${encodeURIComponent(seg)}`);
                const data = await resp.json();
                if (!data.success) {
                    statusEl.innerText = `Erro: ${data.error || 'Falha ao gerar texto'}`;
                    return;
                }
                out.value = data.text || '';
                statusEl.innerText = 'Pronto. Use o botão Copiar.';
            } catch (e) {
                statusEl.innerText = `Erro: ${e.message}`;
            }
        }

        async function copySemIaText() {
            const out = document.getElementById('semIaTextarea');
            const statusEl = document.getElementById('semIaStatus');
            try {
                await navigator.clipboard.writeText(out.value || '');
                statusEl.innerText = 'Conteúdo copiado para a área de transferência.';
            } catch (e) {
                statusEl.innerText = 'Falha ao copiar. Selecione o texto e copie manualmente (Ctrl+C).';
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
                const segResp = await fetch('/api/segmentation_results');
                const segResult = await segResp.json();
                if (!segResult.success) {
                    container.innerHTML = `<div class="error">${segResult.error || 'Dados de segmentação não encontrados'}</div>`;
                    return;
                }
                const data = segResult.data;
                const selection = (data.selection_by_segment || {});
                const segmented = (data.segmented_results || {});
                const selectedList = selection[segKey] || [];
                const segmentedList = segmented[segKey] || [];

                let html = '';
                // Lista resumida (títulos e links) dos Top 15
                html += '<h4 style="margin-top:0;">Top 15 Selecionados (títulos e links)</h4>';
                if (!selectedList.length) {
                    html += '<div class="error">Nenhum selecionado</div>';
                } else {
                    html += '<div class="stat-card" style="margin-bottom:15px;"><ol style="margin-left:18px;">';
                    selectedList.forEach(a => {
                        const t = (a.title||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        const u = a.url || '#';
                        html += `<li style=\"margin-bottom:6px;\"><a href=\"${u}\" target=\"_blank\">${t}</a></li>`;
                    });
                    html += '</ol></div>';
                }

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
                const inputEl = document.getElementById('emailRecipients');
                const recStr = inputEl ? (inputEl.value || '') : '';
                const payload = {};
                if (recStr && recStr.trim()) {
                    payload.recipients = recStr.split(',').map(s => s.trim()).filter(Boolean);
                }
                const resp = await fetch('/api/email/send-latest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
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
                const resp = await fetch('/api/stats');
                const result = await resp.json();
                if (!result.success) {
                    container.innerHTML = `<div class="error">Erro ao carregar dados do pipeline: ${result.error}</div>`;
                    return;
                }
                const stats = result.stats || {};
                const col = stats.collection_stats || {};
                const seg = stats.segmentation_stats || {};
                const gen = stats.generation_stats || {};
                const srcq = stats.source_quality || {};
                const kw = stats.keywords_by_segment || {};

                let html = `
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h3>Coletados</h3>
                            <div class="value">${col.total_articles || 0}</div>
                            <div class="label">artigos coletados</div>
                        </div>
                        <div class="stat-card">
                            <h3>Segmentados</h3>
                            <div class="value">${seg.total_articles || 0}</div>
                            <div class="label">artigos segmentados</div>
                        </div>
                        <div class="stat-card">
                            <h3>IA aprovadas</h3>
                            <div class="value">${seg.ai_filtered || col.ai_articles || 0}</div>
                            <div class="label">passaram no filtro IA</div>
                        </div>
                        <div class="stat-card">
                            <h3>Deduplicação</h3>
                            <div class="value">URL: ${col.duplicates_removed_url||0} / Título: ${col.duplicates_removed_title||0}</div>
                            <div class="label">removidas</div>
                        </div>
                        <div class="stat-card">
                            <h3>Fontes</h3>
                            <div class="value">${col.successful_feeds || 0}</div>
                            <div class="label">fontes processadas</div>
                        </div>
                        <div class="stat-card">
                            <h3>Atualização</h3>
                            <div class="value">${new Date(stats.timestamp || Date.now()).toLocaleString('pt-BR')}</div>
                            <div class="label">última atualização</div>
                        </div>
                    </div>
                `;

                // Detalhe por segmento
                const segStats = (seg.segments_stats || {});
                const segKeys = Object.keys(segStats);
                if (segKeys.length) {
                    html += '<h4 style="margin-top:20px;">Por segmento</h4>';
                    html += '<div class="stat-card" style="margin-top:10px;">';
                    html += '<ul style="margin-left:16px;">';
                    segKeys.forEach(k => {
                        const v = segStats[k] || 0;
                        html += `<li><strong>${k}</strong>: ${v} artigos segmentados</li>`;
                    });
                    html += '</ul>';
                    html += '</div>';
                }

                // Qualidade por fonte
                const srcKeys = Object.keys(srcq);
                if (srcKeys.length) {
                    html += '<h4 style="margin-top:20px;">Qualidade por fonte</h4>';
                    html += '<div class="stat-card" style="margin-top:10px;">';
                    html += '<ul style="margin-left:16px;">';
                    srcKeys.forEach(k => {
                        const info = srcq[k] || {};
                        html += `<li><strong>${k}</strong>: coletados ${info.collected||0} • Top15 ${info.selected_top15||0} • taxa ${info.selection_rate||0}</li>`;
                    });
                    html += '</ul>';
                    html += '</div>';
                }

                // Palavras‑chave por segmento (Top 15)
                const kwSegs = Object.keys(kw);
                if (kwSegs.length) {
                    html += '<h4 style="margin-top:20px;">Palavras‑chave por segmento (Top 15)</h4>';
                    kwSegs.forEach(skey => {
                        const items = kw[skey] || [];
                        html += '<div class="stat-card" style="margin-top:10px;">';
                        html += `<div style=\"font-weight:600; margin-bottom:6px;\">${skey}</div>`;
                        if (!items.length) {
                            html += '<div style="color:#666;">Sem dados</div>';
                        } else {
                            html += '<ul style="margin-left:16px; columns: 2; -webkit-columns: 2; -moz-columns: 2;">';
                            items.slice(0,20).forEach(pair => {
                                const w = pair[0];
                                const c = pair[1];
                                html += `<li>${w}: ${c}</li>`;
                            });
                            html += '</ul>';
                        }
                        html += '</div>';
                    });
                }

                // Logs embutidos
                html += '<h4 style="margin-top:20px;">Logs</h4>';
                html += '<div class="stat-card" style="margin-top:10px;">';
                html += '<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">';
                html += '<div><div style="font-weight:600;">collector.log</div><iframe src="/api/logs/collector" style="width:100%; height:280px; border:1px solid #ddd; border-radius:6px; background:#fff;"></iframe></div>';
                html += '<div><div style="font-weight:600;">pipeline.log</div><iframe src="/api/logs/pipeline" style="width:100%; height:280px; border:1px solid #ddd; border-radius:6px; background:#fff;"></iframe></div>';
                html += '</div>';
                html += '</div>';

                container.innerHTML = html;
            } catch (error) {
                container.innerHTML = `<div class=\"error\">Erro de conexão: ${error.message}</div>`;
            }
        }
        
        function loadData() {
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
