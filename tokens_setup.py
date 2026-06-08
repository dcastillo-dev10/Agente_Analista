import sqlite3
import json

DB = r"C:\Users\Diego\.local\share\opencode\opencode.db"

con = sqlite3.connect(DB, timeout=5)
con.execute("PRAGMA journal_mode=WAL")
cur = con.cursor()

# Primer mensaje de cada sesión (el más limpio, sin historial acumulado) # el mio consume 8,619 de input y es el modelo Big Pickle
rows = cur.execute("""
    SELECT 
        s.title,
        s.model,
        m.id as msg_id,
        m.session_id,
        json_extract(m.data, '$.tokens.input') as tokens_input
    FROM message m
    JOIN session s ON s.id = m.session_id
    WHERE json_extract(m.data, '$.role') = 'assistant'
    ORDER BY m.time_created ASC
""").fetchall()

for title, model, msg_id, session_id, tokens_input in rows:
    if not tokens_input:
        continue

    # Buscar el prompt del usuario que generó ese mensaje
    user_part = cur.execute("""
        SELECT p.data FROM part p
        JOIN message m ON p.message_id = m.id
        WHERE m.session_id = ?
          AND json_extract(m.data, '$.role') = 'user'
        ORDER BY m.time_created ASC
        LIMIT 1
    """, (session_id,)).fetchone()

    if not user_part:
        continue

    prompt_text = json.loads(user_part[0]).get("text", "")
    # Estimación simple: ~4 chars por token
    prompt_tokens_est = len(prompt_text) // 4

    overhead = tokens_input - prompt_tokens_est

    try:
        model_id = json.loads(model).get("id", model)
    except:
        model_id = model

    print(f"Sesión  : {title or session_id[:24]}")
    print(f"Modelo  : {model_id}")
    print(f"Input total     : {tokens_input:,}")
    print(f"Tu prompt (est) : ~{prompt_tokens_est:,}")
    print(f"Overhead interno: ~{overhead:,}")
    print()

    break  # solo el primero, el más limpio

con.close()