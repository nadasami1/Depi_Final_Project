import pandas as pd

# irrigation
d1 = pd.read_csv(r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\raw\FAOSTAT\faostat_irrigation.csv")
d1 = d1[["Item", "Year", "Value", "Unit"]]
d1 = d1.pivot_table(index="Year", columns="Item", values="Value", aggfunc="first").reset_index()
d1.to_csv(r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\processed\FAOSTAT\faostat_irrigation_clean.csv", index=False)

# crop
d2 = pd.read_csv(r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\raw\FAOSTAT\faostat_crop_production_egypt_2016_2020.csv")
d2 = d2[["Item", "Year", "Element", "Value", "Unit"]]
d2 = d2.pivot_table(index=["Item", "Year"], columns="Element", values="Value", aggfunc="first").reset_index()
d2.to_csv(r"C:\Users\GOLDEN TECH\Downloads\AquaAgri_Egypt\Data\processed\FAOSTAT\faostat_crop_clean.csv", index=False)