import sqlite3
import json
import time
from datetime import datetime

DB = r"C:\Users\Diego\.local\share\opencode\opencode.db"

def get_session_state():
    con = sqlite3.connect(DB, timeout=5)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    rows = cur.execute("""
        SELECT id, title, model, cost,
               tokens_input, tokens_output, tokens_reasoning,
               tokens_cache_read, tokens_cache_write,
               time_updated
        FROM session
        ORDER BY time_updated DESC
    """).fetchall()
    con.close()
    return {r[0]: r for r in rows}

def get_last_prompt(session_id):
    con = sqlite3.connect(DB, timeout=5)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    row = cur.execute("""
        SELECT p.data FROM part p
        JOIN message m ON p.message_id = m.id
        WHERE m.session_id = ?
          AND json_extract(m.data, '$.role') = 'user'
        ORDER BY p.time_created DESC
        LIMIT 1
    """, (session_id,)).fetchone()
    con.close()
    if not row:
        return None
    try:
        data = json.loads(row[0])
        return data.get("text", "").strip() or None
    except:
        return None

def fmt(n):
    return f"{n or 0:,}"

prev = get_session_state()
print("Monitor listo. Esperando respuestas de opencode...\n")

try:
    while True:
        time.sleep(2)
        curr = get_session_state()

        for sid, row in curr.items():
            (_, title, model, cost,
             inp, out, reas, cr, cw, updated) = row

            p = prev.get(sid)
            if p is None or updated == p[9]:
                continue

            d_inp  = inp  - (p[4] or 0)
            d_out  = out  - (p[5] or 0)
            d_reas = reas - (p[6] or 0)
            d_cr   = cr   - (p[7] or 0)

            if d_out == 0:
                continue

            ts = datetime.now().strftime("%H:%M:%S")
            try:
                model_id = json.loads(model).get("id", model)
            except:
                model_id = model

            prompt = get_last_prompt(sid)
            prompt_preview = ""
            if prompt:
                clean = prompt[:100].replace('\n', ' ')
                prompt_preview = clean + ("..." if len(prompt) > 100 else "")

            print(f"[{ts}] {title or sid[:24]}")
            print(f"  Modelo     : {model_id}")
            if prompt_preview:
                print(f"  Prompt     : {prompt_preview}")
            print(f"  Δ Input    : +{fmt(d_inp)}")
            print(f"  Δ Output   : +{fmt(d_out)}")
            print(f"  Δ Reasoning: +{fmt(d_reas)}")
            print(f"  Δ Cache R  : +{fmt(d_cr)}")
            print(f"  Total acum : in={fmt(inp)}  out={fmt(out)}")
            print(f"  Costo acum : ${cost:.6f}")
            print()

        prev = curr

except KeyboardInterrupt:
    print("Monitor detenido.")