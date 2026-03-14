import csv
import sys
import os
import multiprocessing
from statistics import mean, median, stdev
from typing import Optional
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

r = os.path.dirname(os.path.abspath(__file__))
s = os.path.join(r, "src")

if s not in sys.path:
    sys.path.insert(0, s)

from src.Simulation.Mesa.FlashCrashModel import FlashCrashModel


def _workerInit():
    sys.stderr = open(os.devnull, "w")
    warnings.filterwarnings("ignore")


def runAnalysis(
        model,
        recoveryAcceptance: float = 0.85,
        recoveryStandard: int = 10,
        buffer: int = 30,
        recoveryCapTicks: int = 700,
) -> Optional[dict]:
    prices = model.market.priceHistory
    crashEvents = model.crashEvents

    if not crashEvents:
        return None
    if crashEvents[0] >= len(prices) or crashEvents[0] <= 1:
        return None

    preCrashSlice = prices[max(0, crashEvents[0] - 10):crashEvents[0]]
    if not preCrashSlice:
        return None
    priceBeforeTheCrash = sum(preCrashSlice) / len(preCrashSlice)

    searchEnd = min(len(prices), crashEvents[0] + model.crashDuration + buffer)
    crashSection = prices[crashEvents[0]:searchEnd]
    if not crashSection:
        return None

    bottomPrice = min(crashSection)
    bottomTick = crashEvents[0] + crashSection.index(bottomPrice)

    if bottomPrice >= priceBeforeTheCrash:
        return None

    crashSeverity = ((priceBeforeTheCrash - bottomPrice) / priceBeforeTheCrash) * 100
    recoveryCalc = bottomPrice + recoveryAcceptance * (priceBeforeTheCrash - bottomPrice)

    nextCrash = next((t for t in crashEvents[1:] if t > bottomTick), None)
    border = min(nextCrash if nextCrash is not None else len(prices), bottomTick + recoveryCapTicks)

    recoveryT = None
    for t in range(bottomTick + 1, border - recoveryStandard + 1):
        if all(p >= recoveryCalc for p in prices[t:t + recoveryStandard]):
            recoveryT = t - bottomTick
            break

    return {
        "Crash Severity (%)": round(crashSeverity, 2),
        "Recovery Time (Ticks)": recoveryT,
        "Recovered": int(recoveryT is not None),
    }


def _runSingleSeed(args: tuple) -> Optional[dict]:
    """
    Runs one simulation for a given seed and returns the analysis result, or None if no
    valid crash was recorded. A single crash is triggered deterministically at crashAtTick
    rather than stochastically. Designed to be called by a worker process via multiprocessing.
    Parameters:
        args: Tuple of (simulationName, seed, steps, kwargs, crashAtTick) for the simulation run.
    """
    simulationName, seed, steps, kwargs, crashAtTick = args
    model = FlashCrashModel(seed=seed, **kwargs)
    for t in range(steps):
        model.step()
        if t == crashAtTick and model.limitOrderBook.bestBid() is not None:
            model.triggerManualCrash()
    result = runAnalysis(model)
    if result is None:
        return None
    return {
        "Simulation": simulationName,
        "Seed": seed,
        "Crash Severity (%)": result["Crash Severity (%)"],
        "Recovery Time (Ticks)": result["Recovery Time (Ticks)"],
        "Recovered": result["Recovered"],
    }


def runSimulationForCrashes(
        simulationName: str,
        pool: multiprocessing.Pool,
        runs: int = 100,
        steps: int = 750,
        crashAtTick: int = 250,
        **kwargs
) -> list:
    """
    Runs repeated simulations in parallel until the required number of valid crash observations
    is collected. Uses apply_async with a callback queue to keep exactly cpuCount * 2 tasks in
    flight at all times, submitting one new task the moment any worker finishes to eliminate
    burst and drain cycles. Random crashes are disabled and a single crash is triggered
    deterministically at crashAtTick instead. Pass and fail results are logged to stdout.
    Parameters:
        simulationName: Label for this simulation configuration.
        pool: Shared multiprocessing Pool to submit tasks to.
        runs: Number of valid crash observations required.
        steps: Number of ticks to simulate per run.
        crashAtTick: The tick at which to trigger a manual flash crash.
    """
    cpuCount = max(1, multiprocessing.cpu_count())
    kwargs["crashProbability"] = 0.0
    rows = []
    seed = 0
    inFlight = 0
    resultQueue = multiprocessing.Queue()

    def onResult(result):
        resultQueue.put(result)

    def submit():
        nonlocal seed, inFlight
        pool.apply_async(
            _runSingleSeed,
            args=((simulationName, seed, steps, kwargs, crashAtTick),),
            callback=onResult,
        )
        seed += 1
        inFlight += 1

    for _ in range(cpuCount * 2):
        submit()

    while len(rows) < runs:
        result = resultQueue.get()
        inFlight -= 1
        if result is not None:
            rows.append(result)
            print(f"[{simulationName}] Seed {seed - inFlight - 1} PASSED — valid so far: {len(rows)}/{runs}")
        else:
            print(f"[{simulationName}] Seed {seed - inFlight - 1} FAILED")
        if len(rows) < runs:
            submit()

    return rows[:runs]


def summary(avR: list) -> tuple:
    """
    Aggregates raw simulation rows into two separate per-simulation summary tables:
    one for crash severity statistics and one for recovery time statistics.
    Parameters:
        avR: List of raw result rows from runSimulationForCrashes.
    Returns a tuple of (severityRows, recoveryRows).
    """
    severityRows = []
    recoveryRows = []
    simNames = list(dict.fromkeys(row["Simulation"] for row in avR))

    for n in simNames:
        simRows = [row for row in avR if row["Simulation"] == n]
        crashSeverities = [row["Crash Severity (%)"] for row in simRows if row["Crash Severity (%)"] is not None]
        recoveryTimes = [row["Recovery Time (Ticks)"] for row in simRows if row["Recovery Time (Ticks)"] is not None]
        recoveredCount = sum(row["Recovered"] for row in simRows)
        recoveryRate = (recoveredCount / len(simRows)) * 100 if simRows else None

        severityRows.append({
            "Sim": n,
            "Runs": len(simRows),
            "Mean Crash Severity (%)": round(mean(crashSeverities), 2) if crashSeverities else None,
            "Median Crash Severity (%)": round(median(crashSeverities), 2) if crashSeverities else None,
            "STD Dev Crash Severity": round(stdev(crashSeverities), 2) if len(crashSeverities) > 1 else 0,
            "Min Crash Severity (%)": round(min(crashSeverities), 2) if crashSeverities else None,
            "Max Crash Severity (%)": round(max(crashSeverities), 2) if crashSeverities else None,
        })

        recoveryRows.append({
            "Sim": n,
            "Runs": len(simRows),
            "Recovered": recoveredCount,
            "Recovery Percentage": round(recoveryRate, 2) if recoveryRate is not None else None,
            "Mean Recovery Time (Ticks)": round(mean(recoveryTimes), 2) if recoveryTimes else None,
            "Median Recovery Time (Ticks)": round(median(recoveryTimes), 2) if recoveryTimes else None,
            "STD Dev Recovery Time": round(stdev(recoveryTimes), 2) if len(recoveryTimes) > 1 else 0,
            "Min Recovery Time (Ticks)": round(min(recoveryTimes), 2) if recoveryTimes else None,
            "Max Recovery Time (Ticks)": round(max(recoveryTimes), 2) if recoveryTimes else None,
        })

    return severityRows, recoveryRows


def simulationRunner():
    """
    Defines the simulation configurations, runs all experiments in parallel using a single
    shared process pool, and writes three CSV files to the project root:
    - experiment_raw_results.csv: one row per valid simulation run
    - experiment_severity_summary.csv: per-simulation crash severity statistics
    - experiment_recovery_summary.csv: per-simulation recovery time statistics
    """
    def writeCsv(filepath, rows, fieldnames):
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    simulations = [
        {
            "name": "Baseline Model",
            "numberOfMarketMakerAgents": 15,
            "numberOfNoisyAgents": 150,
            "numberOfFundamentalAgents": 200,
            "numberOfHighFrequencyAgents": 0,
            "numberOfMomentumAgents": 0,
            "numberOfStopLossAgents": 0,
            "fundamentalVolatility": 0.05,
            "marketMakerStepProbability": 0.9,
            "noisyStepProbability": 0.05,
            "fundamentalStepProbability": 0.015,
            "highFrequencyStepProbability": 1.0,
            "momentumStepProbability": 0.033,
            "stopLossStepProbability": 0.017,
            "collectData": False,
        },
        {
            "name": "Baseline Model with HFT",
            "numberOfMarketMakerAgents": 15,
            "numberOfNoisyAgents": 150,
            "numberOfFundamentalAgents": 200,
            "numberOfHighFrequencyAgents": 8,
            "numberOfMomentumAgents": 0,
            "numberOfStopLossAgents": 0,
            "fundamentalVolatility": 0.05,
            "marketMakerStepProbability": 0.9,
            "noisyStepProbability": 0.05,
            "fundamentalStepProbability": 0.015,
            "highFrequencyStepProbability": 1.0,
            "momentumStepProbability": 0.033,
            "stopLossStepProbability": 0.017,
            "collectData": False,
        },
        {
            "name": "Baseline Model with Momentum",
            "numberOfMarketMakerAgents": 15,
            "numberOfNoisyAgents": 150,
            "numberOfFundamentalAgents": 200,
            "numberOfHighFrequencyAgents": 0,
            "numberOfMomentumAgents": 100,
            "numberOfStopLossAgents": 0,
            "fundamentalVolatility": 0.05,
            "marketMakerStepProbability": 0.9,
            "noisyStepProbability": 0.05,
            "fundamentalStepProbability": 0.015,
            "highFrequencyStepProbability": 1.0,
            "momentumStepProbability": 0.033,
            "stopLossStepProbability": 0.017,
            "collectData": False,
        },
        {
            "name": "Baseline Model With Stop Loss",
            "numberOfMarketMakerAgents": 15,
            "numberOfNoisyAgents": 150,
            "numberOfFundamentalAgents": 200,
            "numberOfHighFrequencyAgents": 0,
            "numberOfMomentumAgents": 0,
            "numberOfStopLossAgents": 30,
            "fundamentalVolatility": 0.05,
            "marketMakerStepProbability": 0.9,
            "noisyStepProbability": 0.05,
            "fundamentalStepProbability": 0.015,
            "highFrequencyStepProbability": 1.0,
            "momentumStepProbability": 0.033,
            "stopLossStepProbability": 0.017,
            "collectData": False,
        },
        {
            "name": "Full Market",
            "numberOfMarketMakerAgents": 15,
            "numberOfNoisyAgents": 150,
            "numberOfFundamentalAgents": 200,
            "numberOfHighFrequencyAgents": 8,
            "numberOfMomentumAgents": 100,
            "numberOfStopLossAgents": 30,
            "fundamentalVolatility": 0.05,
            "marketMakerStepProbability": 0.9,
            "noisyStepProbability": 0.05,
            "fundamentalStepProbability": 0.015,
            "highFrequencyStepProbability": 1.0,
            "momentumStepProbability": 0.033,
            "stopLossStepProbability": 0.017,
            "collectData": False,
        },
    ]

    runs = 100
    steps = 1000
    crashAtTick = 250

    severityColNames = [
        "Sim", "Runs",
        "Mean Crash Severity (%)", "Median Crash Severity (%)",
        "STD Dev Crash Severity", "Min Crash Severity (%)", "Max Crash Severity (%)",
    ]
    recoveryColNames = [
        "Sim", "Runs", "Recovered", "Recovery Percentage",
        "Mean Recovery Time (Ticks)", "Median Recovery Time (Ticks)",
        "STD Dev Recovery Time", "Min Recovery Time (Ticks)", "Max Recovery Time (Ticks)",
    ]
    rawColNames = ["Simulation", "Seed", "Crash Severity (%)", "Recovery Time (Ticks)", "Recovered"]

    allRows = []
    cpuCount = max(1, multiprocessing.cpu_count())

    with multiprocessing.Pool(processes=cpuCount, initializer=_workerInit) as pool:
        for simulation in simulations:
            simulation = simulation.copy()
            simulationName = simulation.pop("name")
            print(f"Running: {simulationName}")
            rows = runSimulationForCrashes(
                simulationName=simulationName,
                pool=pool,
                runs=runs,
                steps=steps,
                crashAtTick=crashAtTick,
                **simulation,
            )
            allRows.extend(rows)
            print(f"  Completed {len(rows)} valid runs")

    severityRows, recoveryRows = summary(allRows)

    dataDir = os.path.join(r, "Data")
    os.makedirs(dataDir, exist_ok=True)

    writeCsv(os.path.join(dataDir, "ExperimentRawResults.csv"), allRows, rawColNames)
    writeCsv(os.path.join(dataDir, "ExperimentSeveritySummary.csv"), severityRows, severityColNames)
    writeCsv(os.path.join(dataDir, "ExperimentRecoverySummary.csv"), recoveryRows, recoveryColNames)

    print("\n--- Severity Summary ---")
    for i in severityRows:
        print(i)
    print("\n--- Recovery Summary ---")
    for i in recoveryRows:
        print(i)


if __name__ == "__main__":
    simulationRunner()