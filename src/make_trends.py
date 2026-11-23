"""Generate reproducible national crop/climate trends without claiming causation."""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = pd.read_csv(ROOT / "datasets/gold/fact_crop_national.csv")
    output = ROOT / "reports/trends"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, constrained_layout=True)
    colors = {"Wheat": "#236c88", "Rice": "#b77520", "Maize (corn)": "#548548"}
    for crop, color in colors.items():
        table = data[data.crop == crop].sort_values("year")
        axes[0].plot(table.year, table.yield_kg_ha, marker="o", label=crop, color=color, linewidth=2)
    axes[0].set_ylabel("Crop yield (kg/ha)")
    axes[0].legend(ncol=3, frameon=False, loc="upper left")
    climate = data.drop_duplicates("year").sort_values("year")
    axes[1].plot(climate.year, climate.governorate_mean_temperature_c, marker="o", color="#ba583b", linewidth=2)
    axes[1].set_ylabel("Temperature (°C)")
    axes[2].plot(climate.year, climate.governorate_mean_precipitation_mm, marker="o", color="#236c88", linewidth=2)
    axes[2].set_ylabel("Precipitation (mm)")
    for ax in axes:
        ax.grid(axis="y", alpha=.2)
        ax.set_xticks(range(2016, 2021))
    fig.suptitle("Egypt: crop yield and climate context, 2016–2020", fontsize=18, fontweight="bold")
    axes[2].set_xlabel("Year\nClimate is an unweighted mean of 27 governorates; not crop-area weighted.\n"
                       "Five annual observations show co-movement only, not causal climate effects. Source flags retained in raw FAOSTAT data.")
    fig.savefig(output / "climate_vs_yield.png", dpi=160)
    plt.close(fig)
    data.to_csv(output / "climate_vs_yield.csv", index=False)
    print(f"Saved trend data and chart: {output}")


if __name__ == "__main__":
    main()
