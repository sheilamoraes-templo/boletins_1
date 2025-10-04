"""
Configurações centralizadas do projeto Boletins IA
"""

import os
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Carrega .env automaticamente (não versionado)
load_dotenv()

class Config:
    """Classe de configurações centralizadas"""
    
    # Configurações de API
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'google/gemini-2.5-flash-lite')
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Configurações de coleta
    DAYS_BACK = 5  # Últimos 5 dias (conforme solicitado)
    MAX_ARTICLES_PER_SOURCE = 100
    MAX_ARTICLES_PER_SEGMENT = 15  # 15 artigos por segmento para boletim
    COLLECT_IA_ONLY = True  # Coletar somente se mencionar IA (título/preview/conteúdo)

    # Selenium (fallback opcional)
    USE_SELENIUM = False  # desabilitado temporariamente
    SELENIUM_TIMEOUT = 12  # segundos para aguardar renderização
    SELENIUM_MAX_PAGES = 10  # máximo de páginas renderizadas por execução
    SELENIUM_DOMAINS = [
        'www1.folha.uol.com.br',
        'www.estadao.com.br',
        'www.cnnbrasil.com.br',
        'exame.com',
    ]
    
    # Configurações de cache
    CACHE_ENABLED = True
    CACHE_EXPIRY_HOURS = 24  # Cache expira em 24 horas
    
    # Configurações de timeout
    REQUEST_TIMEOUT = 30  # Timeout para requisições HTTP
    PROCESSING_TIMEOUT = 300  # Timeout para processamento (5 min)
    EMAIL_FETCH_TIMEOUT = 60  # Timeout para busca de emails
    
    # Configurações de geração
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    
    # Fontes de notícias prioritárias (RSS)
    NEWS_SOURCES = {
        'G1': {
            'rss_feeds': [
                'https://g1.globo.com/rss/g1/tecnologia/'
            ],
            'base_url': 'https://g1.globo.com'
        },
        'UOL': {
            'rss_feeds': [
                'https://rss.uol.com.br/feed/tecnologia.xml'
            ],
            'base_url': 'https://www.uol.com.br'
        },
        'TI Inside': {
            'rss_feeds': [
                'https://tiinside.com.br/feed/',
            ],
            'base_url': 'https://tiinside.com.br'
        },
        'Gizmodo Brasil': {
            'rss_feeds': [
                'https://gizmodo.uol.com.br/feed/',
            ],
            'base_url': 'https://gizmodo.uol.com.br'
        }
    }
    
    # Fontes para scraping leve (sem Selenium)
    SCRAPING_SOURCES = {
        'G1': {
            'base_url': 'https://g1.globo.com',
            'sections': ['/tecnologia/']
        },
        'UOL': {
            'base_url': 'https://www.uol.com.br',
            'sections': ['/tilt/']
        },
        'Exame': {
            'base_url': 'https://exame.com',
            'sections': ['/tecnologia/', '/negocios/']
        },
        'Canaltech': {
            'base_url': 'https://canaltech.com.br',
            'sections': ['/inteligencia-artificial/', '/tecnologia/']
        },
        'AINEWS': {
            'base_url': 'https://ainews.net.br',
            'sections': ['/', '/inteligencia-artificial/']
        },
        'TI Inside (Top News)': {
            'base_url': 'https://tiinside.com.br',
            'sections': ['/top-news/', '/tag/inteligencia-artificial/']
        },
        'BBC Brasil': {
            'base_url': 'https://www.bbc.com',
            'sections': ['/portuguese/topics/c340q0gy0n5t']  # Tecnologia (Português)
        },
        'InfoMoney IA': {
            'base_url': 'https://www.infomoney.com.br',
            'sections': ['/tudo-sobre/inteligencia-artificial/']
        },
        'IA Expert Blog': {
            'base_url': 'https://iaexpert.academy',
            'sections': ['/blog/']
        },
        'GauchaZH IA': {
            'base_url': 'https://gauchazh.clicrbs.com.br',
            'sections': ['/ultimas-noticias/tag/inteligencia-artificial/']
        },
        'NeoFeed IA': {
            'base_url': 'https://neofeed.com.br',
            'sections': ['/noticias-sobre/inteligencia-artificial/']
        },
        'CNN Brasil Tecnologia': {
            'base_url': 'https://www.cnnbrasil.com.br',
            'sections': ['/tecnologia/']
        },
        'IT Forum': {
            'base_url': 'https://itforum.com.br',
            'sections': ['/noticias/']
        },
        'Forbes Brasil (IA)': {
            'base_url': 'https://forbes.com.br',
            'sections': ['/noticias-sobre/ia/']
        }
    }
    
    # Palavras-chave para IA
    AI_KEYWORDS = [
        'inteligência artificial', 'inteligencia artificial', 'IA', 'AI',
        'machine learning', 'aprendizado de máquina', 'deep learning',
        'LLM', 'LLMs', 'ChatGPT', 'GPT', 'OpenAI', 'Anthropic',
        'Claude', 'Gemini', 'Bard', 'neural network', 'rede neural',
        'algoritmo', 'automação', 'robô', 'robôs', 'chatbot',
        'processamento de linguagem natural', 'NLP', 'artificial intelligence',
        'neural networks', 'algorithms', 'automation', 'robots',
        'chatbots', 'natural language processing', 'computer vision',
        'visão computacional', 'aprendizado profundo', 'aprendizado automático'
    ]
    
    # Palavras bloqueadas
    BLOCKED_KEYWORDS = [
        'polêmica', 'fofoca', 'bolsonaro', 'influencer',
        'iphone', 'morte'
    ]
    
    # Segmentos de interesse (conforme especificado)
    SEGMENTS = {
        'marketing_comunicacao_jornalismo': {
            'name': 'Marketing, Comunicação e Jornalismo',
            'keywords': [
                # Marketing e Comunicação
                'marketing', 'publicidade', 'propaganda', 'anúncio', 'campanha',
                'branding', 'marca', 'identidade visual', 'posicionamento',
                'público-alvo', 'audiência', 'consumidor', 'cliente', 'mercado',
                'vendas', 'vendedor', 'comercial', 'negociação', 'fechamento',
                'lead', 'prospecção', 'funil de vendas', 'conversão', 'retorno',
                'roi', 'investimento', 'orçamento', 'custo-benefício',
                
                # Comunicação e Jornalismo
                'comunicação', 'jornalismo', 'jornalista', 'repórter', 'redator',
                'mídia', 'imprensa', 'notícia', 'reportagem', 'entrevista',
                'assessoria de imprensa', 'relações públicas', 'pr', 'rp',
                'comunicação corporativa', 'comunicação interna', 'comunicação externa',
                'crise de comunicação', 'gestão de crise', 'reputação',
                
                # Digital e Conteúdo
                'conteúdo', 'conteúdo digital', 'storytelling', 'narrativa',
                'redes sociais', 'social media', 'instagram', 'facebook', 'twitter',
                'linkedin', 'youtube', 'tiktok', 'influencer', 'influenciador',
                'marketing digital', 'e-commerce', 'loja virtual', 'vendas online',
                'seo', 'sem', 'google ads', 'facebook ads', 'anúncios pagos',
                'email marketing', 'newsletter', 'automação', 'crm',
                'analytics', 'métricas', 'kpi', 'dashboard', 'relatório'
            ],
            'weight': 1.0
        },
        'direito_corporativo_tributario_trabalhista': {
            'name': 'Direito Corporativo, Tributário, Trabalhista e Legislativo',
            'keywords': [
                # Direito Corporativo
                'direito corporativo', 'direito empresarial', 'sociedade', 'empresa',
                'contrato social', 'estatuto', 'assembleia', 'conselho', 'administração',
                'governança corporativa', 'compliance', 'conformidade', 'auditoria',
                'gestão de riscos', 'políticas internas', 'código de conduta',
                'fusão', 'aquisição', 'm&a', 'reestruturação', 'reorganização',
                'joint venture', 'parceria', 'consórcio', 'franquia',
                
                # Direito Tributário
                'direito tributário', 'tributário', 'fiscal', 'imposto', 'taxa',
                'receita federal', 'fazenda', 'icms', 'ipi', 'iss', 'irpj', 'csll',
                'pis', 'cofins', 'inss', 'fgts', 'simples nacional', 'mei',
                'planejamento tributário', 'elisão fiscal', 'evasão fiscal',
                'multa', 'autuação', 'infração', 'penalidade', 'juros',
                'parcelamento', 'refis', 'pgt', 'dívida ativa',
                
                # Direito Trabalhista
                'direito trabalhista', 'trabalhista', 'trabalho', 'emprego',
                'clt', 'consolidação das leis do trabalho', 'carteira de trabalho',
                'salário', 'remuneração', 'benefícios', 'vale-transporte', 'vale-refeição',
                'fgts', 'inss', '13º salário', 'férias', 'licença', 'afastamento',
                'demissão', 'rescisão', 'aviso prévio', 'multa do artigo 477',
                'justa causa', 'sem justa causa', 'indenização', 'verbas rescisórias',
                'sindicato', 'convenção coletiva', 'acordo coletivo', 'greve',
                'assédio', 'discriminação', 'acidente de trabalho', 'cat',
                
                # Direito Legislativo e Judicial
                'direito legislativo', 'legislativo', 'lei', 'legislação', 'norma',
                'decreto', 'portaria', 'instrução normativa', 'resolução',
                'projeto de lei', 'lei ordinária', 'lei complementar', 'medida provisória',
                'congresso', 'senado', 'câmara', 'deputado', 'senador',
                'comissão', 'audiência pública', 'consultoria legislativa',
                'regulamentação', 'regulamento', 'regulamentar',
                'judicial', 'tribunal', 'juiz', 'processo', 'sentença', 'recurso'
            ],
            'weight': 1.0
        },
        'recursos_humanos_gestao_pessoas': {
            'name': 'Recursos Humanos e Gestão de Pessoas',
            'keywords': [
                # Recursos Humanos
                'recursos humanos', 'rh', 'gestão de pessoas', 'gestão humana',
                'departamento pessoal', 'dp', 'pessoal', 'colaborador', 'funcionário',
                'empregado', 'trabalhador', 'equipe', 'time', 'staff',
                
                # Recrutamento e Seleção
                'recrutamento', 'seleção', 'contratação', 'admissão', 'onboarding',
                'processo seletivo', 'entrevista', 'currículo', 'cv', 'candidato',
                'talent acquisition', 'aquisição de talentos', 'headhunting',
                'recrutador', 'seletor', 'analista de rh', 'coordenador de rh',
                'gerente de rh', 'diretor de rh', 'vp de pessoas',
                
                # Desenvolvimento e Treinamento
                'desenvolvimento', 'treinamento', 'capacitação', 'aprendizado',
                'curso', 'workshop', 'seminário', 'palestra', 'mentoring', 'coaching',
                'plano de carreira', 'sucessão', 'liderança', 'gestão',
                'soft skills', 'hard skills', 'competências', 'habilidades',
                'avaliação de desempenho', 'feedback', '1:1', 'pdi',
                
                # Cultura e Engajamento
                'cultura organizacional', 'cultura', 'clima organizacional', 'clima',
                'engajamento', 'satisfação', 'motivação', 'bem-estar',
                'ambiente de trabalho', 'qualidade de vida', 'work-life balance',
                'diversidade', 'inclusão', 'equidade', 'igualdade',
                'valores', 'missão', 'visão', 'propósito', 'identidade',
                
                # Remuneração e Benefícios
                'remuneração', 'salário', 'benefícios', 'compensação', 'pacote',
                'vale-transporte', 'vale-refeição', 'vale-alimentação', 'plano de saúde',
                'plano odontológico', 'seguro de vida', 'previdência privada',
                'participação nos lucros', 'plr', 'bônus', 'comissão',
                'holerite', 'contracheque', 'folha de pagamento',
                
                # Relações Trabalhistas
                'relações trabalhistas', 'sindicato', 'convenção coletiva',
                'acordo coletivo', 'negociação', 'bargaining', 'greve',
                'representação', 'delegado sindical', 'comissão de fábrica',
                'cipa', 'comissão interna', 'segurança do trabalho',
                'demissao', 'demissões',
                
                # Tecnologia e Inovação em RH
                'rh digital', 'people analytics', 'people data', 'dados de rh',
                'sistema de rh', 'software de rh', 'ferramenta de rh',
                'automação', 'inteligência artificial', 'ia', 'machine learning',
                'chatbot', 'assistente virtual', 'plataforma de rh',
                'gestão de talentos', 'talent management', 'succession planning'
            ],
            'weight': 1.0
        }
    }
    
    # Configurações de email
    EMAIL_CONFIG = {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT') or '587'),
        'email_user': os.getenv('EMAIL_USER', ''),
        'email_password': os.getenv('EMAIL_PASSWORD', ''),
        'recipients': os.getenv('EMAIL_RECIPIENTS', '').split(',') if os.getenv('EMAIL_RECIPIENTS') else []
    }
    
    # Configurações de coleta de email
    EMAIL_COLLECTION_CONFIG = {
        'imap_server': os.getenv('IMAP_SERVER', 'imap.gmail.com'),
        'imap_port': int(os.getenv('IMAP_PORT') or '993'),
        'email_user': os.getenv('EMAIL_USER', ''),
        'email_password': os.getenv('EMAIL_PASSWORD', ''),
        'folder': 'INBOX',  # Caixa de entrada
        'days_back': DAYS_BACK
    }
    
    # Configurações de cache
    CACHE_CONFIG = {
        'enabled': CACHE_ENABLED,
        'expiry_hours': CACHE_EXPIRY_HOURS,
        'cache_dir': 'cache',
        'email_cache_file': 'email_links_cache.json',
        'segmentation_cache_file': 'segmentation_cache.json',
        'analysis_cache_file': 'analysis_cache.json'
    }
    
    # Configurações de logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Diretórios
    OUTPUT_DIR = 'outputs'
    LOGS_DIR = 'logs'
    TEMPLATES_DIR = 'templates'
    
    @classmethod
    def get_openrouter_api_key(cls) -> str:
        """Retorna a chave da API do OpenRouter"""
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY não configurada. Configure a variável de ambiente.")
        return cls.OPENROUTER_API_KEY
    
    @classmethod
    def validate_config(cls, require_api: bool = False) -> bool:
        """Valida se as configurações estão corretas
        - require_api=True: exige OPENROUTER_API_KEY (para geração de boletins)
        - require_api=False: não exige (para coleta/segmentação)
        """
        try:
            # Verifica chave da API somente se requerido
            if require_api:
                cls.get_openrouter_api_key()
            
            # Verifica fontes de notícias
            if not cls.NEWS_SOURCES:
                raise ValueError("Nenhuma fonte de notícias configurada")
            
            # Verifica segmentos
            if not cls.SEGMENTS:
                raise ValueError("Nenhum segmento configurado")
            
            return True
        except Exception as e:
            print(f"Erro na configuração: {e}")
            return False
    
    @classmethod
    def create_directories(cls):
        """Cria diretórios necessários"""
        import os
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.TEMPLATES_DIR, exist_ok=True)
