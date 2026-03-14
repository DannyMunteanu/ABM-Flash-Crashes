"""
Plot.py — Run this after Runner.py to generate histogram and normal curve plots
for crash severity and recovery time across all simulation configurations.

Reads from:
  - data/ExperimentRawResults.csv
  - data/ExperimentSeveritySummary.csv
  - data/ExperimentRecoverySummary.csv

Outputs plots to: Graphs/ directory
"""

import os
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from scipy.stats import norm

r = os.path.dirname(os.path.abspath(__file__))
dataDir = os.path.join(r, "data")
plotDir = os.path.join(r, "Graphs")
os.makedirs(plotDir, exist_ok=True)


def readCsv(filepath: str) -> list:
    with open(filepath, "r") as f:
        return list(csv.DictReader(f))


def floatOrNone(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def toPascalCase(simName: str) -> str:
    """
    Converts a simulation name string to PascalCase for use in filenames.
    For example: 'Baseline Model with HFT' -> 'BaselineModelWithHft'
    Parameters:
        simName: The simulation name string to convert.
    """
    return "".join(word.capitalize() for word in simName.split())


def plotHistogramWithNormalCurve(
        values: list,
        mean: float,
        std: float,
        title: str,
        xlabel: str,
        colour: str,
        outputPath: str,
):
    """
    Plots a histogram of values with a fitted normal curve overlaid.
    Parameters:
        values: List of float data points.
        mean: Mean of the distribution.
        std: Standard deviation of the distribution.
        title: Plot title.
        xlabel: X-axis label.
        colour: Bar colour.
        outputPath: File path to save the plot.
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0f0f0f")
    ax.set_facecolor("#1a1a1a")

    ax.hist(
        values, bins=12, density=True,
        color=colour, alpha=0.75, edgecolor="#0f0f0f", linewidth=0.8,
    )

    if std > 0:
        xMin, xMax = min(values) - std, max(values) + std
        x = np.linspace(xMin, xMax, 300)
        p = norm.pdf(x, mean, std)
        ax.plot(x, p, color="white", linewidth=2, linestyle="--", label=f"Normal curve\nμ={mean:.2f}, σ={std:.2f}")
        ax.axvline(mean, color="#ffcc00", linewidth=1.5, linestyle=":", label=f"Mean = {mean:.2f}")
        ax.legend(facecolor="#2a2a2a", edgecolor="#444", labelcolor="white", fontsize=9)

    ax.set_title(title, color="white", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color="#aaaaaa", fontsize=10)
    ax.set_ylabel("Density", color="#aaaaaa", fontsize=10)
    ax.tick_params(colors="#888888")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")

    plt.tight_layout()
    plt.savefig(outputPath, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outputPath}")


def plotCombinedHistograms(
        dataBySimulation: dict,
        title: str,
        xlabel: str,
        outputPath: str,
        colours: list,
):
    """
    Plots overlapping histograms for all simulation types on a single chart.
    Parameters:
        dataBySimulation: Dict mapping simulation name to list of values.
        title: Plot title.
        xlabel: X-axis label.
        outputPath: File path to save the plot.
        colours: List of colours per simulation.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#0f0f0f")
    ax.set_facecolor("#1a1a1a")

    patches = []
    for i, (simName, values) in enumerate(dataBySimulation.items()):
        if not values:
            continue
        colour = colours[i % len(colours)]
        ax.hist(values, bins=12, density=True, color=colour, alpha=0.45,
                edgecolor="#0f0f0f", linewidth=0.5)
        mu, std = np.mean(values), np.std(values)
        if std > 0:
            x = np.linspace(min(values) - std, max(values) + std, 300)
            ax.plot(x, norm.pdf(x, mu, std), color=colour, linewidth=2)
        patches.append(mpatches.Patch(color=colour, label=simName, alpha=0.75))

    ax.legend(handles=patches, facecolor="#2a2a2a", edgecolor="#444",
              labelcolor="white", fontsize=8, loc="upper right")
    ax.set_title(title, color="white", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color="#aaaaaa", fontsize=10)
    ax.set_ylabel("Density", color="#aaaaaa", fontsize=10)
    ax.tick_params(colors="#888888")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")

    plt.tight_layout()
    plt.savefig(outputPath, dpi=150, facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {outputPath}")


def main():
    rawPath = os.path.join(dataDir, "ExperimentRawResults.csv")
    severityPath = os.path.join(dataDir, "ExperimentSeveritySummary.csv")
    recoveryPath = os.path.join(dataDir, "ExperimentRecoverySummary.csv")

    if not os.path.exists(rawPath):
        print(f"ERROR: {rawPath} not found. Run Runner.py first.")
        return

    rawRows = readCsv(rawPath)
    severityRows = readCsv(severityPath)
    recoveryRows = readCsv(recoveryPath)

    simNames = list(dict.fromkeys(row["Simulation"] for row in rawRows))
    colours = ["#4fc3f7", "#ff6b6b", "#69db7c", "#ffd43b", "#cc5de8"]

    severityBySim = {n: [] for n in simNames}
    recoveryBySim = {n: [] for n in simNames}

    for row in rawRows:
        sev = floatOrNone(row["Crash Severity (%)"])
        rec = floatOrNone(row["Recovery Time (Ticks)"])
        if sev is not None:
            severityBySim[row["Simulation"]].append(sev)
        if rec is not None:
            recoveryBySim[row["Simulation"]].append(rec)

    summaryBySim = {}
    for row in severityRows:
        summaryBySim[row["Sim"]] = {
            "meanSev": floatOrNone(row["Mean Crash Severity (%)"]),
            "stdSev": floatOrNone(row["STD Dev Crash Severity"]),
        }
    for row in recoveryRows:
        if row["Sim"] in summaryBySim:
            summaryBySim[row["Sim"]]["meanRec"] = floatOrNone(row["Mean Recovery Time (Ticks)"])
            summaryBySim[row["Sim"]]["stdRec"] = floatOrNone(row["STD Dev Recovery Time"])

    print("\nGenerating per-simulation severity histograms...")
    for i, simName in enumerate(simNames):
        values = severityBySim[simName]
        if not values:
            continue
        stats = summaryBySim.get(simName, {})
        mu = stats.get("meanSev") or np.mean(values)
        std = stats.get("stdSev") or np.std(values)
        plotHistogramWithNormalCurve(
            values=values,
            mean=mu,
            std=std,
            title=f"Crash Severity — {simName}",
            xlabel="Crash Severity (%)",
            colour=colours[i % len(colours)],
            outputPath=os.path.join(plotDir, f"Severity{toPascalCase(simName)}.png"),
        )

    print("\nGenerating per-simulation recovery histograms...")
    for i, simName in enumerate(simNames):
        values = recoveryBySim[simName]
        if not values:
            print(f"  Skipping {simName} — no recovery data")
            continue
        stats = summaryBySim.get(simName, {})
        mu = stats.get("meanRec") or np.mean(values)
        std = stats.get("stdRec") or np.std(values)
        plotHistogramWithNormalCurve(
            values=values,
            mean=mu,
            std=std,
            title=f"Recovery Time — {simName}",
            xlabel="Recovery Time (Ticks)",
            colour=colours[i % len(colours)],
            outputPath=os.path.join(plotDir, f"Recovery{toPascalCase(simName)}.png"),
        )

    print("\nGenerating combined severity histogram...")
    plotCombinedHistograms(
        dataBySimulation=severityBySim,
        title="Crash Severity — All Simulations",
        xlabel="Crash Severity (%)",
        outputPath=os.path.join(plotDir, "SeverityCombined.png"),
        colours=colours,
    )

    print("\nGenerating combined recovery histogram...")
    plotCombinedHistograms(
        dataBySimulation={k: v for k, v in recoveryBySim.items() if v},
        title="Recovery Time — All Simulations",
        xlabel="Recovery Time (Ticks)",
        outputPath=os.path.join(plotDir, "RecoveryCombined.png"),
        colours=colours,
    )

    print(f"\nAll plots saved to: {plotDir}/")


if __name__ == "__main__":
    main()