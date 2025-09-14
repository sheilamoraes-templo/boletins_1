# Boletins IA

Sistema automatizado de coleta, segmentação e geração de boletins sobre Inteligência Artificial de fontes brasileiras confiáveis.

## 🎯 Objetivo

Coletar notícias sobre IA, AI, inteligência artificial e LLMs de fontes brasileiras de qualidade, processar e segmentar o conteúdo para gerar boletins organizados por segmento (Tecnologia, Marketing e Direito Corporativo).

## ✅ Funcionalidades

- **Coleta RSS**: Coleta automática de notícias de 5 fontes prioritárias brasileiras
- **Segmentação Heurística**: Categorização automática em 3 segmentos principais
- **Geração com IA**: Criação de boletins usando OpenRouter/Gemini
- **Visualizador Web**: Interface moderna para visualizar resultados
- **Pipeline Integrado**: Execução completa automatizada

## 🏗️ Arquitetura

```
boletins_1/
├── config.py              # Configurações centralizadas
├── collector.py            # Coletor RSS simplificado
├── segmenter.py            # Segmentador heurístico
├── generator.py            # Gerador de boletins com IA
├── pipeline.py             # Pipeline principal integrado
├── visualizer.py           # Visualizador web
├── requirements.txt        # Dependências
├── outputs/                # Resultados da execução
├── logs/                   # Logs do sistema
└── templates/              # Templates HTML
```

## 📡 Fontes de Notícias

### Fontes Prioritárias (RSS)
- **G1** - Tecnologia, Economia, Ciência e Saúde
- **UOL** - Tecnologia e Economia
- **TI Inside** - Tecnologia e Inovação
- **Gizmodo Brasil** - Tecnologia e Gadgets
- **CNN Brasil** - Notícias gerais

## 🚀 Como Usar

### 1. Instalação

```bash
# Clone o repositório
git clone <repository-url>
cd boletins_1

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configuração

Configure as variáveis de ambiente:

```bash
# Chave da API OpenRouter (obrigatória)
export OPENROUTER_API_KEY="sua-chave-aqui"

# Configurações de email (opcional)
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export EMAIL_USER="seu-email@gmail.com"
export EMAIL_PASSWORD="sua-senha"
export EMAIL_RECIPIENTS="destinatario1@email.com,destinatario2@email.com"
```

### 3. Execução

#### Pipeline Completo
```bash
python pipeline.py
# Escolha opção 1 para execução completa
```

#### Execução Individual
```bash
# Apenas coleta
python collector.py

# Apenas segmentação
python segmenter.py

# Apenas geração de boletins
python generator.py
```

#### Visualizador Web
```bash
python visualizer.py
# Acesse: http://127.0.0.1:5000
```

## 📊 Segmentos

O sistema segmenta as notícias em 3 categorias principais:

### 1. Tecnologia
- Desenvolvimento de software
- Inteligência artificial
- Startups e inovação
- Cloud computing
- Data science

### 2. Marketing
- Marketing digital
- Branding e comunicação
- Vendas e comercial
- Redes sociais
- E-commerce

### 3. Direito Corporativo
- Direito empresarial
- Compliance e governança
- Direito tributário
- Direito trabalhista
- Legislação

## 🔧 Configurações

### Configurações de Coleta
- **DAYS_BACK**: Período de coleta (padrão: 7 dias)
- **MAX_ARTICLES_PER_SOURCE**: Máximo por fonte (padrão: 50)
- **MAX_ARTICLES_PER_SEGMENT**: Máximo por segmento (padrão: 15)

### Configurações de IA
- **GEMINI_MODEL**: Modelo Gemini (padrão: google/gemini-2.0-flash-exp)
- **MAX_TOKENS**: Máximo de tokens (padrão: 4000)
- **TEMPERATURE**: Temperatura de geração (padrão: 0.7)

## 📈 Resultados

O sistema gera:
- **Arquivos JSON** com resultados detalhados
- **Boletins em texto** formatados e prontos para uso
- **Estatísticas** de coleta, segmentação e geração
- **Logs** detalhados de execução

## 🛠️ Tecnologias

- **Python 3.11+**
- **feedparser** - Parsing de feeds RSS
- **BeautifulSoup** - Limpeza de HTML
- **Flask** - Interface web
- **OpenRouter API** - Geração de conteúdo com IA
- **Requests** - Requisições HTTP

## 📝 Estrutura de Arquivos

### Arquivos Principais
- `config.py` - Configurações centralizadas
- `collector.py` - Coletor RSS
- `segmenter.py` - Segmentador heurístico
- `generator.py` - Gerador de boletins
- `pipeline.py` - Pipeline principal
- `visualizer.py` - Visualizador web

### Diretórios
- `outputs/` - Resultados da execução
- `logs/` - Logs do sistema
- `templates/` - Templates HTML

## 🔍 Palavras-chave IA

O sistema busca por:
- inteligência artificial, IA, AI
- machine learning, aprendizado de máquina
- LLM, LLMs, ChatGPT, GPT
- OpenAI, Anthropic, Claude, Gemini
- neural network, rede neural
- algoritmo, automação, robô, chatbot
- E mais 20+ termos relacionados

## 📋 Próximos Passos

1. **GitHub Actions** - Configurar execução diária às 13:00
2. **Email** - Implementar envio automático de boletins
3. **Monitoramento** - Adicionar alertas e notificações
4. **Expansão** - Adicionar mais fontes e segmentos

## 🤝 Contribuição

Este é um projeto em desenvolvimento ativo. Contribuições são bem-vindas!

## 📄 Licença

Este projeto é baseado no projeto "coleta_noticias_online" e adaptado para geração de boletins organizados.

---

**Última atualização:** 10/01/2025  
**Status:** Versão 1.0 - Funcional ✅
