import asyncio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import solara

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
fundamentalVolatility = solara.reactive(0.05)
crashProbability = solara.reactive(0.002)

WINDOW = 750
COLOURS = dict(
    bg="#f5f6fa", surface="#ffffff", surfaceAlt="#eef0f7", border="#d8dce8",
    text="#000000", accent="#1a6fdb", bid="#1a9e5c", ask="#d93535",
    price="#1a6fdb", fund="#c97b00", spread="#7c4dcc", volume="#c47f00",
    crash="#d93535", grid="#c0c8de",
)


def makeModel():
    return FlashCrashModel(
        numberOfMarketMakerAgents=marketMakerCount.value,
        numberOfNoisyAgents=noisyCount.value,
        numberOfFundamentalAgents=fundamentalCount.value,
        numberOfHighFrequencyAgents=highFrequencyCount.value,
        numberOfMomentumAgents=momentumCount.value,
        numberOfStopLossAgents=stopLossCount.value,
        fundamentalVolatility=fundamentalVolatility.value,
        crashProbability=crashProbability.value,
        marketMakerStepProbability=0.9,
        noisyStepProbability=0.5,
        fundamentalStepProbability=0.02,
        highFrequencyStepProbability=1.0,
        momentumStepProbability=0.33,
        stopLossStepProbability=0.5,
    )


css = f"""
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background:{COLOURS['bg']}; font-family:'IBM Plex Sans',sans-serif; font-size:11px; color:{COLOURS['text']}; overflow:hidden; height:100vh; }}
.v-application,.v-application--wrap,.v-main,.v-main__wrap,.v-sheet,.theme--light.v-application {{
    background:{COLOURS['bg']} !important; background-color:{COLOURS['bg']} !important; color:{COLOURS['text']} !important; padding:0 !important; }}
html,body,#app,#app>div,.v-application>div {{ background:{COLOURS['bg']} !important; }}
.v-card,.v-list,.v-toolbar {{ background:{COLOURS['surface']} !important; color:{COLOURS['text']} !important; }}
.v-application--wrap>div,.v-main__wrap>div,.v-main__wrap>div>div {{ padding:0 !important; margin:0 !important; gap:0 !important; }}
.v-application--wrap>div>.col,.v-application--wrap>.col {{ padding:0 !important; gap:0 !important; }}
.row {{ margin:0 !important; }} .col {{ padding:0 !important; }}

.dash-header {{ background:{COLOURS['surface']} !important; border-bottom:1px solid {COLOURS['border']}; padding:0 20px !important;
    height:48px !important; min-height:48px !important; max-height:48px !important;
    align-items:center !important; gap:20px !important; flex-shrink:0 !important;
    flex-wrap:nowrap !important; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,0.06); }}
.header-title {{ font-family:'IBM Plex Mono',monospace !important; font-size:13px !important;
    font-weight:700 !important; color:{COLOURS['text']} !important; letter-spacing:0.06em; white-space:nowrap; }}
.header-badge {{ font-family:'IBM Plex Mono',monospace !important; font-size:10px !important;
    color:{COLOURS['accent']} !important; background:rgba(26,111,219,0.08) !important;
    border:1px solid rgba(26,111,219,0.25) !important; border-radius:3px; padding:2px 8px !important; white-space:nowrap; }}
.stat-block {{ display:flex !important; flex-direction:column !important; gap:1px !important;
    border-left:1px solid {COLOURS['border']} !important; padding-left:14px !important;
    flex-shrink:0; background:{COLOURS['surface']} !important; }}
.stat-label {{ font-size:9px !important; color:{COLOURS['text']} !important; text-transform:uppercase;
    letter-spacing:0.07em; font-weight:500 !important; background:{COLOURS['surface']} !important; }}
.stat-value {{ font-family:'IBM Plex Mono',monospace !important; font-size:12px !important;
    font-weight:700 !important; color:{COLOURS['text']} !important; background:{COLOURS['surface']} !important; }}

.dash-sidebar {{ width:240px !important; min-width:240px !important; max-width:240px !important;
    flex-shrink:0 !important; background:{COLOURS['surface']} !important; border-right:1px solid {COLOURS['border']} !important;
    overflow-y:auto !important; overflow-x:hidden !important; padding:12px 10px !important;
    height:calc(100vh - 48px) !important; align-items:stretch !important; gap:4px !important;
    box-shadow:1px 0 4px rgba(0,0,0,0.04); }}
.dash-sidebar::-webkit-scrollbar {{ width:3px; }}
.dash-sidebar::-webkit-scrollbar-thumb {{ background:{COLOURS['border']}; border-radius:2px; }}
.dash-sidebar .v-label,.dash-sidebar label,.dash-sidebar .v-input__slot label {{
    color:{COLOURS['text']} !important; font-size:10px !important; font-family:'IBM Plex Sans',sans-serif !important; }}
.dash-sidebar .v-slider__thumb,.dash-sidebar .v-slider__track-fill {{ background-color:{COLOURS['accent']} !important; }}
.sidebar-section {{ font-size:9px !important; font-weight:700 !important; text-transform:uppercase;
    letter-spacing:0.12em; color:{COLOURS['accent']} !important; padding:10px 2px 3px !important;
    border-top:1px solid {COLOURS['border']} !important; margin-top:4px !important; }}
.slider-bounds {{ display:flex !important; flex-direction:row !important; justify-content:space-between !important;
    width:100% !important; padding:0 2px !important; margin-top:-4px !important; margin-bottom:2px !important; }}
.slider-bound-val {{ font-family:'IBM Plex Mono',monospace !important; font-size:8px !important;
    color:{COLOURS['text']} !important; letter-spacing:0.04em; }}

.btn-step {{ background:{COLOURS['surfaceAlt']} !important; color:{COLOURS['text']} !important;
    border:1px solid {COLOURS['border']} !important; border-radius:4px !important; flex:1 !important;
    min-width:0 !important; padding:5px 0 !important; font-family:'IBM Plex Mono',monospace !important;
    font-size:10px !important; font-weight:600 !important; text-align:center !important; }}
.btn-step-row {{ display:flex !important; flex-direction:row !important; gap:4px !important;
    width:100% !important; flex-wrap:nowrap !important; align-items:stretch !important; }}
.btn-primary {{ background:{COLOURS['accent']} !important; color:#fff !important; border:none !important;
    border-radius:4px !important; width:100% !important; padding:7px 0 !important;
    font-family:'IBM Plex Mono',monospace !important; font-size:11px !important; font-weight:700 !important; }}
.btn-danger,.btn-danger.v-btn,.v-btn.btn-danger {{ background:#fde8e8 !important; color:{COLOURS['ask']} !important;
    border:1px solid #f5aaaa !important; border-radius:4px !important; width:100% !important; padding:5px 0 !important;
    font-family:'IBM Plex Mono',monospace !important; font-size:10px !important; font-weight:600 !important; }}
.btn-danger .v-btn__content,.v-btn.btn-danger .v-btn__content {{ color:{COLOURS['ask']} !important; background:transparent !important; }}
.btn-danger::before,.v-btn.btn-danger::before {{ background:transparent !important; opacity:0 !important; }}
.btn-cooldown,.btn-cooldown.v-btn,.v-btn.btn-cooldown {{ background:#fdf0eb !important; color:#b04a30 !important;
    border:1px solid #e8b49a !important; border-radius:4px !important; width:100% !important; padding:5px 0 !important;
    font-family:'IBM Plex Mono',monospace !important; font-size:10px !important; font-weight:600 !important; }}
.btn-cooldown .v-btn__content,.v-btn.btn-cooldown .v-btn__content {{ color:#b04a30 !important; background:transparent !important; }}
.btn-cooldown::before,.v-btn.btn-cooldown::before {{ background:transparent !important; opacity:0 !important; }}
"""


def getDataFrame(model):
    dc = model.dataCollector.model_vars
    n = min(len(v) for v in dc.values())
    return pd.DataFrame({k: v[:n] for k, v in dc.items()})


def makeFig(wide=False):
    fig, ax = plt.subplots(figsize=(9.0 if wide else 6.0, 2.8), facecolor=COLOURS['bg'])
    fig.patch.set_facecolor(COLOURS['bg'])
    fig.subplots_adjust(left=0.08, right=0.97, top=0.87, bottom=0.20)
    return fig, ax


def styleAx(ax, title=""):
    ax.set_facecolor("#fafbfd")
    ax.tick_params(colors=COLOURS['text'], labelsize=7)
    ax.xaxis.label.set_color(COLOURS['text'])
    ax.yaxis.label.set_color(COLOURS['text'])
    for sp in ax.spines.values():
        sp.set_edgecolor(COLOURS['border'])
    ax.grid(True, color=COLOURS['grid'], linewidth=0.4, alpha=0.7)
    if title:
        ax.set_title(title, color=COLOURS['text'], fontsize=8, fontweight="600",
                     pad=5, loc="left", fontfamily="monospace")


def addLegend(ax):
    leg = ax.legend(facecolor=COLOURS['surface'], edgecolor=COLOURS['border'], fontsize=6.5, framealpha=0.95)
    for t in leg.get_texts():
        t.set_color(COLOURS['text'])


def addCrashOverlays(ax, model, df):
    xMin = df.index[-WINDOW] if len(df.index) > WINDOW else df.index[0]
    xMax = df.index[-1]
    for t in model.crashEvents:
        ax.axvline(t, color=COLOURS['crash'], linewidth=1.2, alpha=0.5, linestyle=":")
    for start, end in model.crashWindows:
        s, e = max(xMin, start), min(xMax, end)
        if s < e:
            ax.axvspan(s, e, color=COLOURS['crash'], alpha=0.08, zorder=0)
    if model.activeCrashTicks > 0 and model.currentCrashStart is not None:
        s = max(xMin, model.currentCrashStart)
        if s <= xMax:
            ax.axvspan(s, xMax, color=COLOURS['crash'], alpha=0.12, zorder=0)


def clipX(ax, df):
    if len(df.index) > WINDOW:
        ax.set_xlim(df.index[-WINDOW], df.index[-1])


def renderPriceChart(model):
    df = getDataFrame(model)
    fig, ax = makeFig(wide=True)
    styleAx(ax, "PRICE  /  FUNDAMENTAL")
    if "MidPrice" in df.columns and df["MidPrice"].dropna().any():
        ax.plot(df.index, pd.to_numeric(df["MidPrice"], errors="coerce").ffill(),
                color=COLOURS['price'], linewidth=1.4, label="Mid Price")
    if "Fundamental" in df.columns:
        ax.plot(df.index, df["Fundamental"], color=COLOURS['fund'], linewidth=1.1,
                linestyle="--", alpha=0.85, label="Fundamental")
    addCrashOverlays(ax, model, df)
    if model.crashEvents:
        ax.axvline(model.crashEvents[-1], color=COLOURS['crash'], linewidth=1.4,
                   alpha=0.7, linestyle=":", label="Crash")
    clipX(ax, df)
    ax.set_ylabel("Price", fontsize=7)
    addLegend(ax)
    return fig


def renderSpreadChart(model):
    df = getDataFrame(model)
    fig, ax = makeFig(wide=True)
    styleAx(ax, "BID-ASK  SPREAD")
    if "Spread" in df.columns:
        v = pd.to_numeric(df["Spread"], errors="coerce").ffill().fillna(0)
        ax.fill_between(df.index, v, color=COLOURS['spread'], alpha=0.18)
        ax.plot(df.index, v, color=COLOURS['spread'], linewidth=1.2)
        addCrashOverlays(ax, model, df)
        clipX(ax, df)
    ax.set_ylabel("Spread", fontsize=7)
    return fig


def renderVolumeChart(model, ma=20):
    df = getDataFrame(model)
    fig, ax = makeFig(wide=True)
    styleAx(ax, "TRADE  VOLUME")
    if "TradeCount" in df.columns:
        vol = pd.to_numeric(df["TradeCount"], errors="coerce").fillna(0).diff().fillna(0).clip(lower=0)
        ax.bar(df.index, vol, color=COLOURS['volume'], width=0.8, alpha=0.5)
        ax.plot(df.index, vol.rolling(ma, min_periods=1).mean(),
                color=COLOURS['price'], linewidth=1.2, linestyle="--", label=f"{ma}-step MA")
        addCrashOverlays(ax, model, df)
        clipX(ax, df)
        addLegend(ax)
    ax.set_ylabel("Trades", fontsize=7)
    ax.set_xlabel("Step", fontsize=7)
    return fig


def renderDepthChart(model):
    fig, ax = makeFig(wide=False)
    styleAx(ax, "CUMULATIVE  BOOK  DEPTH")
    bids, asks = model.getOrderBookSnapshot(levels=20)
    for data, color in [(bids, COLOURS['bid']), (asks, COLOURS['ask'])]:
        if not data:
            continue
        prices = sorted([d["price"] for d in data])
        qtys = [next(d["qty"] for d in data if d["price"] == p) for p in prices]
        cum = np.cumsum(qtys[::-1])[::-1] if color == COLOURS['bid'] else np.cumsum(qtys)
        ax.fill_between(prices, cum, color=color, alpha=0.25, step="post")
        ax.plot(prices, cum, color=color, linewidth=1.2, drawstyle="steps-post")
    ax.set_ylabel("Cum. Qty", fontsize=7)
    leg = ax.legend(handles=[mpatches.Patch(color=COLOURS['bid'], label="Bids", alpha=0.6),
                             mpatches.Patch(color=COLOURS['ask'], label="Asks", alpha=0.6)],
                    facecolor=COLOURS['surface'], edgecolor=COLOURS['border'], fontsize=6.5)
    for t in leg.get_texts():
        t.set_color(COLOURS['text'])
    return fig


def renderOrderBook(model):
    fig, ax = makeFig(wide=False)
    styleAx(ax, "LIVE  ORDER  BOOK")
    bids, asks = model.getOrderBookSnapshot(levels=10)
    if bids:
        ax.barh([d["price"] for d in bids], [d["qty"] for d in bids],
                color=COLOURS['bid'], alpha=0.6, height=0.012, label="Bids")
    if asks:
        ax.barh([d["price"] for d in asks], [d["qty"] for d in asks],
                color=COLOURS['ask'], alpha=0.6, height=0.012, label="Asks")
    mid = model.limitOrderBook.midPrice()
    if mid:
        ax.axhline(mid, color=COLOURS['price'], linewidth=1.2, linestyle="--",
                   alpha=0.8, label=f"Mid {mid:.2f}")
    ax.set_xlabel("Qty", fontsize=7)
    ax.set_ylabel("Price", fontsize=7)
    addLegend(ax)
    return fig


def renderAgentActivity(model):
    fig, ax = makeFig(wide=False)
    ax.set_facecolor("#fafbfd")
    fig.patch.set_facecolor(COLOURS['bg'])
    ax.set_title("AGENT  COMPOSITION", color=COLOURS['text'], fontsize=8,
                 fontweight="600", pad=5, loc="left", fontfamily="monospace")
    entries = [
        (len(model.marketMakers), "Mkt Maker", "#2563eb"),
        (len(model.fundamental), "Fundamental", "#e03131"),
        (len(model.noisy), "Noisy", "#16a34a"),
        (len(model.highFrequency), "HFT", "#d97706"),
        (len(model.momentum), "Momentum", "#9333ea"),
        (len(model.stopLoss), "Stop Loss", "#0891b2"),
    ]
    nz = [(c, l, col) for c, l, col in entries if c > 0]
    if nz:
        c_, l_, col_ = zip(*nz)
        wedges, texts, autotexts = ax.pie(
            c_, labels=l_, colors=col_, autopct="%1.0f%%",
            wedgeprops={"edgecolor": "#ffffff", "linewidth": 2.5},
            startangle=90, pctdistance=0.75, labeldistance=1.12,
        )
        for t in texts:
            t.set_color(COLOURS['text']);
            t.set_fontsize(8);
            t.set_fontweight("600")
        for at in autotexts:
            at.set_color("#ffffff");
            at.set_fontsize(7.5);
            at.set_fontweight("700")
    return fig


def _fmt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


@solara.component
def BoundedSliderInt(label, value, min, max):
    solara.SliderInt(label, value=value, min=min, max=max)
    with solara.Row(classes=["slider-bounds"]):
        solara.Text(_fmt(min), classes=["slider-bound-val"])
        solara.Text(_fmt(max), classes=["slider-bound-val"])


@solara.component
def BoundedSliderFloat(label, value, min, max, step):
    solara.SliderFloat(label, value=value, min=min, max=max, step=step)
    with solara.Row(classes=["slider-bounds"]):
        solara.Text(_fmt(min), classes=["slider-bound-val"])
        solara.Text(_fmt(max), classes=["slider-bound-val"])


@solara.component
def Sidebar():
    model = modelState.value

    def advance(n):
        if model:
            for _ in range(n):
                model.step()
            modelState.set(modelState.value)
            stepCount.set(stepCount.value + n)

    def reset():
        modelState.set(makeModel())
        stepCount.set(0)
        running.set(False)

    with solara.Column(classes=["dash-sidebar"]):
        solara.Text("CONTROLS", classes=["sidebar-section"])
        with solara.Row(classes=["btn-step-row"]):
            solara.Button("RESET", classes=["btn-step"], on_click=reset)
            solara.Button("+10", classes=["btn-step"], on_click=lambda: advance(10))
            solara.Button("+50", classes=["btn-step"], on_click=lambda: advance(50))
            solara.Button("+200", classes=["btn-step"], on_click=lambda: advance(200))
        solara.Button("RUN" if not running.value else "PAUSE", classes=["btn-primary"],
                      on_click=lambda: running.set(not running.value))

        _ = stepCount.value
        if model:
            active = model.activeCrashTicks > 0
            cooldown = model.crashCooldown > 0
            can = not active and not cooldown
            label = (f"CRASH ACTIVE ({model.activeCrashTicks})" if active
                     else f"COOLDOWN: {model.crashCooldown}" if cooldown
            else "TRIGGER FLASH CRASH")
            cls = "btn-cooldown" if cooldown else "btn-danger"
            solara.Button(label, classes=[cls], disabled=not can,
                          on_click=lambda: model.triggerManualCrash() or stepCount.set(stepCount.value))

        solara.Text("AGENTS", classes=["sidebar-section"])
        BoundedSliderInt("Market Makers", marketMakerCount, 0, 200)
        BoundedSliderInt("Noisy Agents", noisyCount, 0, 200)
        BoundedSliderInt("Fundamental", fundamentalCount, 0, 200)
        BoundedSliderInt("HFT Agents", highFrequencyCount, 0, 200)
        BoundedSliderInt("Momentum", momentumCount, 0, 200)
        BoundedSliderInt("Stop Loss", stopLossCount, 0, 200)

        solara.Text("MARKET", classes=["sidebar-section"])
        BoundedSliderFloat("Fundamental Vol", fundamentalVolatility, 0.01, 2.0, 0.01)


_CELL_L = {"flex": "1.5", "minWidth": "0", "minHeight": "0", "overflow": "hidden", "background": COLOURS['bg']}
_CELL_R = {"flex": "1", "minWidth": "0", "minHeight": "0", "overflow": "hidden", "background": COLOURS['bg']}
_ROW = {"flex": "1", "minHeight": "0", "overflow": "hidden", "borderBottom": f"1px solid {COLOURS['border']}",
        "alignItems": "stretch", "gap": "0"}
_ROW_LAST = {**_ROW, "borderBottom": "none"}
_DIV = {"borderRight": f"1px solid {COLOURS['border']}"}


@solara.component
def ChartGrid():
    model = modelState.value
    if not model:
        solara.Text("Initialising…")
        return
    _ = stepCount.value
    rows = [
        (renderPriceChart, renderDepthChart, _ROW),
        (renderSpreadChart, renderOrderBook, _ROW),
        (renderVolumeChart, renderAgentActivity, _ROW_LAST),
    ]
    with solara.Column(style={"flex": "1", "minWidth": "0", "height": "calc(100vh - 48px)",
                              "overflow": "hidden", "gap": "0", "alignItems": "stretch"}):
        for left, right, rowStyle in rows:
            with solara.Row(style=rowStyle):
                with solara.Column(style={**_CELL_L, **_DIV}):
                    solara.FigureMatplotlib(left(model))
                with solara.Column(style=_CELL_R):
                    solara.FigureMatplotlib(right(model))


@solara.component
def page():
    solara.Title("Flash Crash Simulation")
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

    with solara.Column(style={"height": "100vh", "overflow": "hidden", "gap": "0", "padding": "0", "margin": "0"}):
        with solara.Row(classes=["dash-header"]):
            _ = stepCount.value
            solara.Text("AGENT BASED FLASH CRASH AND RECOVERY SIMULATION", classes=["header-title"])
            solara.Text("MESA and SOLARA", classes=["header-badge"])
            model = modelState.value
            if model:
                mid = model.limitOrderBook.midPrice()
                spread = model.limitOrderBook.spread()
                for lbl, val in [
                    ("MID PRICE", f"{mid:.2f}" if mid else "—"),
                    ("FUNDAMENTAL", f"{float(model.market.fundamentalPrice):.2f}"),
                    ("SPREAD", f"{spread:.4f}" if spread else "—"),
                    ("TRADES", str(len(model.limitOrderBook.trades))),
                    ("BID DEPTH", str(model.limitOrderBook.depth("buy", 10))),
                    ("ASK DEPTH", str(model.limitOrderBook.depth("sell", 10))),
                    ("CRASHES", str(len(model.crashEvents))),
                    ("STEP", str(stepCount.value)),
                ]:
                    with solara.Column(classes=["stat-block"]):
                        solara.Text(lbl, classes=["stat-label"])
                        solara.Text(val, classes=["stat-value"])

        with solara.Row(style={"flex": "1", "minHeight": "0", "overflow": "hidden",
                               "gap": "0", "alignItems": "stretch", "flexWrap": "nowrap"}):
            Sidebar()
            ChartGrid()
