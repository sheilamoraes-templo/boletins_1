"""
Agentes modulares de IA (com proteção OpenRouterGuard):
- ArticleSummarizerAgent: resume artigos individuais
- BulletinSynthesisAgent: sintetiza boletim a partir de resumos
- BulletinReviewAgent: revisa e lapida o texto final do boletim

Todos os agentes usam OpenRouterGuard internamente para garantir rate limiting,
backoff e controle de tokens por chamada, conforme as regras do projeto.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from monitoring_openrouter import OpenRouterGuard
from config import Config

logger = logging.getLogger(__name__)


class ArticleSummarizerAgent:
    """Agente responsável por resumir artigos individuais."""

    def __init__(self):
        self.guard = OpenRouterGuard()
        self.max_tokens = 900
        self.temperature = 0.3

    def generate_summary(self, article: Dict) -> Optional[str]:
        content = article.get('content') or ''
        if not content or len(content) < 200:
            return None
        prompt = (
            "Você é um analista de notícias especializado em transformar artigos em resumos claros e informativos.\n\n"
            "## OBJETIVO ##\n"
            "Ler o artigo fornecido e produzir um resumo detalhado, em português do Brasil, que capture o essencial do texto.\n\n"
            "## INSTRUÇÕES ##\n"
            "1. Leia o artigo inteiro com atenção.\n"
            "2. Identifique os elementos principais: o que aconteceu, quem está envolvido, quando, onde e por que importa.\n"
            "3. Estruture o resumo em 5 a 8 frases, em tom jornalístico (informativo, neutro e claro).\n"
            "4. Inclua sempre:\n"
            "   - Contexto (de onde vem a notícia ou qual o pano de fundo).\n"
            "   - Fatos principais (o que aconteceu de fato).\n"
            "   - Atores (empresas, pessoas, instituições).\n"
            "   - Impacto ou consequência (por que essa notícia é relevante).\n"
            "5. Não adicione opiniões, julgamentos ou informações que não estão no texto original.\n"
            "6. Evite frases vagas como ‘isso é importante’. Sempre explique o motivo concreto.\n\n"
            "## FORMATO DE SAÍDA ##\n"
            "- Escreva um único parágrafo coeso, entre 5 e 8 frases, em estilo jornalístico conciso.\n\n"
            f"TÍTULO: {article.get('title','N/A')}\nFONTE: {article.get('source','N/A')}\nDATA: {article.get('published','N/A')}\nURL: {article.get('url','N/A')}\n\n"
            f"CONTEÚDO:\n{content}\n\nRESUMO:"
        )
        resp = self.guard.generate_text(prompt, max_tokens=self.max_tokens, temperature=self.temperature)
        if resp.get('status') == 'success':
            return (resp.get('content') or '').strip()
        logger.error(f"Falha no resumo: {resp.get('error')}")
        return None


class BulletinSynthesisAgent:
    """Agente responsável por sintetizar boletins a partir de resumos de artigos."""

    def __init__(self):
        self.guard = OpenRouterGuard()
        self.max_tokens = 1200
        self.temperature = 0.5

    def generate_bulletin(self, segment_display_name: str, date_range: str, summaries: List[str], articles: List[Dict]) -> Dict[str, str]:
        ctx_items: List[str] = []
        for i, (s, a) in enumerate(zip(summaries, articles), 1):
            ctx_items.append(f"{i}. {a.get('title','N/A')} — {a.get('source','N/A')} — {a.get('published','N/A')}\n{s}")
        ctx = "\n\n".join(ctx_items)

        prompt = (
            f"Você é um editor-chefe de jornal especializado em transformar resumos de notícias em um boletim jornalístico bem escrito e coeso.\n\n"
            f"## OBJETIVO ##\n"
            f"Produzir um boletim informativo narrativo e analítico, em português do Brasil, com base apenas nos resumos fornecidos.\n\n"
            f"## INSTRUÇÕES DE REDAÇÃO ##\n\n"
            f"### 1. Estrutura obrigatória\n"
            f"- **Título principal**: direto e informativo.\n"
            f"- **Subtítulo**: completa o título e aponta o fio condutor.\n"
            f"- **Lide (primeiro parágrafo)**: apresenta de forma clara o que marcou a semana e por que importa.\n"
            f"- **Corpo**: dividido em 3 a 5 blocos (use “###” como subtítulos).\n"
            f"   - Cada bloco deve reunir notícias de um mesmo tema ou que se conectem logicamente.\n"
            f"   - Apresente as notícias em ordem lógica: do mais geral para o mais específico, ou do mais relevante para o complementar.\n"
            f"- **Fecho**: um parágrafo final que amarra as ideias e mostra o panorama geral.\n"
            f"- **Referências**: lista das fontes originais, citando veículo e link.\n\n"
            f"### 2. Estilo e tom\n"
            f"- Jornalístico, claro, objetivo e didático.\n"
            f"- Frases curtas e bem pontuadas.\n"
            f"- Varie verbos de atribuição (“afirmou”, “ressaltou”, “divulgou”).\n"
            f"- Use conectores para ligar ideias: “Enquanto isso…”, “Já no setor…”, “Por outro lado…”.\n\n"
            f"### 3. Técnicas jornalísticas\n"
            f"- **Costura narrativa**: conecte notícias, não as apresente isoladas.\n"
            f"   - Exemplo ruim: “A empresa X lançou produto. A empresa Y fez fusão.”\n"
            f"   - Exemplo bom: “Enquanto a empresa X aposta em novos produtos, a Y investe em fusões para fortalecer sua posição.”\n"
            f"- **Contextualização**: explique em uma frase por que cada fato importa.\n"
            f"- **Atribuição correta**: cite sempre a fonte (“Segundo o jornal Valor (2025)…” ) e adicione o link no fim.\n"
            f"- **Variedade**: evite começar todos os parágrafos da mesma forma.\n\n"
            f"### 4. Extensão\n"
            f"- Produza entre 600 e 900 palavras (ou menos, se o material for limitado).\n"
            f"- Evite listas secas; escreva sempre em formato narrativo.\n\n"
            f"## RESUMOS ##\n{ctx}\n\nAgora escreva o boletim seguindo todas as instruções acima."
        )
        resp = self.guard.generate_text(prompt, max_tokens=self.max_tokens, temperature=self.temperature)
        if resp.get('status') != 'success':
            return {'status': 'error', 'error': resp.get('error', 'erro na síntese')}
        return {'status': 'success', 'content': (resp.get('content') or '').strip()}


class BulletinReviewAgent:
    """Agente responsável por revisar e lapidar o texto final do boletim."""

    def __init__(self):
        self.guard = OpenRouterGuard()
        self.max_tokens = 2000
        self.temperature = 0.2

    def review(self, raw_bulletin_text: str, segment_display_name: str) -> Dict[str, str]:
        prompt = (
            "Você é um revisor editorial responsável por lapidar textos jornalísticos.\n\n"
            "## OBJETIVO ##\n"
            "Revisar o boletim de notícias fornecido, mantendo conteúdo factual, mas melhorando clareza, fluidez e estilo jornalístico.\n\n"
            "## INSTRUÇÕES ##\n"
            "1. Corrija gramática, pontuação e ortografia.\n"
            "2. Garanta que os parágrafos tenham transições suaves, sem parecer blocos soltos.\n"
            "3. Uniformize o estilo para que soe como uma reportagem coesa:\n"
            "   - Varie as palavras e verbos de atribuição.\n"
            "   - Tire repetições desnecessárias.\n"
            "   - Simplifique frases muito longas.\n"
            "4. Preserve a estrutura: Título, Subtítulo, Lide, Blocos (###), Fecho e Referências.\n"
            "5. Não adicione novas informações nem opiniões.\n"
            "6. Ajuste o ritmo para que a leitura seja envolvente, como em uma newsletter profissional.\n\n"
            f"## CONTEXTO ##\nCategoria: {segment_display_name}.\n\n"
            f"## TEXTO ORIGINAL ##\n{raw_bulletin_text}\n\n"
            "## SAÍDA ##\nTexto revisado, em português do Brasil, pronto para publicação."
        )
        resp = self.guard.generate_text(prompt, max_tokens=self.max_tokens, temperature=self.temperature)
        if resp.get('status') != 'success':
            return {'status': 'error', 'error': resp.get('error', 'erro na revisão')}
        return {'status': 'success', 'content': (resp.get('content') or '').strip()}
