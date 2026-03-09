# This file is created to have a runner which generates a summary of our results as a CSV.

import csv
import sys
import os

from statistics import mean, median, stdev
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

r = os.path.dirname(os.path.abspath(__file__))
s = os.path.join(r, "src")

if s not in sys.path:

    sys.path.insert(0, s)

from Simulation.model import FlashCrashModel


def runAnalysis( model,
    recoveryAcceptance= 0.85,
    recoveryStandard =10,
    buffer=30,
    recoveryCapTicks=600):
    prices= model.market.priceHistory
    crashEvents = model.crash_events

    if not crashEvents:
        return None


    if crashEvents[0]>= len(prices) or crashEvents[0] <=1 :
        return None

    if not prices[max(0, crashEvents[0] - 10):crashEvents[0]]:
        return None

    c = prices[max(0, crashEvents[0] - 10):crashEvents[0]]
    priceBeforeTheCrash = sum(c)/len(c)
    

    searchEnd = min(len(prices), crashEvents[0] + model.crash_duration + buffer)
    crashSection = prices[crashEvents[0]:searchEnd]

    if not crashSection:
        return None

    bottomPrice = min(crashSection)

    bottomTick = crashEvents[0] + crashSection.index(bottomPrice)

    if bottomPrice >= priceBeforeTheCrash:
        return None

    crashSeverity = ((priceBeforeTheCrash-bottomPrice)/priceBeforeTheCrash) * 100

    recoveryCalc = bottomPrice + recoveryAcceptance* (priceBeforeTheCrash - bottomPrice)

    a = None
    for t in crashEvents[1:]:
        if t> bottomTick:            
            a= t
            break

    if a is None:
        border = len(prices)
    else:
        border = a
 
    border = min(border, bottomTick+recoveryCapTicks)
  

    recoveryT = None

    beginning = bottomTick + 1
    endTick = border- recoveryStandard + 1

    for t in range(beginning, endTick):

        if all(p>= recoveryCalc for p in prices[t:t + recoveryStandard]):
            recoveryT = t - bottomTick
            break

    recovered = int(recoveryT is not None)

    res = {
    "Crash Severity (%)": round(crashSeverity, 2),
    "Recovery Time (Ticks)": recoveryT,
    "Recovered": recovered }

    return res


def runSimulationForCrashes(simulationName, runs =100, steps= 5000, **kwargs):
    rows = []
    seed = 0

    while len(rows)< runs:

        model = FlashCrashModel(seed=seed, **kwargs)

        for t in range(steps):
            model.step()

        evalMetrics = runAnalysis(model)

        if evalMetrics is not None:
            rows.append({
                "Simulation": simulationName,
                "Crash Severity (%)": evalMetrics["Crash Severity (%)"],
                "Recovery Time (Ticks)": evalMetrics["Recovery Time (Ticks)"],
                "Recovered": evalMetrics["Recovered"],})
        seed+= 1
    return rows


def summary(avR):
    rows = []
    simName = sorted(set(row["Simulation"] for row in avR))
    

    for n in simName:
        rows1 = [r for r in avR if r["Simulation"]== n]

        cS = [r["Crash Severity (%)"] for r in rows1 
              if r["Crash Severity (%)"] is not None]

        recoveries = [ r["Recovery Time (Ticks)"] for r in rows1
            if r["Recovery Time (Ticks)"] is not None]

        recoveredR = sum(r["Recovered"] for r in rows1)
        recoveryRate = (recoveredR/len(rows1)) * 100 if len(rows1) > 0 else None

        a = round (mean(cS),2) if cS else None
        b = round (median(cS), 2) if cS else None
        c= round(stdev(cS), 2) if len(cS)> 1 else 0
        d = round(mean(recoveries),2) if recoveries else None
        e = round (median(recoveries), 2) if recoveries else None
        f = round(stdev(recoveries), 2) if len(recoveries) >1 else 0
        g=round(recoveryRate, 2) if recoveryRate is not None else None

        rows.append({
            "Sim": n,
            "Runs": len(rows1),
            "Mean Crash Severity": a,
            "Median Crash Severity": b,
            "STD Dev: Crash": c,
            "Mean Recovery Time": d,
            "Median Recovery Time": e,
            "STD Dev: Recovery":  f,
            "Recovered": recoveredR,
            "Recovery Percentage": g })
    return rows



def simulationRunner():
    def writeCsv(filepath, rows, fieldnames):
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames = fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    simulations = [
        { "name": "Baseline Model",
            "n_market_maker": 15,
            "n_noisy": 7,
            "n_fundamental": 3,
            "n_hft": 0,
            "n_momentum": 0,
            "n_stoploss": 0,
        },
        {"name": "Baseline Model with HFT",
            "n_market_maker": 15,
            "n_noisy": 7,
            "n_fundamental": 3,
            "n_hft": 2,
            "n_momentum": 0,
            "n_stoploss": 0,
        },
        {"name": "Baseline Model with Momentum",
            "n_market_maker": 15,
            "n_noisy": 7,
            "n_fundamental": 3,
            "n_hft": 0,
            "n_momentum": 3,
            "n_stoploss": 0,
        },
        {"name": "Baseline Model with Stop-Loss",
            "n_market_maker": 15,
            "n_noisy": 7,
            "n_fundamental": 3,
            "n_hft": 0,
            "n_momentum": 0,
            "n_stoploss": 3,
        },
        {"name": "Full Market",
            "n_market_maker": 15,
            "n_noisy": 7,
            "n_fundamental": 3,
            "n_hft": 2,
            "n_momentum": 3,
            "n_stoploss": 3,
        },
    ]

    runs = 100 # If you wanna test make this 1
    steps = 5000 # If you wanna test make this 1000

    rows1 = []

    for simulation in simulations:
        simulation = simulation.copy()
        simulationName = simulation.pop("name")

        rows = runSimulationForCrashes(
            simulationName =simulationName,
            runs=runs,
            steps=steps,
            **simulation
        )
        rows1.extend(rows)

    colNames = ["Sim","Runs", "Mean Crash Severity", "Median Crash Severity",
    "STD Dev: Crash","Mean Recovery Time","Median Recovery Time","STD Dev: Recovery",
    "Recovered","Recovery Percentage",]

    writeCsv(os.path.join(r, "experiment_results_summary.csv"), summary(rows1), colNames)
    for i in summary(rows1):
        print(i)

if __name__ == "__main__":
    simulationRunner()
