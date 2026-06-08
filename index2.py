import pandas as pd
import re
import unicodedata

# =========================
# ARCHIVOS
# =========================

archivo_aulas = "estadistica_aulas.xlsx"
archivo_becados = "reporte_becados.xlsx"

# =========================
# UTILIDADES
# =========================

def normalize_column_name(name: str) -> str:
    name = str(name)
    name = unicodedata.normalize("NFKD", name)
    name = "".join(ch for ch in name if not unicodedata.combining(ch))
    name = name.lower()
    name = re.sub(r"[\W_]+", "", name)
    return name


def get_column_candidates(df: pd.DataFrame) -> dict[str, str]:
    return {normalize_column_name(col): col for col in df.columns}


def is_equivalent_column(normalized_name: str, normalized_required: str) -> bool:
    if normalized_name == normalized_required:
        return True

    synonyms = {
        "codigoaula": {"aula", "codigoaula", "codigodeaula"},
        "dni": {"dni", "doc", "documento", "numeroidentidad", "documentodenidentidad"},
        "periodo": {"periodo", "periodo"},
        "seccion": {"seccion", "seccion"},
    }
    return normalized_name in synonyms.get(normalized_required, set())


def rename_columns(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    normalized_actual = get_column_candidates(df)
    rename_map = {}
    already_matched = set()
    missing_columns = []

    for column in required_columns:
        norm_required = normalize_column_name(column)
        matched = None

        # Prefer exact normalized matches first.
        if norm_required in normalized_actual:
            matched = normalized_actual[norm_required]
            already_matched.add(matched)

        # Otherwise use synonym mapping among unmatched actual columns.
        if matched is None:
            for actual_norm, actual_name in normalized_actual.items():
                if actual_name in already_matched:
                    continue
                if is_equivalent_column(actual_norm, norm_required):
                    matched = actual_name
                    already_matched.add(actual_name)
                    break

        if matched is not None:
            rename_map[matched] = column
        else:
            missing_columns.append(column)

    if missing_columns:
        raise KeyError(
            f"Faltan columnas requeridas en el archivo: {missing_columns}. "
            f"Columnas encontradas: {list(df.columns)}"
        )

    return df.rename(columns=rename_map)


def ensure_codigo_aula_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Codigo Aula" not in df.columns and "Aula" in df.columns:
        df = df.copy()
        df["Codigo Aula"] = df["Aula"]
    return df


# =========================
# ESTADÍSTICA DE AULAS
# =========================

columnas_reporte = [
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
    "Total Mat/Susp"
]

try:
    df_aulas = pd.read_excel(archivo_aulas)
    df_aulas = df_aulas.rename(columns=lambda c: str(c).strip())
    df_aulas = ensure_codigo_aula_column(df_aulas)
    df_aulas = rename_columns(df_aulas, columnas_reporte)
except FileNotFoundError as exc:
    raise SystemExit(f"No se encontró el archivo de aulas: {archivo_aulas}") from exc
except KeyError as exc:
    raise SystemExit(f"Error en el archivo de aulas: {exc}") from exc

reporte = (
    df_aulas[columnas_reporte]
    .drop_duplicates(subset=["Codigo Aula"])
)

# =========================
# BECADOS
# =========================

try:
    df_becados = pd.read_excel(archivo_becados)
    df_becados = df_becados.rename(columns=lambda c: str(c).strip())
    df_becados = ensure_codigo_aula_column(df_becados)
    df_becados = rename_columns(df_becados, ["Dni", "Codigo Aula"])
except FileNotFoundError as exc:
    raise SystemExit(f"No se encontró el archivo de becados: {archivo_becados}") from exc
except KeyError as exc:
    raise SystemExit(f"Error en el archivo de becados: {exc}") from exc

# Eliminar DNIs repetidos

df_becados = df_becados.drop_duplicates(subset=["Dni"])

# Contar becados por aula
becados_por_aula = (
    df_becados
    .groupby("Codigo Aula")
    .size()
    .reset_index(name="Becados Unicos")
)

# =========================
# UNIÓN
# =========================

reporte_final = reporte.merge(
    becados_por_aula,
    on="Codigo Aula",
    how="left"
)

# Reemplazar nulos por 0
reporte_final["Becados Unicos"] = (
    reporte_final["Becados Unicos"]
    .fillna(0)
    .astype(int)
)

# =========================
# EXPORTAR
# =========================

reporte_final.to_excel(
    "Reporte_Aulas_Becados.xlsx",
    index=False
)

print("Reporte generado correctamente")
