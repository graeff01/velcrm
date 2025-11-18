import sqlite3
conn = sqlite3.connect('crm.db')
c = conn.cursor()

# Criar tabela lead_followups
c.execute('''
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

# Criar tabela lead_automations
c.execute('''
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

conn.commit()
conn.close()
print('Tabelas criadas!')
