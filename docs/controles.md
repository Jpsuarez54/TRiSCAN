# Los 12 controles

> Este archivo se genera con `python scripts/generar_controles_md.py`. No lo edites a mano: cambia `src/triscan/controles.yaml`.

| ID | Pilar | Fase | Severidad | Control |
|---|---|---|---|---|
| [GOB-01](#gob-01) | Gobernanza | auditar | alta | Inventario de modelos y agentes con dueño y versión |
| [PRIV-01](#priv-01) | Privacidad | auditar | alta | Qué datos entran y salen de cada sistema |
| [SEC-01](#sec-01) | SecOps | auditar | critica | Permisos de cada agente declarados y mínimos |
| [SUM-01](#sum-01) | Gobernanza | auditar | alta | Origen y formato de los modelos verificados |
| [SEC-02](#sec-02) | SecOps | asegurar | alta | Guardrails de entrada y de salida |
| [PRIV-02](#priv-02) | Privacidad | asegurar | critica | Sin llaves ni contraseñas en el código o en los prompts |
| [SEC-03](#sec-03) | SecOps | asegurar | alta | Topes de presupuesto en cada agente |
| [SEC-04](#sec-04) | SecOps | asegurar | critica | Aprobación humana en acciones críticas |
| [MON-01](#mon-01) | Gobernanza | monitorear | alta | Registros inmutables de cada acción |
| [MON-02](#mon-02) | Gobernanza | monitorear | media | Alertas por desvíos y abuso |
| [EXP-01](#exp-01) | Explicabilidad | monitorear | media | Razonamiento guardado y respuestas con citas |
| [MON-03](#mon-03) | SecOps | monitorear | media | Pruebas de red team periódicas |

## GOB-01

**Inventario de modelos y agentes con dueño y versión**

- **Pilar:** Gobernanza · **Fase:** auditar · **Severidad:** alta
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** No se puede gobernar lo que no se sabe que existe. Cada modelo y agente necesita una persona responsable.
- **Cómo arreglarlo:** Crea ia-inventario.yaml (triscan init) y declara dueño, versión y origen de cada modelo y agente.
- **Riesgo:** Si nadie sabe qué modelos y agentes hay, nadie responde cuando uno falla o queda expuesto.
- **Referencias:** OWASP LLM LLM03 · NIST AI RMF GOVERN, MAP · ISO/IEC 42001 Anexo A

## PRIV-01

**Qué datos entran y salen de cada sistema**

- **Pilar:** Privacidad · **Fase:** auditar · **Severidad:** alta
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Sin saber qué clase de datos toca cada modelo o agente, no se puede protegerlos ni justificar su uso.
- **Cómo arreglarlo:** En el inventario, declara datos con una de estas clases por cada modelo y agente: publico, interno, personal, sensible.
- **Riesgo:** Un agente que lee datos personales sin que nadie lo sepa es una fuga esperando a ocurrir.
- **Referencias:** OWASP LLM LLM02 · NIST AI RMF MAP · ISO/IEC 42001 Anexo A

## SEC-01

**Permisos de cada agente declarados y mínimos**

- **Pilar:** SecOps · **Fase:** auditar · **Severidad:** critica
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Un agente con permisos amplios puede hacer mucho daño si se equivoca o lo manipulan.
- **Cómo arreglarlo:** Declara herramientas y permisos de cada agente. Usa permisos mínimos y evita herramientas con comodín o de administrador.
- **Riesgo:** Un agente con permisos de administrador puede hacer el mismo daño que un atacante con esas credenciales.
- **Referencias:** OWASP LLM LLM06 · NIST AI RMF MANAGE · ISO/IEC 42001 Anexo A

## SUM-01

**Origen y formato de los modelos verificados**

- **Pilar:** Gobernanza · **Fase:** auditar · **Severidad:** alta
- **Cómo se revisa:** leyendo el proyecto
- **Por qué importa:** Un modelo descargado es código de terceros. Algunos formatos (pickle) pueden ejecutar código al cargarse.
- **Cómo arreglarlo:** Usa formato safetensors, fija la revisión del modelo (revision=) y no actives trust_remote_code salvo que lo hayas revisado.
- **Riesgo:** Un modelo descargado de un repositorio público es código de terceros: puede ejecutar código al cargarlo.
- **Referencias:** OWASP LLM LLM03 · NIST AI RMF MAP, GOVERN · ISO/IEC 42001 Anexo A

## SEC-02

**Guardrails de entrada y de salida**

- **Pilar:** SecOps · **Fase:** asegurar · **Severidad:** alta
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Filtrar lo que entra y lo que sale reduce prompt injection y fuga de datos.
- **Cómo arreglarlo:** Agrega una librería de guardrails (por ejemplo LLM Guard, NeMo Guardrails o Guardrails AI) y decláralo en el inventario.
- **Riesgo:** Entrada y salida son los dos puntos donde un ataque se puede detener.
- **Referencias:** OWASP LLM LLM01, LLM02, LLM05 · NIST AI RMF MANAGE · ISO/IEC 42001 Anexo A

## PRIV-02

**Sin llaves ni contraseñas en el código o en los prompts**

- **Pilar:** Privacidad · **Fase:** asegurar · **Severidad:** critica
- **Cómo se revisa:** leyendo el proyecto
- **Por qué importa:** Una llave en el repositorio la puede ver cualquiera con acceso, y un modelo puede repetirla en sus respuestas.
- **Cómo arreglarlo:** Mueve los secretos a variables de entorno o a un gestor de secretos, rota las llaves expuestas y no subas archivos .env.
- **Riesgo:** Una llave en el código o en un prompt la puede leer cualquiera que vea el repositorio, los registros o la respuesta del modelo.
- **Referencias:** OWASP LLM LLM02, LLM07 · NIST AI RMF MANAGE · ISO/IEC 42001 Anexo A

## SEC-03

**Topes de presupuesto en cada agente**

- **Pilar:** SecOps · **Fase:** asegurar · **Severidad:** alta
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Un agente sin tope puede gastar sin límite o actuar durante horas sin que nadie lo note.
- **Cómo arreglarlo:** Declara en el inventario presupuesto con max_tokens, max_pasos o max_costo_usd.
- **Riesgo:** Un agente sin tope puede gastar sin control o repetir una acción dañina miles de veces.
- **Referencias:** OWASP LLM LLM10, LLM06 · NIST AI RMF MANAGE · ISO/IEC 42001 Anexo A

## SEC-04

**Aprobación humana en acciones críticas**

- **Pilar:** SecOps · **Fase:** asegurar · **Severidad:** critica
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Las acciones que cambian datos, mandan mensajes o ejecutan comandos necesitan que una persona las apruebe.
- **Cómo arreglarlo:** Marca aprobacion_humana en true para todo agente con herramientas críticas (ejecutar, borrar, enviar, pagar, desplegar).
- **Riesgo:** Sin aprobación humana, un error o un prompt malicioso basta para que un agente ejecute, borre o envíe algo que no se puede deshacer.
- **Referencias:** OWASP LLM LLM06 · NIST AI RMF MANAGE · ISO/IEC 42001 Anexo A

## MON-01

**Registros inmutables de cada acción**

- **Pilar:** Gobernanza · **Fase:** monitorear · **Severidad:** alta
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Si el propio agente puede borrar o cambiar el registro, la auditoría no sirve.
- **Cómo arreglarlo:** Envía los registros a un destino que el agente no pueda modificar y decláralo (destino e inmutable) con su evidencia.
- **Riesgo:** Si el agente puede borrar o editar sus registros, después no hay forma de saber qué pasó.
- **Referencias:** OWASP LLM LLM06 · NIST AI RMF MEASURE, GOVERN · ISO/IEC 42001 Anexo A

## MON-02

**Alertas por desvíos y abuso**

- **Pilar:** Gobernanza · **Fase:** monitorear · **Severidad:** media
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Sin alertas, un comportamiento raro se descubre tarde, cuando el daño ya ocurrió.
- **Cómo arreglarlo:** Configura alertas por uso inusual, costos y bloqueos de guardrails, y decláralas en el inventario.
- **Riesgo:** Sin alertas, un abuso o un desvío se descubre cuando ya hizo daño.
- **Referencias:** OWASP LLM LLM10 · NIST AI RMF MEASURE, MANAGE · ISO/IEC 42001 Anexo A

## EXP-01

**Razonamiento guardado y respuestas con citas**

- **Pilar:** Explicabilidad · **Fase:** monitorear · **Severidad:** media
- **Cómo se revisa:** con lo que declaras en ia-inventario.yaml
- **Por qué importa:** Poder revisar el razonamiento y las fuentes ayuda a detectar alucinaciones y decisiones sesgadas.
- **Cómo arreglarlo:** Guarda el razonamiento del agente (registra_razonamiento) y, si usas RAG, haz que cite sus fuentes (citas).
- **Riesgo:** Sin el razonamiento ni las fuentes, no se puede explicar ni corregir una decisión del modelo.
- **Referencias:** OWASP LLM LLM09 · NIST AI RMF MEASURE · ISO/IEC 42001 Anexo A

## MON-03

**Pruebas de red team periódicas**

- **Pilar:** SecOps · **Fase:** monitorear · **Severidad:** media
- **Cómo se revisa:** leyendo el proyecto
- **Por qué importa:** Los ataques cambian. Probar tu propio sistema con regularidad encuentra fallas antes que los atacantes.
- **Cómo arreglarlo:** Agrega pruebas automáticas (por ejemplo promptfoo, garak o PyRIT) a tu proceso y repítelas, o declara la fecha de la última prueba.
- **Riesgo:** Es mejor encontrar la brecha tú que enterarte por un incidente.
- **Referencias:** OWASP LLM LLM01 · NIST AI RMF MEASURE · ISO/IEC 42001 Anexo A
