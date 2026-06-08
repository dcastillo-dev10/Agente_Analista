# Preguntas: 

**1. ¿Por qué el orden de tu AGENTS.md importa, no solo el tamaño?**

El orden importa porque los modelos no procesan todas las instrucciones con la misma relevancia. Las instrucciones críticas colocadas al inicio tienen mayor probabilidad de influir en la toma de decisiones durante la generación. Si las reglas importantes quedan enterradas en medio de contexto descriptivo, compiten por atención con información menos relevante.

---

**2. ¿Por qué generar output cuesta más que leer input?**

Leer información es una tarea de reconocimiento; generar una respuesta implica tomar decisiones constantemente. Cada línea de código, validación o explicación requiere evaluar múltiples alternativas posibles.

En mi caso, el agente puede analizar rápidamente un Excel, pero generar una solución correcta exige decidir qué columnas usar, cómo relacionar tablas, qué validaciones aplicar y qué riesgos existen. Por eso la generación consume más razonamiento que la simple lectura.

---

**3. Módulo legacy con 30 gotchas: ¿raíz, memory/dominio o RAG? ¿Por qué?**

Lo colocaría principalmente en memory/dominio.

Los 30 gotchas representan conocimiento específico del dominio y problemas recurrentes que aparecen constantemente. No son reglas universales del agente ni información que deba cargarse en cada tarea.

Solo dejaría en la raíz los gotchas más críticos que puedan provocar errores graves. Si los gotchas son extensos o cambian frecuentemente, evaluaría RAG para cargarlos bajo demanda.