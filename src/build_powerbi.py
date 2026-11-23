"""Create a portable Power BI model snapshot and native trend visual bindings."""

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "powerbi"


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def table_definition(name, file, numeric, measures=None):
    data = pd.read_csv(ROOT / file).astype(object)
    if name == "NationalCrop":
        data = data[data.crop.isin(["Wheat", "Rice", "Maize (corn)"])]
    data = data.where(pd.notna(data), None)
    columns = list(data.columns)
    # Embedded immutable snapshot: portable and credential-free. Regenerate to refresh.
    rows = json.dumps(data.values.tolist(), ensure_ascii=False, allow_nan=False)
    escaped = rows.replace('"', '""')
    names = ", ".join('"' + column + '"' for column in columns)
    type_rules = ", ".join('{"' + column + '", ' + ("Int64.Type" if dtype == "int64" else "type number") + '}'
                           for column, dtype in numeric.items())
    expression = f'let Rows = Json.Document("{escaped}"), Source = Table.FromRows(Rows, {{{names}}}), Typed = Table.TransformColumnTypes(Source, {{{type_rules}}}, "en-US") in Typed'
    table = {"name": name, "columns": [{"name": column, "dataType": numeric.get(column, "string"),
               "sourceColumn": column, "summarizeBy": "none"} for column in columns],
             "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": expression}}]}
    if measures:
        table["measures"] = [{"name": title, "expression": dax, "formatString": "#,0.00"} for title, dax in measures.items()]
    return table


def field(entity, property, measure=False):
    return {"Measure" if measure else "Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": property}}


def projection(entity, property, measure=False):
    return {"field": field(entity, property, measure), "queryRef": f"{entity}.{property}", "nativeQueryRef": property}


def main():
    national = table_definition("NationalCrop", "datasets/gold/fact_crop_national.csv",
        {"year": "int64", "area_ha": "double", "production_kg": "double", "yield_kg_ha": "double",
         "governorate_mean_temperature_c": "double", "governorate_mean_precipitation_mm": "double", "climate_governorate_count": "int64"},
        {"Crop yield kg per ha": "AVERAGE('NationalCrop'[yield_kg_ha])"})
    climate = table_definition("Climate", "datasets/gold/fact_climate_annual.csv",
        {"year": "int64", "governorate_id": "int64", "mean_temperature_c": "double", "annual_precipitation_mm": "double"},
        {"Governorate mean temperature C": "AVERAGE('Climate'[mean_temperature_c])",
         "Governorate mean precipitation mm": "AVERAGE('Climate'[annual_precipitation_mm])"})
    model = {"name": "AquaAgri", "compatibilityLevel": 1601,
             "model": {"culture": "en-US", "defaultPowerBIDataSourceVersion": "powerBI_V3", "tables": [national, climate]}}
    write(BASE / "AquaAgri.SemanticModel/model.bim", model)
    write(BASE / "AquaAgri.SemanticModel/definition.pbism", {"version": "1.0", "settings": {}})
    pages = BASE / "AquaAgri.Report/definition/pages"
    metadata = json.loads((pages / "pages.json").read_text())
    page_id = metadata["pageOrder"][0]
    path = pages / page_id
    page = json.loads((path / "page.json").read_text())
    page.update({"displayName": "National yield and climate context (not causal)", "width": 1280, "height": 1000})
    write(path / "page.json", page)
    specs = [
        ("yield_trends", "NationalCrop", "Crop yield kg per ha", "National crop yield (kg/ha) — one line per crop", "crop"),
        ("temperature_trends", "Climate", "Governorate mean temperature C", "Temperature °C — unweighted governorate mean", None),
        ("rainfall_trends", "Climate", "Governorate mean precipitation mm", "Annual rainfall mm — unweighted governorate mean", None),
    ]
    for index, (name, entity, measure, title, series) in enumerate(specs):
        state = {"Category": {"projections": [projection(entity, "year")]},
                 "Y": {"projections": [projection(entity, measure, True)]}}
        if series:
            state["Series"] = {"projections": [projection(entity, series)]}
        visual = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
                  "name": name, "position": {"x": 30, "y": 20 + 320*index, "z": index, "height": 300, "width": 1220, "tabOrder": index},
                  "visual": {"visualType": "lineChart", "query": {"queryState": state,
                       "sortDefinition": {"sort": [{"field": field(entity, "year"), "direction": "Ascending"}]}},
                       "visualContainerObjects": {"title": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}},
                             "text": {"expr": {"Literal": {"Value": "'" + title + "'"}}}}}]},
                       "drillFilterOtherVisuals": True}}
        write(path / "visuals" / name / "visual.json", visual)
    print("Built Power BI model snapshot and three native line charts")


if __name__ == "__main__":
    main()
