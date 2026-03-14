import matplotlib
import solara

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import asyncio

from Simulation.Mesa.FlashCrashModel import FlashCrashModel

modelState = solara.reactive(None)
running = solara.reactive(False)
stepCount = solara.reactive(0)
marketMakerCount = solara.reactive(25)
noisyCount = solara.reactive(60)
fundamentalCount = solara.reactive(200)
highFrequencyCount = solara.reactive(15)
momentumCount = solara.reactive(90)
stopLossCount = solara.reactive(40)
fundamentalVolatilityAmount = solara.reactive(0.05)
marketMakerSpreadAmount = solara.reactive(0.2)
crashProbabilityAmount = solara.reactive(0.002)


def makeModel():
    return FlashCrashModel(
        numberOfMarketMakerAgents=marketMakerCount.value,
        numberOfNoisyAgents=noisyCount.value,
        numberOfFundamentalAgents=fundamentalCount.value,
        numberOfHighFrequencyAgents=highFrequencyCount.value,
        numberOfMomentumAgents=momentumCount.value,
        numberOfStopLossAgents=stopLossCount.value,
        fundamentalVolatility=fundamentalVolatilityAmount.value,
        marketMakerSpread=marketMakerSpreadAmount.value,
        crashProbability=crashProbabilityAmount.value,
        marketMakerStepProbability=0.9,
        noisyStepProbability=0.5,
        fundamentalStepProbability=0.02,
        highFrequencyStepProbability=1.0,
        momentumStepProbability=0.33,
        stopLossStepProbability=0.5
    )


bg = "#0f1117"
surface = "#1a1f2e"
surfaceAlt = "#222840"
border = "#2e3550"
text = "#f0f4ff"
muted = "#c8d0e8"  # brighter muted — more readable on dark bg
accent = "#4f9eff"
bidColor = "#34c97a"
askColor = "#f05c5c"
priceColor = "#4f9eff"
fundColor = "#ffb347"
spreadColor = "#b07fff"
tradeColor = "#2edfa3"
crashColor = "#ff6b6b"
cooldownColor = "#c0614a"  # distinct muted red for cooldown state
volumeColor = "#f0c040"
gridColor = "#ffffff"  # white grid lines
tickColor = "#e0e6f5"  # near-white tick labels

WINDOW = 500

css = f"""
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    background: {bg};
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 11px;
    color: {text};
    overflow: hidden;
    height: 100vh;
}}

/* Kill any Vuetify white surfaces */
.v-application,
.v-application--wrap,
.v-main,
.v-main__wrap,
.v-sheet,
.theme--light.v-application {{
    background: {bg} !important;
    background-color: {bg} !important;
    color: {text} !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}}

html, body, #app, #app > div, .v-application > div {{
    background: {bg} !important;
    background-color: {bg} !important;
}}

.v-card, .v-list, .v-toolbar {{
    background: {surface} !important;
    color: {text} !important;
}}

.v-application--wrap > div,
.v-main__wrap > div,
.v-main__wrap > div > div {{
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
}}

.v-application--wrap > div > .col,
.v-application--wrap > .col {{
    padding: 0 !important;
    gap: 0 !important;
}}

.row {{ margin: 0 !important; }}
.col  {{ padding: 0 !important; }}

/* ── Header ── */
.dash-header {{
    background: {surface} !important;
    border-bottom: 1px solid {border};
    padding: 0 20px !important;
    height: 48px !important;
    min-height: 48px !important;
    max-height: 48px !important;
    align-items: center !important;
    gap: 20px !important;
    flex-shrink: 0 !important;
    flex-wrap: nowrap !important;
    overflow: hidden;
}}

.header-title {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    color: {text} !important;
    letter-spacing: 0.06em;
    white-space: nowrap;
}}

.header-badge {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    color: {accent} !important;
    background: rgba(79,158,255,0.12) !important;
    border: 1px solid rgba(79,158,255,0.3) !important;
    border-radius: 3px;
    padding: 2px 8px !important;
    white-space: nowrap;
}}

.stat-block {{
    display: flex !important;
    flex-direction: column !important;
    gap: 1px !important;
    border-left: 1px solid {border} !important;
    padding-left: 14px !important;
    flex-shrink: 0;
    background: {surface} !important;
}}

.stat-label {{
    font-size: 9px !important;
    color: {muted} !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 500 !important;
    background: {surface} !important;
}}

.stat-value {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    color: {text} !important;
    background: {surface} !important;
}}

/* ── Sidebar ── */
.dash-sidebar {{
    width: 240px !important;
    min-width: 240px !important;
    max-width: 240px !important;
    flex-shrink: 0 !important;
    background: {surface} !important;
    border-right: 1px solid {border} !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 12px 10px !important;
    height: calc(100vh - 48px) !important;
    align-items: stretch !important;
    gap: 4px !important;
}}

.dash-sidebar::-webkit-scrollbar {{ width: 3px; }}
.dash-sidebar::-webkit-scrollbar-thumb {{ background: {border}; border-radius: 2px; }}

.dash-sidebar .v-label,
.dash-sidebar label,
.dash-sidebar .v-input__slot label {{
    color: {text} !important;
    font-size: 10px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}}

.dash-sidebar .v-slider__thumb,
.dash-sidebar .v-slider__track-fill {{ background-color: {accent} !important; }}

.sidebar-section {{
    font-size: 9px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: {accent} !important;
    padding: 10px 2px 3px !important;
    border-top: 1px solid {border} !important;
    margin-top: 4px !important;
}}

/* ── Buttons ── */
.btn {{
    background: {surface} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 4px !important;
    padding: 4px 10px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
}}

.btn-step {{
    background: {surface} !important;
    color: {text} !important;
    border: 1px solid {border} !important;
    border-radius: 4px !important;
    flex: 1 !important;
    min-width: 0 !important;
    padding: 5px 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    text-align: center !important;
}}

.btn-step-row {{
    display: flex !important;
    flex-direction: row !important;
    gap: 4px !important;
    width: 100% !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
}}

.btn-primary {{
    background: {accent} !important;
    color: #0a0e1a !important;
    border: none !important;
    border-radius: 4px !important;
    width: 100% !important;
    padding: 7px 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 700 !important;
}}

/* Active crash — bright red */
.btn-danger,
.btn-danger.v-btn,
.v-btn.btn-danger {{
    background: #5c1a1a !important;
    background-color: #5c1a1a !important;
    color: {askColor} !important;
    border: 1px solid #c03030 !important;
    border-radius: 4px !important;
    width: 100% !important;
    padding: 5px 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
}}

.btn-danger .v-btn__content,
.v-btn.btn-danger .v-btn__content {{ color: {askColor} !important; background: transparent !important; }}
.btn-danger::before, .v-btn.btn-danger::before {{ background: transparent !important; opacity: 0 !important; }}

/* Cooldown state — muted earthy red, visually distinct */
.btn-cooldown,
.btn-cooldown.v-btn,
.btn-cooldown .v-btn,
.v-btn.btn-cooldown {{
    background: #5a2a20 !important;
    background-color: #5a2a20 !important;
    color: #e8957a !important;
    border: 1px solid #a04030 !important;
    border-radius: 4px !important;
    width: 100% !important;
    padding: 5px 0 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 600 !important;
}}

.btn-cooldown .v-btn__content,
.v-btn.btn-cooldown .v-btn__content {{
    color: #e8957a !important;
    background: transparent !important;
}}

/* Also override the before/after pseudo overlays Vuetify uses */
.btn-cooldown::before,
.v-btn.btn-cooldown::before {{
    background: transparent !important;
    opacity: 0 !important;
}}

/* ── Chart area rows/cols ── */
.chart-col {{
    flex: 1 !important;
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    height: calc(100vh - 48px) !important;
    overflow: hidden !important;
}}

.chart-row {{
    flex: 1 !important;
    min-height: 0 !important;
    display: flex !important;
    overflow: hidden !important;
    border-bottom: 1px solid {border} !important;
}}

.chart-row:last-child {{ border-bottom: none !important; }}

.chart-cell {{
    flex: 1 !important;
    min-width: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
    border-right: 1px solid {border} !important;
}}

.chart-cell:last-child {{ border-right: none !important; }}

.chart-cell .v-responsive,
.chart-cell canvas,
.chart-cell img,
.chart-cell .v-image__image {{
    width: 100% !important;
    height: 100% !important;
    object-fit: fill !important;
    display: block !important;
}}

.chart-cell > div,
.chart-cell > div > div {{
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    flex: 1 !important;
}}
"""


def getDataFrame(model):
    dataCollection = model.dataCollector.model_vars
    minLength = None
    for value in dataCollection.values():
        if minLength is None or len(value) < minLength:
            minLength = len(value)
    safe = {key: value[:minLength] for key, value in dataCollection.items()}
    return pd.DataFrame(safe)


def styleAx(ax, title=""):
    ax.set_facecolor(bg)
    ax.tick_params(colors=tickColor, labelsize=7)
    ax.xaxis.label.set_color(tickColor)
    ax.yaxis.label.set_color(tickColor)
    for sp in ax.spines.values():
        sp.set_edgecolor("#4a5270")  # slightly lighter spine for contrast
    ax.grid(True, color=gridColor, linewidth=0.3, alpha=0.18)
    if title:
        ax.set_title(title, color=tickColor, fontsize=8, fontweight="600", pad=5,
                     loc="left", fontfamily="monospace")


def addLegend(ax):
    leg = ax.legend(facecolor=surface, edgecolor=border, fontsize=6.5,
                    framealpha=0.9)
    for txt in leg.get_texts():
        txt.set_color(tickColor)


def addCrashLines(ax, model):
    for t in model.crashEvents:
        ax.axvline(t, color=crashColor, linewidth=1.2, alpha=0.6, linestyle=":")


def addCrashRegions(ax, model, df):
    if len(df.index) > WINDOW:
        xMin, xMax = df.index[-WINDOW], df.index[-1]
    else:
        xMin, xMax = df.index[0], df.index[-1]

    # Completed crashes
    for start, end in model.crashWindows:
        clampedStart = max(xMin, start)
        clampedEnd = min(xMax, end)
        if clampedStart < clampedEnd:
            ax.axvspan(clampedStart, clampedEnd, color=crashColor, alpha=0.15, zorder=0)

    # Currently active crash
    if model.activeCrashTicks > 0 and model.currentCrashStart is not None:
        clampedStart = max(xMin, model.currentCrashStart)
        clampedEnd = xMax
        if clampedStart <= clampedEnd:
            ax.axvspan(clampedStart, clampedEnd, color=crashColor, alpha=0.20, zorder=0)


def makeFig(wide=False):
    w = 9.0 if wide else 6.0
    fig, ax = plt.subplots(figsize=(w, 2.8), facecolor=bg)
    fig.patch.set_facecolor(bg)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.87, bottom=0.20)
    return fig, ax


def renderPriceChart(model):
    df = getDataFrame(model)
    fig, ax = makeFig(wide=True)
    styleAx(ax, "PRICE  /  FUNDAMENTAL")
    if "MidPrice" in df.columns and df["MidPrice"].dropna().any():
        midPrice = pd.to_numeric(df["MidPrice"], errors="coerce").ffill()
        ax.plot(df.index, midPrice, color=priceColor, linewidth=1.4, label="Mid Price")
    if "Fundamental" in df.columns:
        ax.plot(df.index, df["Fundamental"], color=fundColor, linewidth=1.1,
                linestyle="--", alpha=0.85, label="Fundamental")
    addCrashLines(ax, model)
    addCrashRegions(ax, model, df)
    if model.crashEvents:
        ax.axvline(model.crashEvents[-1], color=crashColor, linewidth=1.4, alpha=0.8,
                   linestyle=":", label="Crash")
    if len(df.index) > WINDOW:
        ax.set_xlim(df.index[-WINDOW], df.index[-1])
    ax.set_ylabel("Price", color=tickColor, fontsize=7)
    addLegend(ax)
    return fig


def renderSpreadChart(model):
    df = getDataFrame(model)
    fig, ax = makeFig(wide=True)
    styleAx(ax, "BID-ASK  SPREAD")
    if "Spread" in df.columns:
        spreadVals = pd.to_numeric(df["Spread"], errors="coerce").ffill().fillna(0)
        ax.fill_between(df.index, spreadVals, color=spreadColor, alpha=0.3)
        ax.plot(df.index, spreadVals, color=spreadColor, linewidth=1.2)
        addCrashLines(ax, model)
        addCrashRegions(ax, model, df)
        if len(df.index) > WINDOW:
            ax.set_xlim(df.index[-WINDOW], df.index[-1])
    ax.set_ylabel("Spread", color=tickColor, fontsize=7)
    return fig


def renderVolumeChart(model, ma_window=20):
    df = getDataFrame(model)
    fig, ax = makeFig(wide=True)
    styleAx(ax, "TRADE  VOLUME")
    if "TradeCount" in df.columns:
        trades = pd.to_numeric(df["TradeCount"], errors="coerce").fillna(0)
        volume = trades.diff().fillna(trades).clip(lower=0)
        ax.bar(df.index, volume, color=volumeColor, width=0.8, alpha=0.6, align="center")
        ma = volume.rolling(window=ma_window, min_periods=1).mean()
        ax.plot(df.index, ma, color=priceColor, linewidth=1.2, linestyle="--",
                label=f"{ma_window}-step MA")
        addCrashLines(ax, model)
        addCrashRegions(ax, model, df)
        if len(df.index) > WINDOW:
            ax.set_xlim(df.index[-WINDOW], df.index[-1])
        addLegend(ax)
    ax.set_ylabel("Trades", color=tickColor, fontsize=7)
    ax.set_xlabel("Step", color=tickColor, fontsize=7)
    return fig


def renderDepthChart(model):
    fig, ax = makeFig(wide=False)
    styleAx(ax, "CUMULATIVE  BOOK  DEPTH")
    bids, asks = model.getOrderBookSnapshot(levels=20)
    if bids:
        bidPrices = sorted([d["price"] for d in bids])
        bidQtys = [next(d["qty"] for d in bids if d["price"] == p) for p in bidPrices]
        bidCum = np.cumsum(bidQtys[::-1])[::-1]
        ax.fill_between(bidPrices, bidCum, color=bidColor, alpha=0.4, step="post")
        ax.plot(bidPrices, bidCum, color=bidColor, linewidth=1.2, drawstyle="steps-post")
    if asks:
        askPrices = sorted([d["price"] for d in asks])
        askQtys = [next(d["qty"] for d in asks if d["price"] == p) for p in askPrices]
        askCum = np.cumsum(askQtys)
        ax.fill_between(askPrices, askCum, color=askColor, alpha=0.4, step="post")
        ax.plot(askPrices, askCum, color=askColor, linewidth=1.2, drawstyle="steps-post")
    ax.set_ylabel("Cum. Qty", color=tickColor, fontsize=7)
    leg = ax.legend(handles=[mpatches.Patch(color=bidColor, label="Bids", alpha=0.7),
                             mpatches.Patch(color=askColor, label="Asks", alpha=0.7)],
                    facecolor=surface, edgecolor=border, fontsize=6.5)
    for txt in leg.get_texts():
        txt.set_color(tickColor)
    return fig


def renderOrderBook(model):
    fig, ax = makeFig(wide=False)
    styleAx(ax, "LIVE  ORDER  BOOK")
    bids, asks = model.getOrderBookSnapshot(levels=10)
    if bids:
        ax.barh([d["price"] for d in bids], [d["qty"] for d in bids],
                color=bidColor, alpha=0.7, height=0.012, label="Bids")
    if asks:
        ax.barh([d["price"] for d in asks], [d["qty"] for d in asks],
                color=askColor, alpha=0.7, height=0.012, label="Asks")
    mid = model.limitOrderBook.midPrice()
    if mid:
        ax.axhline(mid, color=priceColor, linewidth=1.2, linestyle="--",
                   alpha=0.8, label=f"Mid {mid:.2f}")
    ax.set_xlabel("Qty", color=tickColor, fontsize=7)
    ax.set_ylabel("Price", color=tickColor, fontsize=7)
    addLegend(ax)
    return fig


def renderAgentActivity(model):
    fig, ax = makeFig(wide=False)
    ax.set_facecolor(bg)
    fig.patch.set_facecolor(bg)
    ax.set_title("AGENT  COMPOSITION", color=tickColor, fontsize=8, fontweight="600",
                 pad=5, loc="left", fontfamily="monospace")
    counts = [len(model.marketMakers), len(model.fundamental), len(model.noisy),
              len(model.highFrequency), len(model.momentum), len(model.stopLoss)]
    labels = ["Mkt Maker", "Fundamental", "Noisy", "HFT", "Momentum", "Stop Loss"]
    colors = [bidColor, fundColor, priceColor, tradeColor, "#a8dadc", "#e9c46a"]
    nz = [(c, l, col) for c, l, col in zip(counts, labels, colors) if c > 0]
    if nz:
        c_, l_, col_ = zip(*nz)
        wedges, texts, autotexts = ax.pie(
            c_, labels=l_, colors=col_, autopct="%1.0f%%",
            textprops={"color": tickColor, "fontsize": 7},
            wedgeprops={"edgecolor": bg, "linewidth": 1.5},
            startangle=90
        )
        for t in texts + autotexts:
            t.set_color(tickColor)
            t.set_fontsize(7)
    return fig


@solara.component
def Sidebar():
    model = modelState.value

    def advance(n):
        if model:
            for _ in range(n):
                model.step()
            modelState.set(modelState.value)
            stepCount.set(stepCount.value + n)

    with solara.Column(classes=["dash-sidebar"]):
        solara.Text("CONTROLS", classes=["sidebar-section"])

        with solara.Row(classes=["btn-step-row"]):
            solara.Button("RESET", classes=["btn-step"], on_click=lambda: [
                modelState.set(makeModel()), stepCount.set(0), running.set(False)
            ])
            solara.Button("+10", classes=["btn-step"], on_click=lambda: advance(10))
            solara.Button("+50", classes=["btn-step"], on_click=lambda: advance(50))
            solara.Button("+200", classes=["btn-step"], on_click=lambda: advance(200))

        solara.Button(
            "RUN" if not running.value else "PAUSE",
            classes=["btn-primary"],
            on_click=lambda: running.set(not running.value)
        )

        _ = stepCount.value
        if model:
            isCrashActive = model.activeCrashTicks > 0
            isCooldown = model.crashCooldown > 0
            canTrigger = not isCrashActive and not isCooldown

            if isCrashActive:
                label = f"CRASH ACTIVE ({model.activeCrashTicks})"
                btnClass = "btn-danger"  # bright red
            elif isCooldown:
                label = f"COOLDOWN: {model.crashCooldown}"
                btnClass = "btn-cooldown"  # muted earthy red — distinct from active
            else:
                label = "TRIGGER FLASH CRASH"
                btnClass = "btn-danger"

            def triggerCrash():
                if canTrigger:
                    model.triggerManualCrash()
                    stepCount.set(stepCount.value)

            solara.Button(label, classes=[btnClass], disabled=not canTrigger, on_click=triggerCrash)

        solara.SliderFloat("Crash Probability", value=crashProbabilityAmount, min=0.0, max=0.02, step=0.001)

        solara.Text("AGENTS", classes=["sidebar-section"])
        solara.SliderInt("Market Makers", value=marketMakerCount, min=0, max=200)
        solara.SliderInt("Noisy Agents", value=noisyCount, min=0, max=200)
        solara.SliderInt("Fundamental", value=fundamentalCount, min=0, max=200)
        solara.SliderInt("HFT Agents", value=highFrequencyCount, min=0, max=200)
        solara.SliderInt("Momentum", value=momentumCount, min=0, max=200)
        solara.SliderInt("Stop Loss", value=stopLossCount, min=0, max=200)

        solara.Text("MARKET", classes=["sidebar-section"])
        solara.SliderFloat("Fundamental Vol", value=fundamentalVolatilityAmount, min=0.01, max=2.0, step=0.01)
        solara.SliderFloat("MM Spread", value=marketMakerSpreadAmount, min=0.1, max=3.0, step=0.05)


CELL_LEFT = {
    "flex": "1.5",
    "minWidth": "0",
    "minHeight": "0",
    "overflow": "hidden",
    "background": bg,
}

CELL_RIGHT = {
    "flex": "1",
    "minWidth": "0",
    "minHeight": "0",
    "overflow": "hidden",
    "background": bg,
}

ROW_STYLE = {
    "flex": "1",
    "minHeight": "0",
    "overflow": "hidden",
    "borderBottom": f"1px solid {border}",
    "alignItems": "stretch",
    "gap": "0",
}

ROW_LAST_STYLE = {**ROW_STYLE, "borderBottom": "none"}

DIVIDER = {"borderRight": f"1px solid {border}"}


@solara.component
def ChartGrid():
    model = modelState.value
    if not model:
        solara.Text("Initialising…", style={"color": muted, "padding": "20px"})
        return

    _ = stepCount.value

    with solara.Column(style={
        "flex": "1",
        "minWidth": "0",
        "height": "calc(100vh - 48px)",
        "overflow": "hidden",
        "gap": "0",
        "alignItems": "stretch",
    }):
        with solara.Row(style=ROW_STYLE):
            with solara.Column(style={**CELL_LEFT, **DIVIDER}):
                solara.FigureMatplotlib(renderPriceChart(model))
            with solara.Column(style=CELL_RIGHT):
                solara.FigureMatplotlib(renderDepthChart(model))

        with solara.Row(style=ROW_STYLE):
            with solara.Column(style={**CELL_LEFT, **DIVIDER}):
                solara.FigureMatplotlib(renderSpreadChart(model))
            with solara.Column(style=CELL_RIGHT):
                solara.FigureMatplotlib(renderOrderBook(model))

        with solara.Row(style=ROW_LAST_STYLE):
            with solara.Column(style={**CELL_LEFT, **DIVIDER}):
                solara.FigureMatplotlib(renderVolumeChart(model))
            with solara.Column(style=CELL_RIGHT):
                solara.FigureMatplotlib(renderAgentActivity(model))


@solara.component
def page():
    solara.Style(css)

    if modelState.value is None:
        modelState.set(makeModel())

    async def autoStepper():
        while True:
            await asyncio.sleep(0.3)
            if running.value and modelState.value:
                modelState.value.step()
                stepCount.set(stepCount.value + 1)

    solara.lab.use_task(autoStepper, dependencies=[])

    with solara.Column(style={
        "height": "100vh",
        "overflow": "hidden",
        "gap": "0",
        "padding": "0",
        "margin": "0",
    }):
        with solara.Row(classes=["dash-header"]):
            _ = stepCount.value
            solara.Text("FLASH CRASH ABM", classes=["header-title"])
            solara.Text("MESA + SOLARA", classes=["header-badge"])

            model = modelState.value
            if model:
                midPrice = model.limitOrderBook.midPrice()
                spread = model.limitOrderBook.spread()
                stats = [
                    ("MID PRICE", f"{midPrice:.2f}" if midPrice else "—"),
                    ("FUNDAMENTAL", f"{float(model.market.fundamentalPrice):.2f}"),
                    ("SPREAD", f"{spread:.4f}" if spread else "—"),
                    ("TRADES", str(len(model.limitOrderBook.trades))),
                    ("BID DEPTH", str(model.limitOrderBook.depth("buy", 10))),
                    ("ASK DEPTH", str(model.limitOrderBook.depth("sell", 10))),
                    ("CRASHES", str(len(model.crashEvents))),
                    ("STEP", str(stepCount.value)),
                ]
                for lbl, val in stats:
                    with solara.Column(classes=["stat-block"]):
                        solara.Text(lbl, classes=["stat-label"])
                        solara.Text(val, classes=["stat-value"])

        with solara.Row(style={
            "flex": "1",
            "minHeight": "0",
            "overflow": "hidden",
            "gap": "0",
            "alignItems": "stretch",
            "flexWrap": "nowrap",
        }):
            Sidebar()
            ChartGrid()
