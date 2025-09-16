"""
Tarefa semanal sem IA: coleta, segmentação e envio por email dos Top 15 integrais por segmento.

Requer variáveis de ambiente (.env ou secrets no CI):
- SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENTS

Saídas esperadas utilizadas:
- outputs/latest_collection.json (da coleta)
- outputs/latest_segmentation.json (da segmentação)
- outputs/latest_selection.json (seleção Top15 gravada pelo segmenter)
"""

import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no PYTHONPATH ao rodar via GitHub Actions
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

from config import Config
from collector import NewsCollector
from segmenter import NewsSegmenter


logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL), format=Config.LOG_FORMAT)
logger = logging.getLogger("weekly_task")


def _load_selection() -> Dict[str, List[Dict[str, Any]]]:
    path = f"{Config.OUTPUT_DIR}/latest_selection.json"
    if not os.path.exists(path):
        raise FileNotFoundError("latest_selection.json não encontrado. Execute a segmentação primeiro.")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f) or {}
    sel = data.get('selection_by_segment') or {}
    if not sel:
        raise RuntimeError("selection_by_segment vazio no latest_selection.json")
    return sel


def _html_escape(text: str) -> str:
    return (text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _build_segment_email_html(seg_key: str, articles: List[Dict[str, Any]]) -> str:
    seg_name = (Config.SEGMENTS.get(seg_key, {}).get('name')) or seg_key
    date_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    parts: List[str] = []
    parts.append('<!DOCTYPE html>')
    parts.append('<html lang="pt-BR">')
    parts.append('<head>')
    parts.append('<meta charset="UTF-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append(f'<title>Notícias coletadas {date_str} - {_html_escape(seg_name)}</title>')
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
    parts.append(f'<h1>Notícias coletadas {_html_escape(date_str)} - {_html_escape(seg_name)}</h1>')
    parts.append(f'<div class="meta">Pronto para copiar e colar em uma LLM</div>')
    parts.append('</div>')

    for i, a in enumerate(articles, 1):
        title = _html_escape(a.get('title') or '')
        src = _html_escape(a.get('source') or '')
        dt = _html_escape(a.get('published') or '')
        url = a.get('url') or ''
        content = _html_escape(a.get('content') or '')
        parts.append('<div class="card">')
        parts.append(f'<div class="title">{i}. {title}</div>')
        parts.append(f'<div class="meta">Fonte: {src} • Data: {dt} • <a href="{url}" target="_blank">{_html_escape(url)}</a></div>')
        parts.append(f'<div class="content">{content}</div>')
        parts.append('</div>')

    parts.append('<div class="refs"><strong>Referências</strong><ol>')
    for i, a in enumerate(articles, 1):
        title = _html_escape(a.get('title') or '')
        url = a.get('url') or ''
        src = _html_escape(a.get('source') or '')
        dt = _html_escape(a.get('published') or '')
        parts.append(f'<li>{title} — {src} — {dt} — <a href="{url}" target="_blank">{_html_escape(url)}</a></li>')
    parts.append('</ol></div>')
    parts.append('<div class="footer">Boletins IA (Sem IA) — este email contém o conteúdo integral dos 15 artigos do segmento, em formato copiável.</div>')
    parts.append('</div>')
    parts.append('</body></html>')
    return '\n'.join(parts)


def _send_email(html_body: str, subject: str) -> None:
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    email_user = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASSWORD')
    recipients = [r.strip() for r in (os.getenv('EMAIL_RECIPIENTS') or '').split(',') if r.strip()]

    missing = []
    if not email_user: missing.append('EMAIL_USER')
    if not email_password: missing.append('EMAIL_PASSWORD')
    if not recipients: missing.append('EMAIL_RECIPIENTS')
    if missing:
        raise RuntimeError('Campos faltantes: ' + ', '.join(missing))

    msg = MIMEMultipart('alternative')
    msg['From'] = email_user
    msg['To'] = ', '.join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(email_user, email_password)
    server.sendmail(email_user, recipients, msg.as_string())
    server.quit()


def run_weekly() -> None:
    load_dotenv()
    Config.create_directories()

    # Coleta
    collector = NewsCollector()
    col = collector.collect_articles(days_back=Config.DAYS_BACK, max_articles_per_source=Config.MAX_ARTICLES_PER_SOURCE)
    if col.get('status') == 'success':
        collector.save_results(col)
        logger.info(f"Coleta concluída: {col.get('stats',{}).get('ai_articles',0)} artigos")
    else:
        raise RuntimeError(f"Erro na coleta: {col.get('error')}")

    # Segmentação (gera latest_selection.json)
    segmenter = NewsSegmenter()
    seg = segmenter.segment_articles(col.get('articles', []))
    if seg.get('status') == 'success':
        segmenter.save_results(seg)
        logger.info("Segmentação concluída")
    else:
        raise RuntimeError(f"Erro na segmentação: {seg.get('error')}")

    # Email com Top15 integrais (um por segmento)
    # Carrega seleção com fallback para latest_segmentation.json, se necessário
    selection = {}
    try:
        selection = _load_selection()
    except Exception:
        segf = f"{Config.OUTPUT_DIR}/latest_segmentation.json"
        if os.path.exists(segf):
            with open(segf, 'r', encoding='utf-8') as f:
                seg_data = json.load(f) or {}
            selection = seg_data.get('selection_by_segment', {}) or {}
        else:
            raise

    seg_order = [
        'marketing_comunicacao_jornalismo',
        'direito_corporativo_tributario_trabalhista',
        'recursos_humanos_gestao_pessoas',
    ]
    seg_names = {k: (Config.SEGMENTS.get(k, {}).get('name') or k) for k in seg_order}
    sent_count = 0
    date_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    for seg in seg_order:
        arts = selection.get(seg) or []
        if not arts:
            continue
        html = _build_segment_email_html(seg, arts)
        subject = f"Notícias coletadas {date_str} - {seg_names[seg]}"
        _send_email(html, subject)
        sent_count += 1
    logger.info(f"Emails enviados por segmento: {sent_count}")


if __name__ == '__main__':
    run_weekly()


