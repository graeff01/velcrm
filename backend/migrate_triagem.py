import sqlite3
from datetime import datetime

def migrate_database():
    conn = sqlite3.connect('crm.db')
    cursor = conn.cursor()
    
    print("Iniciando migracao do sistema de triagem...")
    
    try:
        # Verificar se tabela leads existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
        if not cursor.fetchone():
            print("ERRO: Tabela leads nao existe!")
            return
        
        print("Atualizando tabela leads...")
        
        new_columns = [
            ("triage_status", "TEXT DEFAULT 'pendente'"),
            ("lead_score", "INTEGER DEFAULT 0"),
            ("priority", "TEXT DEFAULT 'normal'"),
            ("triage_completed_at", "DATETIME"),
            ("auto_responded", "INTEGER DEFAULT 0"),
            ("last_auto_response_at", "DATETIME"),
            ("budget_range", "TEXT"),
            ("urgency", "TEXT DEFAULT 'normal'"),
            ("qualified_by", "TEXT")
        ]
        
        for col_name, col_type in new_columns:
            try:
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
                print(f"  Coluna {col_name} adicionada")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"  Coluna {col_name} ja existe")
                else:
                    print(f"  Erro: {e}")
        
        print("Criando tabela de automacoes...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_automations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                automation_type TEXT NOT NULL,
                status TEXT DEFAULT 'agendado',
                scheduled_for DATETIME NOT NULL,
                sent_at DATETIME,
                message_content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        ''')
        print("  Tabela lead_automations criada")
        
        print("Criando tabela de follow-ups...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                followup_count INTEGER DEFAULT 1,
                last_followup_at DATETIME,
                next_followup_at DATETIME,
                max_followups INTEGER DEFAULT 3,
                followup_interval_hours INTEGER DEFAULT 24,
                status TEXT DEFAULT 'ativo',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        ''')
        print("  Tabela lead_followups criada")
        
        print("Criando indices...")
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_leads_triage_status ON leads(triage_status)",
            "CREATE INDEX IF NOT EXISTS idx_leads_priority ON leads(priority)",
            "CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_automations_scheduled ON lead_automations(scheduled_for, status)",
            "CREATE INDEX IF NOT EXISTS idx_followups_next ON lead_followups(next_followup_at, status)"
        ]
        
        for idx in indices:
            cursor.execute(idx)
        print("  Indices criados")
        
        print("Atualizando leads existentes...")
        cursor.execute('''
            UPDATE leads 
            SET triage_status = 'qualificado',
                triage_completed_at = created_at,
                qualified_by = 'manual',
                lead_score = 70
            WHERE assigned_to IS NOT NULL 
        ''')
        updated1 = cursor.rowcount
        
        cursor.execute('''
            UPDATE leads 
            SET triage_status = 'em_triagem',
                lead_score = 50
            WHERE assigned_to IS NULL 
              AND status = 'novo'
        ''')
        updated2 = cursor.rowcount
        
        print(f"  {updated1} leads qualificados, {updated2} em triagem")
        
        conn.commit()
        print("\nMigracao concluida com sucesso!")
        
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE triage_status = 'qualificado'")
        qualificados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE triage_status = 'em_triagem'")
        triagem = cursor.fetchone()[0]
        
        print(f"\nEstatisticas:")
        print(f"  Total de leads: {total}")
        print(f"  Qualificados: {qualificados}")
        print(f"  Em triagem: {triagem}")
        
    except Exception as e:
        print(f"\nErro durante migracao: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
