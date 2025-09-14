"""
Script de teste para verificar se o sistema está funcionando
"""

import os
import sys
import logging
from datetime import datetime

# Adiciona o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Testa se todos os módulos podem ser importados"""
    print("Testando importações...")
    
    try:
        from config import Config
        print("✅ config.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar config.py: {e}")
        return False
    
    try:
        from collector import NewsCollector
        print("✅ collector.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar collector.py: {e}")
        return False
    
    try:
        from segmenter import NewsSegmenter
        print("✅ segmenter.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar segmenter.py: {e}")
        return False
    
    try:
        from generator import BulletinGenerator
        print("✅ generator.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar generator.py: {e}")
        return False
    
    try:
        from pipeline import BoletinsPipeline
        print("✅ pipeline.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar pipeline.py: {e}")
        return False
    
    try:
        from visualizer import BoletinsVisualizer
        print("✅ visualizer.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar visualizer.py: {e}")
        return False
    
    try:
        from email_sender import EmailSender
        print("✅ email_sender.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar email_sender.py: {e}")
        return False
    
    return True

def test_config():
    """Testa se a configuração está válida"""
    print("\nTestando configuração...")
    
    try:
        from config import Config
        
        # Testa criação de diretórios
        Config.create_directories()
        print("✅ Diretórios criados com sucesso")
        
        # Testa validação de configuração
        if Config.validate_config():
            print("✅ Configuração válida")
        else:
            print("⚠️ Configuração com problemas (verifique OPENROUTER_API_KEY)")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        return False

def test_instances():
    """Testa se as instâncias podem ser criadas"""
    print("\nTestando criação de instâncias...")
    
    try:
        from config import Config
        from collector import NewsCollector
        from segmenter import NewsSegmenter
        
        # Cria instâncias básicas
        collector = NewsCollector()
        print("✅ NewsCollector criado com sucesso")
        
        segmenter = NewsSegmenter()
        print("✅ NewsSegmenter criado com sucesso")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar instâncias: {e}")
        return False

def test_dependencies():
    """Testa se as dependências estão instaladas"""
    print("\nTestando dependências...")
    
    dependencies = [
        'feedparser',
        'requests',
        'beautifulsoup4',
        'flask',
        'flask_cors'
    ]
    
    missing_deps = []
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} instalado")
        except ImportError:
            print(f"❌ {dep} não instalado")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n⚠️ Dependências faltando: {', '.join(missing_deps)}")
        print("Execute: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Função principal de teste"""
    print("TESTE DO SISTEMA BOLETINS IA")
    print("="*50)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
    print("="*50)
    
    # Configura logging básico
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    tests = [
        ("Dependências", test_dependencies),
        ("Importações", test_imports),
        ("Configuração", test_config),
        ("Instâncias", test_instances)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name.upper()} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Relatório final
    print(f"\n{'='*50}")
    print("RELATÓRIO FINAL")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 SISTEMA PRONTO PARA USO!")
        print("\nPróximos passos:")
        print("1. Configure OPENROUTER_API_KEY no arquivo .env")
        print("2. Execute: python pipeline.py")
        print("3. Acesse o visualizador: python visualizer.py")
    else:
        print("\n⚠️ SISTEMA COM PROBLEMAS")
        print("Corrija os erros antes de continuar.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
