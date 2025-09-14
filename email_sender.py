"""
Módulo de envio de boletins por email
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

from config import Config

logger = logging.getLogger(__name__)

class EmailSender:
    """Enviador de boletins por email"""
    
    def __init__(self):
        self.smtp_server = Config.EMAIL_CONFIG['smtp_server']
        self.smtp_port = Config.EMAIL_CONFIG['smtp_port']
        self.email_user = Config.EMAIL_CONFIG['email_user']
        self.email_password = Config.EMAIL_CONFIG['email_password']
        self.recipients = Config.EMAIL_CONFIG['recipients']
        
        # Valida configuração
        if not self._validate_config():
            raise ValueError("Configuração de email inválida")
    
    def _validate_config(self) -> bool:
        """Valida se a configuração de email está correta"""
        required_fields = ['smtp_server', 'smtp_port', 'email_user', 'email_password']
        
        for field in required_fields:
            if not Config.EMAIL_CONFIG.get(field):
                logger.error(f"Campo obrigatório de email não configurado: {field}")
                return False
        
        if not self.recipients:
            logger.error("Nenhum destinatário configurado")
            return False
        
        return True
    
    def send_bulletins(self, bulletins_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia boletins por email"""
        try:
            logger.info("INICIANDO ENVIO DE BOLETINS POR EMAIL")
            logger.info("="*50)
            
            bulletins = bulletins_data.get('bulletins', {})
            if not bulletins:
                return {
                    'status': 'error',
                    'error': 'Nenhum boletim encontrado para envio'
                }
            
            # Prepara email principal
            email_content = self._prepare_email_content(bulletins)
            
            # Envia email principal
            result = self._send_email(
                subject="Boletins IA - Resumo Diário",
                content=email_content,
                recipients=self.recipients
            )
            
            if result['status'] == 'success':
                logger.info(f"✅ Email principal enviado com sucesso para {len(self.recipients)} destinatários")
                
                # Opcionalmente, envia boletins individuais
                individual_results = self._send_individual_bulletins(bulletins)
                
                return {
                    'status': 'success',
                    'main_email_sent': True,
                    'individual_emails_sent': individual_results,
                    'total_recipients': len(self.recipients),
                    'sent_date': datetime.now().isoformat()
                }
            else:
                logger.error(f"❌ Erro ao enviar email principal: {result.get('error')}")
                return result
                
        except Exception as e:
            logger.error(f"Erro no envio de boletins: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _prepare_email_content(self, bulletins: Dict[str, Any]) -> str:
        """Prepara conteúdo do email principal"""
        try:
            # Cabeçalho do email
            content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boletins IA</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .bulletin {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        .bulletin-title {{
            font-size: 1.3em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .bulletin-meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
        }}
        .bulletin-content {{
            white-space: pre-line;
            line-height: 1.5;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Boletins IA</h1>
        <p>Sistema de Coleta e Análise de Notícias sobre Inteligência Artificial</p>
        <p>Data: {datetime.now().strftime('%d/%m/%Y')}</p>
    </div>
"""
            
            # Adiciona cada boletim
            successful_bulletins = 0
            for segment, bulletin_info in bulletins.items():
                if bulletin_info.get('status') == 'success':
                    successful_bulletins += 1
                    
                    content += f"""
    <div class="bulletin">
        <div class="bulletin-title">{bulletin_info.get('title', f'Boletim de {segment.title()}')}</div>
        <div class="bulletin-meta">
            Segmento: {segment.title()} | 
            Artigos analisados: {bulletin_info.get('articles_count', 0)} | 
            Gerado em: {bulletin_info.get('generated_date', 'N/A')}
        </div>
        <div class="bulletin-content">{bulletin_info.get('ai_generated_text', 'Conteúdo não disponível')}</div>
    </div>
"""
            
            # Rodapé
            content += f"""
    <div class="footer">
        <p>Boletins gerados automaticamente pelo Sistema Boletins IA</p>
        <p>Total de boletins: {successful_bulletins}</p>
        <p>Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
    </div>
</body>
</html>
"""
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao preparar conteúdo do email: {e}")
            return "Erro ao preparar conteúdo do email"
    
    def _send_individual_bulletins(self, bulletins: Dict[str, Any]) -> Dict[str, Any]:
        """Envia boletins individuais por segmento"""
        try:
            results = {}
            
            for segment, bulletin_info in bulletins.items():
                if bulletin_info.get('status') == 'success':
                    try:
                        subject = f"Boletim IA - {bulletin_info.get('title', segment.title())}"
                        content = self._prepare_individual_bulletin_content(bulletin_info)
                        
                        result = self._send_email(
                            subject=subject,
                            content=content,
                            recipients=self.recipients
                        )
                        
                        results[segment] = result
                        
                        if result['status'] == 'success':
                            logger.info(f"✅ Boletim individual '{segment}' enviado com sucesso")
                        else:
                            logger.error(f"❌ Erro ao enviar boletim individual '{segment}': {result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"Erro ao enviar boletim individual '{segment}': {e}")
                        results[segment] = {'status': 'error', 'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Erro no envio de boletins individuais: {e}")
            return {}
    
    def _prepare_individual_bulletin_content(self, bulletin_info: Dict[str, Any]) -> str:
        """Prepara conteúdo de boletim individual"""
        try:
            content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{bulletin_info.get('title', 'Boletim IA')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .bulletin-content {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            white-space: pre-line;
            line-height: 1.5;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{bulletin_info.get('title', 'Boletim IA')}</h1>
        <p>Segmento: {bulletin_info.get('segment', 'N/A').title()}</p>
        <p>Artigos analisados: {bulletin_info.get('articles_count', 0)}</p>
        <p>Data: {datetime.now().strftime('%d/%m/%Y')}</p>
    </div>
    
    <div class="bulletin-content">
{bulletin_info.get('ai_generated_text', 'Conteúdo não disponível')}
    </div>
    
    <div class="footer">
        <p>Boletim gerado automaticamente pelo Sistema Boletins IA</p>
        <p>Enviado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
    </div>
</body>
</html>
"""
            
            return content
            
        except Exception as e:
            logger.error(f"Erro ao preparar conteúdo individual: {e}")
            return "Erro ao preparar conteúdo do boletim"
    
    def _send_email(self, subject: str, content: str, recipients: List[str]) -> Dict[str, Any]:
        """Envia email para lista de destinatários"""
        try:
            # Cria mensagem
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_user
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Adiciona conteúdo HTML
            html_part = MIMEText(content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Conecta ao servidor SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            
            # Envia email
            text = msg.as_string()
            server.sendmail(self.email_user, recipients, text)
            server.quit()
            
            logger.info(f"Email enviado com sucesso para {len(recipients)} destinatários")
            
            return {
                'status': 'success',
                'recipients_count': len(recipients),
                'sent_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def send_test_email(self) -> Dict[str, Any]:
        """Envia email de teste"""
        try:
            logger.info("Enviando email de teste...")
            
            test_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teste de Email</title>
</head>
<body>
    <h1>Teste de Configuração de Email</h1>
    <p>Este é um email de teste do Sistema Boletins IA.</p>
    <p>Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
    <p>Se você recebeu este email, a configuração está funcionando corretamente!</p>
</body>
</html>
"""
            
            result = self._send_email(
                subject="Teste de Email - Boletins IA",
                content=test_content,
                recipients=self.recipients
            )
            
            if result['status'] == 'success':
                logger.info("✅ Email de teste enviado com sucesso")
            else:
                logger.error(f"❌ Erro no email de teste: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no envio de email de teste: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

def main():
    """Função principal para testar o envio de email"""
    print("TESTE DE ENVIO DE EMAIL")
    print("="*40)
    
    # Configura logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(f'{Config.LOGS_DIR}/email_sender.log'),
            logging.StreamHandler()
        ]
    )
    
    # Cria diretórios necessários
    Config.create_directories()
    
    try:
        # Testa configuração
        if not Config.EMAIL_CONFIG['email_user']:
            print("❌ Configuração de email não encontrada.")
            print("Configure as variáveis de ambiente:")
            print("  EMAIL_USER, EMAIL_PASSWORD, EMAIL_RECIPIENTS")
            return
        
        # Envia email de teste
        sender = EmailSender()
        result = sender.send_test_email()
        
        if result['status'] == 'success':
            print(f"✅ Email de teste enviado com sucesso!")
            print(f"Destinatários: {result['recipients_count']}")
        else:
            print(f"❌ Erro no envio: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")

if __name__ == "__main__":
    main()
