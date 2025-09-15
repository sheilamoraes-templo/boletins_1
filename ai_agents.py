"""
Agentes modulares de IA:
- ArticleSummarizerAgent: resume artigos individuais
- BulletinSynthesisAgent: sintetiza boletim a partir de resumos
- BulletinReviewAgent: revisa e lapida o texto final do boletim

Todos os agentes usam OpenRouterGuard internamente para garantir rate limiting,
backoff e controle de tokens por chamada, conforme as regras do projeto.
"""

from typing import Dict, List, Optional
from datetime import datetime

from monitoring_openrouter import OpenRouterGuard


class ArticleSummarizerAgent:
    """Agente responsável por resumir artigos individuais."""

    def __init__(self):
        self.guard = OpenRouterGuard()

    def generate_summary(self, article: Dict) -> Optional[str]:
        content = article.get('content') or ''
        if not content or len(content) < 200:
            return None
        prompt = (
            "Resuma de forma detalhada, em português (Brasil), o artigo abaixo, mantendo fatos e contexto, sem opinião.\n"
            "Use 5-8 frases, tom jornalístico, conciso e claro.\n\n"
            f"TÍTULO: {article.get('title','N/A')}\nFONTE: {article.get('source','N/A')}\nDATA: {article.get('published','N/A')}\nURL: {article.get('url','N/A')}\n\n"
            f"CONTEÚDO:\n{content}\n\nRESUMO:"
        )
        resp = self.guard.generate_text(prompt)
        if resp.get('status') == 'success':
            return (resp.get('content') or '').strip()
        return None


class BulletinSynthesisAgent:
    """Agente responsável por sintetizar boletins a partir de resumos de artigos."""

    def __init__(self):
        self.guard = OpenRouterGuard()

    def generate_bulletin(self, segment_display_name: str, date_range: str, summaries: List[str], articles: List[Dict]) -> Dict[str, str]:
        ctx_items: List[str] = []
        for i, (s, a) in enumerate(zip(summaries, articles), 1):
            ctx_items.append(f"{i}. {a.get('title','N/A')} — {a.get('source','N/A')} — {a.get('published','N/A')}\n{s}")
        ctx = "\n\n".join(ctx_items)

        prompt = (
            f"## PERSONA ##\n"
            f"Você é um repórter-editor de Inteligência de Mercado especializado em {segment_display_name}.\n"
            f"Escreve em português do Brasil, em tom jornalístico analítico, claro e envolvente.\n"
            f"Seu papel é costurar as principais notícias da semana em um texto coeso, informativo e fluido.\n\n"
            f"## OBJETIVO ##\n"
            f"Produzir um boletim semanal estruturado e narrativo com base apenas nos resumos fornecidos ({date_range}).\n"
            f"O texto deve ser único, com início, meio e fim, costurando os fatos como uma narrativa jornalística.\n\n"
            f"## INSTRUÇÕES ##\n"
            f"1. Estrutura:\n- Título; Subtítulo; Lide; Corpo com 3–5 blocos (###); Fecho; Referências.\n"
            f"2. Conteúdo:\n- Baseie-se apenas nos resumos (abaixo). Não invente fatos.\n- Atribua corretamente: 'segundo {{veículo}} ({{ano}})'.\n- Inclua link limpo no fim da frase: (Fonte: {{veículo}}, {{link}}).\n"
            f"3. Estilo: jornalístico, analítico, profissional; frases curtas; sem hype; sem extrapolar.\n"
            f"4. Tamanho: 600–900 palavras (ou adequado à força das fontes).\n\n"
            f"## RESUMOS ##\n{ctx}\n\nGere o boletim agora:"
        )
        resp = self.guard.generate_text(prompt)
        if resp.get('status') != 'success':
            return {'status': 'error', 'error': resp.get('error', 'erro na síntese')}
        return {'status': 'success', 'content': (resp.get('content') or '').strip()}


class BulletinReviewAgent:
    """Agente responsável por revisar e lapidar o texto final do boletim."""

    def __init__(self):
        self.guard = OpenRouterGuard()

    def review(self, raw_bulletin_text: str, segment_display_name: str) -> Dict[str, str]:
        prompt = (
            f"Revise o texto abaixo em português (Brasil), mantendo o conteúdo factual, sem adicionar informações.\n"
            f"Ajuste para estilo jornalístico: frases claras, coesão, transições suaves, sem jargões e sem hype.\n"
            f"Faça correções de gramática, pontuação e fluidez. Preserve a estrutura (Título, Subtítulo, Lide, ### seções, Fecho).\n"
            f"Categoria: {segment_display_name}.\n\n"
            f"TEXTO:\n{raw_bulletin_text}\n\nTEXTO REVISTO:"
        )
        resp = self.guard.generate_text(prompt)
        if resp.get('status') != 'success':
            return {'status': 'error', 'error': resp.get('error', 'erro na revisão')}
        return {'status': 'success', 'content': (resp.get('content') or '').strip()}


