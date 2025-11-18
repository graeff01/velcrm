# test_create_lead.py
from database import Database

db = Database()

# Criar 3 leads de teste
leads_teste = [
    {
        'name': 'João Silva',
        'phone': '5551999887766',
        'status': 'novo'
    },
    {
        'name': 'Maria Santos',
        'phone': '5551988776655',
        'status': 'novo'
    },
    {
        'name': 'Carlos Oliveira',
        'phone': '5551977665544',
        'status': 'novo'
    }
]

print("🧪 Criando leads de teste...")

for lead_data in leads_teste:
    lead = db.create_or_get_lead(
        phone=lead_data['phone'],
        name=lead_data['name']
    )
    if lead:
        print(f"✅ Lead criado: {lead['name']} (ID: {lead['id']})")
    else:
        print(f"❌ Erro ao criar: {lead_data['name']}")

print("\n📊 Verificando leads no banco...")
all_leads = db.get_all_leads()
print(f"Total de leads: {len(all_leads)}")

for lead in all_leads:
    print(f"  • {lead['name']} - Status: {lead['status']}")