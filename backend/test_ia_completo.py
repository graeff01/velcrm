# -*- coding: utf-8 -*-
"""
🧪 TESTE COMPLETO DO SISTEMA DE QUALIFICAÇÃO DE IA
Simula um lead passando por todo o processo de qualificação
ATUALIZADO: Gera leads únicos a cada execução
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database
from ia_assistant import IAAssistant
from triagem_inteligente import TriagemInteligente
import json
import time
import random
from datetime import datetime

# Cores para o terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


# ============================================
# 🎲 GERADOR DE DADOS REALISTAS
# ============================================

NOMES_MASCULINOS = [
    "João", "Pedro", "Carlos", "Lucas", "Rafael", "Fernando", 
    "Gustavo", "Bruno", "Ricardo", "Rodrigo", "Marcos", "Paulo"
]

NOMES_FEMININOS = [
    "Maria", "Ana", "Juliana", "Patricia", "Fernanda", "Camila",
    "Beatriz", "Larissa", "Amanda", "Gabriela", "Mariana", "Carolina"
]

SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Costa", "Ferreira",
    "Rodrigues", "Almeida", "Nascimento", "Lima", "Araújo", "Carvalho",
    "Gomes", "Martins", "Rocha", "Ribeiro", "Barbosa", "Cardoso"
]

EMPRESAS_PORTE = {
    'pequeno': ['Loja', 'Boutique', 'Café', 'Studio', 'Consultoria'],
    'medio': ['Distribuidora', 'Comércio', 'Serviços', 'Empresa', 'Negócios'],
    'grande': ['Corporação', 'Group', 'Holding', 'Internacional', 'S.A.']
}


def gerar_nome_completo():
    """Gera um nome completo realista"""
    genero = random.choice(['M', 'F'])
    if genero == 'M':
        primeiro = random.choice(NOMES_MASCULINOS)
    else:
        primeiro = random.choice(NOMES_FEMININOS)
    
    sobrenome1 = random.choice(SOBRENOMES)
    sobrenome2 = random.choice(SOBRENOMES)
    
    return f"{primeiro} {sobrenome1} {sobrenome2}"


def gerar_telefone_unico():
    """Gera um telefone brasileiro único"""
    timestamp = int(time.time())
    ddd = random.randint(11, 99)
    # Usa timestamp nos últimos dígitos para garantir unicidade
    numero = f"{ddd}9{timestamp % 100000000:08d}"
    return f"55{numero}"


def gerar_nome_empresa(porte='medio'):
    """Gera nome de empresa realista"""
    sufixo = random.choice(EMPRESAS_PORTE.get(porte, EMPRESAS_PORTE['medio']))
    sobrenome = random.choice(SOBRENOMES)
    return f"{sobrenome} {sufixo}"


# ============================================
# 🎨 FUNÇÕES DE FORMATAÇÃO
# ============================================

def print_section(title):
    """Imprime uma seção formatada"""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}\n")


def print_success(message):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_info(message):
    """Imprime mensagem informativa"""
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")


def print_warning(message):
    """Imprime mensagem de aviso"""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")


def print_error(message):
    """Imprime mensagem de erro"""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


# ============================================
# 🔧 FUNÇÕES DE TESTE
# ============================================

def criar_lead_teste(db, nome=None, telefone=None):
    """Cria um lead de teste com dados únicos"""
    if not nome:
        nome = gerar_nome_completo()
    if not telefone:
        telefone = gerar_telefone_unico()
    
    print_info(f"Criando lead: {nome} | {telefone}")
    
    lead = db.create_or_get_lead(phone=telefone, name=nome)
    if lead:
        print_success(f"Lead criado com ID: {lead['id']}")
        return lead
    else:
        print_error("Falha ao criar lead")
        return None


def simular_conversa(db, ia_assistant, lead_id, conversa_script):
    """Simula uma conversa completa entre IA e lead"""
    print_section("📱 SIMULANDO CONVERSA COM O LEAD")
    
    for i, (lead_msg, esperado) in enumerate(conversa_script, 1):
        print(f"\n{Colors.BOLD}Rodada {i}:{Colors.ENDC}")
        print(f"  {Colors.OKCYAN}Lead:{Colors.ENDC} {lead_msg}")
        
        # Adicionar mensagem do lead
        db.add_message(
            lead_id=lead_id,
            sender_type='lead',
            sender_name='Lead Teste',
            content=lead_msg
        )
        
        # Processar com IA
        resposta_ia = ia_assistant.processar_mensagem(lead_id, lead_msg)
        
        if resposta_ia:
            print(f"  {Colors.OKGREEN}IA:{Colors.ENDC} {resposta_ia[:100]}...")
            
            # Verificar se resposta esperada está presente
            if esperado and esperado.lower() in resposta_ia.lower():
                print_success(f"Resposta contém keyword esperada: '{esperado}'")
            elif esperado:
                print_warning(f"Resposta não contém keyword esperada: '{esperado}'")
        else:
            print_info("IA não respondeu (lead pode estar qualificado ou escalado)")
        
        time.sleep(0.5)  # Simular delay entre mensagens
    
    print_success("Conversa simulada completa!")


def analisar_qualificacao(db, triagem, lead_id):
    """Analisa a qualificação final do lead"""
    print_section("📊 ANÁLISE DE QUALIFICAÇÃO")
    
    # Buscar lead atualizado
    lead = db.get_lead(lead_id)
    
    print(f"{Colors.BOLD}Dados do Lead:{Colors.ENDC}")
    print(f"  Nome: {lead.get('name', 'N/A')}")
    print(f"  Telefone: {lead.get('phone', 'N/A')}")
    print(f"  Status: {lead.get('status', 'N/A')}")
    print(f"  Interesse: {lead.get('interesse', 'N/A')}")
    print(f"  Orçamento: {lead.get('orcamento', 'N/A')}")
    print(f"  Prazo: {lead.get('prazo', 'N/A')}")
    print(f"  Preferência Contato: {lead.get('preferencia_contato', 'N/A')}")
    print(f"  Tipo Cliente: {lead.get('tipo_cliente', 'N/A')}")
    print(f"  Tamanho Empresa: {lead.get('tamanho_empresa', 'N/A')}")
    
    # Buscar respostas salvas
    respostas = db.get_lead_qualificacao_respostas(lead_id)
    
    print(f"\n{Colors.BOLD}Respostas Coletadas ({len(respostas)}):{Colors.ENDC}")
    for resp in respostas:
        print(f"  • {resp['pergunta_id']}: {resp['resposta'][:50]}...")
    
    # Buscar histórico de mensagens
    mensagens = db.get_messages_by_lead(lead_id)
    
    # Preparar dados para scoring
    respostas_dict = {r['pergunta_id']: r['resposta'] for r in respostas}
    historico = [{'sender_type': m['sender_type'], 'body': m['content']} for m in mensagens]
    
    # Calcular score
    print(f"\n{Colors.BOLD}Calculando Score...{Colors.ENDC}")
    resultado = triagem.calcular_score_completo(respostas_dict, historico)
    
    # Exibir resultado
    print_section("🎯 RESULTADO FINAL DA QUALIFICAÇÃO")
    
    score_total = resultado['score_total']
    score_maximo = resultado['score_maximo']
    percentual = resultado['percentual']
    classificacao = resultado['classificacao']
    prioridade = resultado['prioridade']
    is_vip = resultado['is_vip']
    
    # Cor baseada na classificação
    if classificacao == 'hot':
        cor = Colors.FAIL  # Vermelho (quente)
    elif classificacao == 'warm':
        cor = Colors.WARNING  # Amarelo (morno)
    else:
        cor = Colors.OKBLUE  # Azul (frio)
    
    print(f"{Colors.BOLD}Score:{Colors.ENDC} {cor}{score_total}/{score_maximo} ({percentual}%){Colors.ENDC}")
    print(f"{Colors.BOLD}Classificação:{Colors.ENDC} {cor}{classificacao.upper()}{Colors.ENDC}")
    print(f"{Colors.BOLD}Prioridade:{Colors.ENDC} {prioridade.upper()}")
    print(f"{Colors.BOLD}VIP:{Colors.ENDC} {'⭐ SIM' if is_vip else 'NÃO'}")
    print(f"{Colors.BOLD}Sentimento:{Colors.ENDC} {resultado['sentimento']}")
    print(f"{Colors.BOLD}Qualificado:{Colors.ENDC} {'✅ SIM' if resultado['qualificado'] else '❌ NÃO'}")
    
    # Breakdown do score
    print(f"\n{Colors.BOLD}Breakdown do Score:{Colors.ENDC}")
    breakdown = resultado['breakdown']
    
    if 'perguntas' in breakdown:
        print(f"\n  {Colors.BOLD}Perguntas:{Colors.ENDC}")
        for pergunta_id, dados in breakdown['perguntas'].items():
            print(f"    • {pergunta_id}: {dados['score']} pts - {dados['motivo']}")
    
    if 'sentimento' in breakdown:
        sent = breakdown['sentimento']
        print(f"\n  {Colors.BOLD}Sentimento:{Colors.ENDC}")
        print(f"    • {sent['classificacao']}: {sent['score']} pts")
    
    if 'penalidades' in breakdown and breakdown['penalidades']['motivos']:
        pen = breakdown['penalidades']
        print(f"\n  {Colors.BOLD}Penalidades:{Colors.ENDC}")
        for motivo in pen['motivos']:
            print(f"    • {motivo}")
    
    # Recomendações
    print(f"\n{Colors.BOLD}Recomendações:{Colors.ENDC}")
    for rec in resultado['recomendacoes']:
        print(f"  • {rec}")
    
    return resultado


# ============================================
# 🎯 CENÁRIOS DE TESTE
# ============================================

def teste_lead_vip():
    """Testa com um lead VIP (score alto)"""
    print_section("🔥 TESTE 1: LEAD VIP - SCORE ALTO")
    
    db = Database()
    ia_assistant = IAAssistant(db)
    triagem = TriagemInteligente()
    
    # Gerar dados únicos
    nome = gerar_nome_completo()
    telefone = gerar_telefone_unico()
    empresa = gerar_nome_empresa(porte='grande')
    
    # Criar lead
    lead = criar_lead_teste(db, nome, telefone)
    if not lead:
        return
    
    lead_id = lead['id']
    
    # Script de conversa (mensagem_lead, keyword_esperada_na_resposta)
    conversa = [
        ("Olá, quero contratar urgente!", "nome"),
        (nome, "interesse"),
        (f"Preciso de um CRM completo enterprise para {empresa}", "orçamento"),
        ("Tenho orçamento de R$ 150.000", "prazo"),
        ("Preciso implementar em até 1 semana", "contato"),
        ("WhatsApp e reunião presencial se necessário", "empresa"),
        ("Sim, para minha empresa", "funcionários"),
        ("Temos 350 funcionários", None)
    ]
    
    simular_conversa(db, ia_assistant, lead_id, conversa)
    resultado = analisar_qualificacao(db, triagem, lead_id)
    
    # Validações
    print_section("✅ VALIDAÇÕES")
    
    if resultado['score_total'] >= 80:
        print_success(f"Score VIP alcançado: {resultado['score_total']} >= 80")
    else:
        print_warning(f"Score não atingiu VIP: {resultado['score_total']} < 80")
    
    if resultado['is_vip']:
        print_success("Lead detectado como VIP ⭐")
    else:
        print_warning("Lead NÃO foi detectado como VIP")
    
    if resultado['classificacao'] == 'hot':
        print_success("Classificação HOT atribuída corretamente 🔥")
    else:
        print_warning(f"Classificação {resultado['classificacao']} (esperado: hot)")


def teste_lead_medio():
    """Testa com um lead médio (score normal)"""
    print_section("⚡ TESTE 2: LEAD MÉDIO - SCORE NORMAL")
    
    db = Database()
    ia_assistant = IAAssistant(db)
    triagem = TriagemInteligente()
    
    # Gerar dados únicos
    nome = gerar_nome_completo()
    telefone = gerar_telefone_unico()
    empresa = gerar_nome_empresa(porte='medio')
    
    lead = criar_lead_teste(db, nome, telefone)
    if not lead:
        return
    
    lead_id = lead['id']
    
    conversa = [
        ("Oi, queria saber mais sobre CRM", "nome"),
        (nome.split()[0], "interesse"),
        (f"Quero um sistema básico para {empresa}", "orçamento"),
        ("Tenho uns R$ 5.000 disponíveis", "prazo"),
        ("Não tenho pressa, pode ser em 30 dias", "contato"),
        ("E-mail está bom", "empresa"),
        ("É para meu negócio", "funcionários"),
        ("Somos 12 pessoas", None)
    ]
    
    simular_conversa(db, ia_assistant, lead_id, conversa)
    resultado = analisar_qualificacao(db, triagem, lead_id)
    
    print_section("✅ VALIDAÇÕES")
    
    if 40 <= resultado['score_total'] < 80:
        print_success(f"Score médio: {resultado['score_total']} (entre 40-79)")
    else:
        print_warning(f"Score fora da faixa média: {resultado['score_total']}")
    
    if resultado['classificacao'] in ['warm', 'cold']:
        print_success(f"Classificação {resultado['classificacao']} apropriada")


def teste_lead_frio():
    """Testa com um lead frio (score baixo)"""
    print_section("❄️ TESTE 3: LEAD FRIO - SCORE BAIXO")
    
    db = Database()
    ia_assistant = IAAssistant(db)
    triagem = TriagemInteligente()
    
    # Gerar dados únicos
    nome = gerar_nome_completo()
    telefone = gerar_telefone_unico()
    
    lead = criar_lead_teste(db, nome, telefone)
    if not lead:
        return
    
    lead_id = lead['id']
    
    conversa = [
        ("oi", "nome"),
        (nome.split()[0].lower(), "interesse"),
        ("só curiosidade", "orçamento"),
        ("não tenho dinheiro", "prazo"),
        ("talvez ano que vem", "contato"),
        ("tanto faz", None)
    ]
    
    simular_conversa(db, ia_assistant, lead_id, conversa)
    resultado = analisar_qualificacao(db, triagem, lead_id)
    
    print_section("✅ VALIDAÇÕES")
    
    if resultado['score_total'] < 40:
        print_success(f"Score baixo detectado: {resultado['score_total']} < 40")
    else:
        print_warning(f"Score acima do esperado: {resultado['score_total']}")
    
    if resultado['classificacao'] == 'cold':
        print_success("Classificação COLD atribuída corretamente ❄️")


def teste_lead_indeciso():
    """Testa com um lead indeciso (respostas vagas)"""
    print_section("🤔 TESTE 4: LEAD INDECISO - RESPOSTAS VAGAS")
    
    db = Database()
    ia_assistant = IAAssistant(db)
    triagem = TriagemInteligente()
    
    # Gerar dados únicos
    nome = gerar_nome_completo()
    telefone = gerar_telefone_unico()
    
    lead = criar_lead_teste(db, nome, telefone)
    if not lead:
        return
    
    lead_id = lead['id']
    
    conversa = [
        ("Olá", "nome"),
        (nome, "interesse"),
        ("Ainda estou vendo as opções", "orçamento"),
        ("Depende do valor", "prazo"),
        ("Não sei ainda", "contato"),
        ("Qualquer um serve", None)
    ]
    
    simular_conversa(db, ia_assistant, lead_id, conversa)
    resultado = analisar_qualificacao(db, triagem, lead_id)
    
    print_section("✅ VALIDAÇÕES")
    
    if 20 <= resultado['score_total'] < 60:
        print_success(f"Score de indecisão detectado: {resultado['score_total']}")
    
    if resultado['classificacao'] in ['cold', 'warm']:
        print_success(f"Classificação apropriada para indeciso: {resultado['classificacao']}")


# ============================================
# 📋 MENU PRINCIPAL
# ============================================

def menu_principal():
    """Menu de seleção de testes"""
    print_section("🧪 SISTEMA DE TESTES - QUALIFICAÇÃO DE IA")
    print_info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\nEscolha o teste a executar:")
    print("  1. 🔥 Lead VIP (score alto)")
    print("  2. ⚡ Lead Médio (score normal)")
    print("  3. ❄️  Lead Frio (score baixo)")
    print("  4. 🤔 Lead Indeciso (respostas vagas)")
    print("  5. 🎯 Todos os testes sequencialmente")
    print("  6. ❌ Sair")
    
    escolha = input("\nDigite o número da opção: ").strip()
    
    if escolha == '1':
        teste_lead_vip()
    elif escolha == '2':
        teste_lead_medio()
    elif escolha == '3':
        teste_lead_frio()
    elif escolha == '4':
        teste_lead_indeciso()
    elif escolha == '5':
        print_info("Executando todos os testes...")
        teste_lead_vip()
        time.sleep(2)
        teste_lead_medio()
        time.sleep(2)
        teste_lead_frio()
        time.sleep(2)
        teste_lead_indeciso()
    elif escolha == '6':
        print_info("Encerrando...")
        return
    else:
        print_error("Opção inválida!")
        return
    
    print_section("✅ TESTES CONCLUÍDOS")
    print_info("Verifique os resultados acima!")
    print_info("Você pode ver os leads criados em: http://localhost:5000")


if __name__ == '__main__':
    try:
        menu_principal()
    except KeyboardInterrupt:
        print_info("\n\nTeste interrompido pelo usuário")
    except Exception as e:
        print_error(f"Erro durante teste: {e}")
        import traceback
        traceback.print_exc()