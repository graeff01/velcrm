import sqlite3

print("🔧 Iniciando patch triage_status...")

conn = sqlite3.connect("database.db")
c = conn.cursor()

try:
    c.execute("ALTER TABLE leads ADD COLUMN triage_status TEXT DEFAULT 'none'")
    print("✅ Coluna triage_status adicionada!")
except Exception as e:
    print("ℹ️ Coluna já existe ou erro ignorado:", e)

conn.commit()
conn.close()

print("✔️ Patch finalizado!")
