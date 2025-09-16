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


def _build_selection_email_html(selection_by_segment: Dict[str, List[Dict[str, Any]]]) -> str:
    seg_order = [
        'marketing_comunicacao_jornalismo',
        'direito_corporativo_tributario_trabalhista',
        'recursos_humanos_gestao_pessoas',
    ]
    seg_names = {
        k: (Config.SEGMENTS.get(k, {}).get('name') or k) for k in seg_order
    }

    parts: List[str] = []
    parts.append('<div style="font-family:Segoe UI,Arial,sans-serif; line-height:1.5; color:#222;">')
    parts.append('<h1 style="margin:0 0 10px 0;">Top 15 integrais por segmento</h1>')
    parts.append(f'<div style="color:#666; font-size:13px;">Data: {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>')

    for seg in seg_order:
        arts = selection_by_segment.get(seg) or []
        if not arts:
            continue
        parts.append(f'<hr><h2 style="margin:16px 0 8px 0;">{_html_escape(seg_names[seg])}</h2>')
        # Bloco copiável: 15 integrais
        for i, a in enumerate(arts, 1):
            title = _html_escape(a.get('title') or '')
            src = _html_escape(a.get('source') or '')
            dt = _html_escape(a.get('published') or '')
            url = a.get('url') or ''
            content = _html_escape(a.get('content') or '')
            parts.append('<div style="background:#f8f9fa;border-left:4px solid #667eea;padding:12px;margin:10px 0;">')
            parts.append(f'<div style="font-weight:700;">{i}. {title}</div>')
            parts.append(f'<div style="color:#666; font-size:12px;">Fonte: {src} • Data: {dt} • <a href="{url}" target="_blank">link</a></div>')
            parts.append(f'<div style="margin-top:8px; white-space:pre-wrap;">{content}</div>')
            parts.append('</div>')
        # Lista final de títulos/links
        parts.append('<div style="margin-top:8px;"><strong>Referências</strong></div>')
        parts.append('<ol style="margin:6px 0 16px 18px;">')
        for i, a in enumerate(arts, 1):
            title = _html_escape(a.get('title') or '')
            url = a.get('url') or ''
            src = _html_escape(a.get('source') or '')
            dt = _html_escape(a.get('published') or '')
            parts.append(f'<li>{title} — {src} — {dt} — <a href="{url}" target="_blank">{url}</a></li>')
        parts.append('</ol>')

    parts.append('</div>')
    return '\n'.join(parts)


def _send_email(html_body: str) -> None:
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
    msg['Subject'] = 'Boletins IA (Sem IA) - Top 15 integrais por segmento'
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

    # Email com Top15 integrais
    selection = _load_selection()
    html = _build_selection_email_html(selection)
    _send_email(html)
    logger.info("Email enviado com os Top 15 integrais por segmento")


if __name__ == '__main__':
    run_weekly()


