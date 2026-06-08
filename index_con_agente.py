# =============================================================================
#  OBJETIVO
# =============================================================================
# Generar un reporte consolidado de aulas y becados, eliminando duplicados,
# contando becados únicos por aula y exportando un Excel final con la columna
# "Becados Unicos".
#
#  ENTRADAS
# - estadistica_aulas.xlsx   (información de aulas)
# - reporte_becados.xlsx     (información de becados)
#
#  SALIDA
# - Reporte_Aulas_Becados.xlsx
#
#  FLUJO
# 1. Descubrimiento y perfilado de cada archivo
# 2. Normalización de nombres de columna
# 3. Validación de columnas requeridas
# 4. Eliminación de duplicados (Codigo Aula / Dni)
# 5. Conteo de becados únicos por aula
# 6. Merge left (aulas + becados)
# 7. Control de calidad post-merge
# 8. Exportación
# =============================================================================

import pandas as pd
import re
import unicodedata
import os
import sys
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

ARCHIVO_AULAS = "estadistica_aulas.xlsx"
ARCHIVO_BECADOS = "reporte_becados.xlsx"
ARCHIVO_SALIDA = "Reporte_Aulas_Becados.xlsx"

COLUMNAS_AULAS = [
    "Codigo Aula",
    "Local",
    "Período",
    "Nivel",
    "Grado",
    "Sección",
    "Aula",
    "Capacidad",
    "Matriculados",
    "Suspendidos",
    "Pre-inscritos",
    "Total Mat/Susp",
]

COLUMNAS_BECADOS = ["Dni", "Codigo Aula"]

SINONIMOS = {
    "codigoaula": {"codigoaula", "codigodeaula", "cod_aula", "cod_aulas", "aula", "codigo"},
    "dni": {"dni", "doc", "documento", "numeroidentidad", "documentodenidentidad", "nrodoc", "nrodocumento"},
    "local": {"local", "locales", "sede"},
    "periodo": {"periodo", "periodo", "anio", "year", "ciclo"},
    "nivel": {"nivel", "nivelacademico"},
    "grado": {"grado", "gradoacademico"},
    "seccion": {"seccion", "seccion", "secc"},
    "capacidad": {"capacidad", "capacidadmaxima", "cupo", "vacantes"},
    "matriculados": {"matriculados", "matricula", "nromatriculados"},
    "suspendidos": {"suspendidos", "suspenso", "susp"},
    "preinscritos": {"preinscritos", "preinscrito", "pre_inscritos", "preinscripcion", "pre-inscritos"},
    "totalmatsusp": {"totalmatsusp", "totalmatsus", "totalmatsusp", "totalmatriculadosuspendidos"},
}

# =============================================================================
# UTILIDADES
# =============================================================================

def normalize_column_name(name: str) -> str:
    name = str(name).strip()
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = re.sub(r"[\W_]+", "", name)
    return name.lower()


def build_column_map(df: pd.DataFrame) -> dict[str, str]:
    return {normalize_column_name(col): col for col in df.columns}


def resolve_column(norm_candidate: str, norm_required: str) -> bool:
    if norm_candidate == norm_required:
        return True
    return norm_candidate in SINONIMOS.get(norm_required, set())


def validate_and_rename(df: pd.DataFrame, required: list[str], source: str) -> pd.DataFrame:
    norm_map = build_column_map(df)
    rename = {}
    missing = []
    matched_actual = set()

    for req in required:
        norm_req = normalize_column_name(req)
        found = None

        # 1. coincidencia exacta normalizada
        if norm_req in norm_map:
            found = norm_map[norm_req]
            matched_actual.add(found)

        # 2. búsqueda por sinónimos entre columnas aún no emparejadas
        if found is None:
            for act_norm, act_name in norm_map.items():
                if act_name in matched_actual:
                    continue
                if resolve_column(act_norm, norm_req):
                    found = act_name
                    matched_actual.add(act_name)
                    break

        if found is not None:
            rename[found] = req
        else:
            missing.append(req)

    if missing:
        print(f"  [!] Columnas requeridas NO encontradas en {source}: {missing}")
        print(f"  [!] Columnas disponibles    : {list(df.columns)}")
        sys.exit(1)

    return df.rename(columns=rename)


def check_file(path: str) -> None:
    if not os.path.exists(path):
        print(f"[ERROR] Archivo no encontrado: {path}")
        print(f"        Ruta absoluta esperada: {os.path.abspath(path)}")
        sys.exit(1)


def profile_dataframe(df: pd.DataFrame, name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  PERFIL: {name}")
    print(f"{'='*60}")
    print(f"  Shape       : {df.shape[0]:>8} filas x {df.shape[1]:>3} columnas")
    print(f"  Columnas    : {list(df.columns)}")
    print(f"  Duplicados  : {df.duplicated().sum():>8}")
    print(f"  Nulos       :")
    for col in df.columns:
        nulos = df[col].isna().sum()
        if nulos:
            print(f"    - {col}: {nulos}")
    print(f"  dtypes      :\n{df.dtypes.to_string()}")
    print(f"\n  Head (5):\n{df.head().to_string(index=False)}")


def quality_check(aulas: pd.DataFrame, becados_count: pd.DataFrame,
                  merged: pd.DataFrame) -> None:
    print(f"\n{'='*60}")
    print("  CONTROL DE CALIDAD POST-MERGE")
    print(f"{'='*60}")

    aulas_orig = aulas["Codigo Aula"].nunique()
    aulas_merge = merged["Codigo Aula"].nunique()
    print(f"  Aulas únicas origen           : {aulas_orig}")
    print(f"  Aulas únicas en merge         : {aulas_merge}")

    becados_total = int(becados_count["Becados Unicos"].sum())
    becados_merge = int(merged["Becados Unicos"].sum())
    print(f"  Becados únicos origen         : {becados_total}")
    print(f"  Becados únicos en merge       : {becados_merge}")

    aulas_sin_becados = (merged["Becados Unicos"] == 0).sum()
    print(f"  Aulas sin becados             : {aulas_sin_becados}")

    perdidas = aulas_orig - aulas_merge
    if perdidas:
        print(f"  [ADVERTENCIA] Aulas perdidas en merge: {perdidas}")
    else:
        print(f"  Integridad de aulas           : OK")

    print(f"  Shape final                   : {merged.shape[0]} filas x {merged.shape[1]} columnas")


# =============================================================================
# FASE 1 — VALIDACIÓN DE ARCHIVOS
# =============================================================================

print(f"\n{'#'*60}")
print(f"  REPORTE CONSOLIDADO AULAS - BECADOS")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'#'*60}")

print(f"\n[1/8] Validando archivos...")
check_file(ARCHIVO_AULAS)
check_file(ARCHIVO_BECADOS)
print("  OK")

# =============================================================================
# FASE 2 — DESCARGA Y PERFILADO
# =============================================================================

print(f"\n[2/8] Leyendo y perfilando datos...")

df_aulas_raw = pd.read_excel(ARCHIVO_AULAS)
df_aulas_raw.columns = [str(c).strip() for c in df_aulas_raw.columns]
profile_dataframe(df_aulas_raw, ARCHIVO_AULAS)

df_becados_raw = pd.read_excel(ARCHIVO_BECADOS)
df_becados_raw.columns = [str(c).strip() for c in df_becados_raw.columns]
profile_dataframe(df_becados_raw, ARCHIVO_BECADOS)

# =============================================================================
# FASE 3 — NORMALIZACIÓN DE COLUMNAS
# =============================================================================

print(f"\n[3/8] Normalizando columnas...")

df_aulas = validate_and_rename(df_aulas_raw, COLUMNAS_AULAS, ARCHIVO_AULAS)

# Si existe columna "Aula" pero no "Codigo Aula", copiarla
if "Codigo Aula" not in df_aulas.columns and "Aula" in df_aulas.columns:
    df_aulas["Codigo Aula"] = df_aulas["Aula"]
    print("  [INFO] Columna 'Codigo Aula' creada desde 'Aula'")

df_becados = validate_and_rename(df_becados_raw, COLUMNAS_BECADOS, ARCHIVO_BECADOS)

if "Codigo Aula" not in df_becados.columns and "Aula" in df_becados.columns:
    df_becados["Codigo Aula"] = df_becados["Aula"]
    print("  [INFO] Columna 'Codigo Aula' (becados) creada desde 'Aula'")

print("  OK")

# =============================================================================
# FASE 4 — ELIMINACIÓN DE DUPLICADOS
# =============================================================================

print(f"\n[4/8] Eliminando duplicados...")

dup_aulas_antes = df_aulas.duplicated(subset=["Codigo Aula"]).sum()
df_aulas_sd = df_aulas.drop_duplicates(subset=["Codigo Aula"]).copy()
print(f"  Aulas  : {dup_aulas_antes} duplicado(s) eliminado(s) por 'Codigo Aula'  ({df_aulas_sd.shape[0]} únicos)")

dup_becados_antes = df_becados.duplicated(subset=["Dni"]).sum()
df_becados_sd = df_becados.drop_duplicates(subset=["Dni"]).copy()
print(f"  Becados: {dup_becados_antes} duplicado(s) eliminado(s) por 'Dni'         ({df_becados_sd.shape[0]} únicos)")

# =============================================================================
# FASE 5 — CONTEO DE BECADOS ÚNICOS POR AULA
# =============================================================================

print(f"\n[5/8] Contando becados únicos por aula...")

becados_por_aula = (
    df_becados_sd
    .groupby("Codigo Aula", as_index=False)
    .agg({"Dni": "nunique"})
    .rename(columns={"Dni": "Becados Unicos"})
)

print(f"  Aulas con becados: {becados_por_aula.shape[0]}")

# =============================================================================
# FASE 6 — MERGE
# =============================================================================

print(f"\n[6/8] Fusionando datasets por 'Codigo Aula'...")

reporte = df_aulas_sd[COLUMNAS_AULAS].merge(
    becados_por_aula,
    on="Codigo Aula",
    how="left",
)

print(f"  Shape pre-merge (aulas) : {df_aulas_sd.shape}")
print(f"  Shape post-merge        : {reporte.shape}")

# =============================================================================
# FASE 7 — CONTROL DE CALIDAD
# =============================================================================

print(f"\n[7/8] Control de calidad...")

reporte["Becados Unicos"] = reporte["Becados Unicos"].fillna(0).astype(int)

quality_check(df_aulas_sd, becados_por_aula, reporte)

# =============================================================================
# FASE 8 — EXPORTACIÓN
# =============================================================================

print(f"\n[8/8] Exportando...")

if os.path.exists(ARCHIVO_SALIDA):
    print(f"  [INFO] Sobrescribiendo: {ARCHIVO_SALIDA}")

reporte.to_excel(ARCHIVO_SALIDA, index=False)
print(f"  Reporte generado: {os.path.abspath(ARCHIVO_SALIDA)}")
print(f"  Shape final     : {reporte.shape[0]} filas x {reporte.shape[1]} columnas")
print()
print(f"{'#'*60}")
print(f"  PROCESO COMPLETADO EXITOSAMENTE")
print(f"{'#'*60}")
