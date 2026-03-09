import matplotlib
import solara

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import sys, os, asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Simulation.model import FlashCrashModel

# ── Reactive state ─────────────────────────────────────────────────────────────
model_state     = solara.reactive(None)
running         = solara.reactive(False)
step_count      = solara.reactive(0)
n_market_maker  = solara.reactive(15)
n_noisy         = solara.reactive(7)
n_fundamental   = solara.reactive(3)
n_hft           = solara.reactive(2)
n_momentum      = solara.reactive(3)
n_stoploss      = solara.reactive(3)
fundamental_vol = solara.reactive(0.2)
mm_spread       = solara.reactive(0.7)
crash_prob      = solara.reactive(0.002)

def make_model():
    return FlashCrashModel(
        n_market_maker=n_market_maker.value, n_noisy=n_noisy.value,
        n_fundamental=n_fundamental.value,   n_hft=n_hft.value,
        n_momentum=n_momentum.value,         n_stoploss=n_stoploss.value,
        fundamental_vol=fundamental_vol.value, mm_spread=mm_spread.value,
        crash_prob=crash_prob.value,
    )

# ── Colour palette (light theme) ───────────────────────────────────────────────
BG     = "#f5f5f5"
PANEL  = "#ffffff"
GRID   = "#e0e0e0"
TEXT   = "#212121"
MUTED  = "#757575"
BID    = "#2e7d32"
ASK    = "#c62828"
PRICE  = "#1565c0"
FUND   = "#e65100"
SPREAD = "#6a1b9a"
TRADE  = "#00838f"
CRASH  = "#d32f2f"

CSS = f"""
    body {{ background: {BG}; margin: 0; font-family: 'Roboto', sans-serif; font-size: 11px; }}
    .panel {{ background: {PANEL}; border-radius: 8px; padding: 16px; border: 1px solid {GRID}; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .btn   {{ background: #1976d2; color: #ffffff; border: none; border-radius: 4px; }}
    .btn-run   {{ background: #1976d2; color: #ffffff; border-radius: 4px; width: 100%; }}
    .btn-run.paused {{ background: #1565c0; }}
    .btn-crash {{ background: #fff3e0; color: #c62828; border: 1px solid #ef9a9a; border-radius: 4px; font-weight: bold; }}
    .btn-crash.active {{ background: #ffebee; }}
    .section-label {{ color: {MUTED}; margin-top: 8px; }}
    .crash-label   {{ color: {CRASH}; margin-top: 8px; }}
    .stat-label    {{ color: {MUTED}; }}
    .stat-value    {{ color: #424242; font-weight: bold; }}
    .header-title  {{ color: #ffffff; font-weight: bold; font-size: 18px; }}
    .header-sub    {{ color: #bbdefb; font-size: 13px; }}
    .panel-title   {{ color: #1565c0; font-weight: bold; font-size: 16px; margin-bottom: 8px; }}
    .step-counter  {{ color: {MUTED}; }}
    .v-label {{ color: #616161 !important; font-size: 11px !important; }}
    .v-input__slot label {{ color: #616161 !important; }}
"""

# ── Chart helpers ──────────────────────────────────────────────────────────────
def _style_ax(ax, title=""):
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.7)
    if title:
        ax.set_title(title, color=TEXT, fontsize=9, fontweight="bold", pad=6)

def _legend(ax):
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7)

def _crash_lines(ax, model):
    for t in model.crash_events:
        ax.axvline(t, color=CRASH, linewidth=1.5, alpha=0.7, linestyle=":")

# ── Chart renderers ────────────────────────────────────────────────────────────
def render_price_chart(model):
    df = model.datacollector.get_model_vars_dataframe()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 5), facecolor=BG)
    fig.subplots_adjust(hspace=0.35, left=0.1, right=0.97, top=0.93, bottom=0.1)

    _style_ax(ax1, "Price & Fundamental Value")
    if "MidPrice" in df.columns and df["MidPrice"].dropna().any():
        ax1.plot(df.index, df["MidPrice"], color=PRICE, linewidth=1.5, label="Mid Price")
    if "Fundamental" in df.columns:
        ax1.plot(df.index, df["Fundamental"], color=FUND, linewidth=1.2, linestyle="--", label="Fundamental", alpha=0.85)
    _crash_lines(ax1, model)
    if model.crash_events:
        ax1.axvline(model.crash_events[-1], color=CRASH, linewidth=1.5, alpha=0.8, linestyle=":", label="Flash Crash")
    ax1.set_ylabel("Price", color=TEXT, fontsize=8)
    _legend(ax1)

    _style_ax(ax2, "Bid-Ask Spread")
    if "Spread" in df.columns and df["Spread"].dropna().any():
        sv = df["Spread"].ffill()
        ax2.fill_between(df.index, sv, color=SPREAD, alpha=0.4)
        ax2.plot(df.index, sv, color=SPREAD, linewidth=1.2)
        _crash_lines(ax2, model)
    ax2.set_ylabel("Spread", color=TEXT, fontsize=8)
    ax2.set_xlabel("Step",   color=TEXT, fontsize=8)
    return fig


def render_order_book(model):
    fig, ax = plt.subplots(figsize=(5, 5), facecolor=BG)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.1)
    title = "Live Order Book ⚠ CRASH ACTIVE" if model.active_crash_ticks > 0 else "Live Order Book (Top 10 Levels)"
    _style_ax(ax, title)
    if model.active_crash_ticks > 0:
        ax.title.set_color(CRASH)

    bids, asks = model.get_order_book_snapshot(levels=10)
    if not bids and not asks:
        ax.text(0.5, 0.5, "No orders in book", transform=ax.transAxes, ha="center", va="center", color=TEXT, fontsize=10)
        return fig

    if bids:
        ax.barh([d["price"] for d in bids], [d["qty"] for d in bids], color=BID, alpha=0.75, height=0.015, label="Bids")
    if asks:
        ax.barh([d["price"] for d in asks], [d["qty"] for d in asks], color=ASK, alpha=0.75, height=0.015, label="Asks")
    mid = model.lob.midPrice()
    if mid:
        ax.axhline(mid, color=PRICE, linewidth=1.2, linestyle="--", alpha=0.8, label=f"Mid: {mid:.2f}")
    ax.set_xlabel("Quantity", color=TEXT, fontsize=8)
    ax.set_ylabel("Price",    color=TEXT, fontsize=8)
    _legend(ax)
    return fig


def render_depth_chart(model):
    fig, ax = plt.subplots(figsize=(5, 3.5), facecolor=BG)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.12)
    _style_ax(ax, "Cumulative Book Depth")

    bids, asks = model.get_order_book_snapshot(levels=20)
    if not bids and not asks:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", va="center", color=TEXT, fontsize=10)
        return fig

    if bids:
        bp = sorted([d["price"] for d in bids])
        bq = [next(d["qty"] for d in bids if d["price"] == p) for p in bp]
        bc = np.cumsum(bq[::-1])[::-1]
        ax.fill_between(bp, bc, color=BID, alpha=0.5, step="post")
        ax.plot(bp, bc, color=BID, linewidth=1.2, drawstyle="steps-post")
    if asks:
        ap = sorted([d["price"] for d in asks])
        aq = [next(d["qty"] for d in asks if d["price"] == p) for p in ap]
        ac = np.cumsum(aq)
        ax.fill_between(ap, ac, color=ASK, alpha=0.5, step="post")
        ax.plot(ap, ac, color=ASK, linewidth=1.2, drawstyle="steps-post")

    ax.set_xlabel("Price", color=TEXT, fontsize=8)
    ax.set_ylabel("Cumulative Qty", color=TEXT, fontsize=8)
    ax.legend(handles=[mpatches.Patch(color=BID, label="Bid Depth", alpha=0.7),
                       mpatches.Patch(color=ASK, label="Ask Depth", alpha=0.7)],
              facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, fontsize=7)
    return fig


def render_agent_activity(model):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 3), facecolor=BG)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.15, wspace=0.35)

    ax1.set_facecolor(BG)
    ax1.set_title("Agent Composition", color=TEXT, fontsize=9, fontweight="bold")
    counts = [len(model._market_makers), len(model._fundamental), len(model._noisy),
              len(model._hft), len(model._momentum), len(model._stoploss)]
    labels = ["Mkt Maker", "Fundamental", "Noisy", "HFT", "Momentum", "Stop Loss"]
    colors = [BID, FUND, PRICE, TRADE, "#388e3c", "#f57c00"]
    nz = [(c, l, col) for c, l, col in zip(counts, labels, colors) if c > 0]
    if nz:
        c_, l_, col_ = zip(*nz)
        _, _, autos = ax1.pie(c_, labels=l_, colors=col_, autopct="%1.0f%%",
                              textprops={"color": TEXT, "fontsize": 7},
                              wedgeprops={"edgecolor": "#ffffff", "linewidth": 1.5})
        for a in autos:
            a.set_color(TEXT); a.set_fontsize(7)

    _style_ax(ax2, "Cumulative Trade Count")
    df = model.datacollector.get_model_vars_dataframe()
    if "TradeCount" in df.columns:
        ax2.plot(df.index, df["TradeCount"], color=TRADE, linewidth=1.5)
        ax2.fill_between(df.index, df["TradeCount"], color=TRADE, alpha=0.2)
        _crash_lines(ax2, model)
    ax2.set_xlabel("Step",   color=TEXT, fontsize=8)
    ax2.set_ylabel("Trades", color=TEXT, fontsize=8)
    return fig


# ── Solara components ──────────────────────────────────────────────────────────
@solara.component
def ControlPanel():
    m = model_state.value

    def advance(n):
        if m is not None:
            for _ in range(n):
                m.step()
            step_count.set(step_count.value + n)

    with solara.Column(classes=["panel"]):
        solara.Text("⚡ Flash Crash ABM", classes=["panel-title"])

        with solara.Row(style={"flexWrap": "wrap", "gap": "4px"}):
            solara.Button("↺ Reset", classes=["btn"], on_click=lambda: [model_state.set(make_model()), step_count.set(0), running.set(False)])
            solara.Button("+10",  classes=["btn"], on_click=lambda: advance(10))
            solara.Button("+50",  classes=["btn"], on_click=lambda: advance(50))
            solara.Button("+200", classes=["btn"], on_click=lambda: advance(200))

        label = "⏸ Pause" if running.value else "▷ Run"
        solara.Button(label, classes=["btn-run"] + (["paused"] if running.value else []),
                      on_click=lambda: running.set(not running.value))
        solara.Text(f"Step: {step_count.value}", classes=["step-counter"])

        solara.Text("── Flash Crash ──", classes=["crash-label"])
        if m is not None:
            if m.active_crash_ticks > 0:
                crash_status = f"⚠ CRASH ACTIVE ({m.active_crash_ticks} ticks left)"
            elif m.crash_cooldown > 0:
                crash_status = f"Cooldown: {m.crash_cooldown} ticks"
            else:
                crash_status = f"Events: {len(m.crash_events)}"
            solara.Text(crash_status, classes=["stat-value"])

        def on_trigger_crash():
            if m is not None:
                m.trigger_manual_crash()
                step_count.set(step_count.value)

        crash_active = m is not None and m.active_crash_ticks > 0
        solara.Button("💥 Trigger Flash Crash",
                      classes=["btn-crash"] + (["active"] if crash_active else []),
                      on_click=on_trigger_crash)

        solara.SliderFloat("Crash Probability", value=crash_prob, min=0.0, max=0.02, step=0.001)

        solara.Text("── Agent Counts ──", classes=["section-label"])
        solara.SliderInt("Market Makers", value=n_market_maker, min=0, max=20)
        solara.SliderInt("Noisy Agents",  value=n_noisy,        min=0, max=20)
        solara.SliderInt("Fundamental",   value=n_fundamental,  min=0, max=10)
        solara.SliderInt("HFT Agents",    value=n_hft,          min=0, max=10)
        solara.SliderInt("Momentum",      value=n_momentum,     min=0, max=10)
        solara.SliderInt("Stop Loss",     value=n_stoploss,     min=0, max=10)

        solara.Text("── Market Parameters ──", classes=["section-label"])
        solara.SliderFloat("Fundamental Vol", value=fundamental_vol, min=0.01, max=2.0, step=0.01)
        solara.SliderFloat("MM Spread",       value=mm_spread,       min=0.1,  max=3.0, step=0.05)

        if m is not None:
            solara.Text("── Live Stats ──", classes=["section-label"])
            mid    = m.lob.midPrice()
            spread = m.lob.spread()
            stats  = [
                ("Mid Price",    f"{mid:.2f}"                          if mid    else "—"),
                ("Fundamental",  f"{float(m.market.fundamentalPrice):.2f}"),
                ("Spread",       f"{spread:.4f}"                       if spread else "—"),
                ("Total Trades", str(len(m.lob.trades))),
                ("Bid Depth",    str(m.lob.depth("buy",  10))),
                ("Ask Depth",    str(m.lob.depth("sell", 10))),
                ("Crash Events", str(len(m.crash_events))),
            ]
            for lbl, val in stats:
                with solara.Row(style={"justifyContent": "space-between"}):
                    solara.Text(lbl, classes=["stat-label"])
                    solara.Text(val, classes=["stat-value"])


@solara.component
def ChartPanel():
    m = model_state.value
    if m is None:
        solara.Text("Click ↺ Reset to initialise the model", classes=["stat-label"])
        return

    _ = step_count.value

    with solara.Column(style={"gap": "16px"}):
        with solara.Row(style={"gap": "16px", "alignItems": "flex-start"}):
            with solara.Column(style={"flex": "1"}):
                for fig in [render_order_book(m), render_depth_chart(m)]:
                    solara.FigureMatplotlib(fig); plt.close(fig)
            with solara.Column(style={"flex": "1.4"}):
                for fig in [render_price_chart(m), render_agent_activity(m)]:
                    solara.FigureMatplotlib(fig); plt.close(fig)


@solara.component
def Page():
    solara.Style(CSS)

    async def auto_stepper():
        while True:
            await asyncio.sleep(0.3)
            if running.value and model_state.value is not None:
                model_state.value.step()
                step_count.set(step_count.value + 1)

    solara.lab.use_task(auto_stepper, dependencies=[])

    with solara.Row(style={"background": "#1976d2", "borderBottom": "1px solid #1565c0",
                           "padding": "12px 24px", "alignItems": "center", "gap": "12px"}):
        solara.Text("📈 Flash Crash ABM Simulator", classes=["header-title"])
        solara.Text("Mesa + Solara  ·  with Manual Crash Trigger", classes=["header-sub"])

    with solara.Row(style={"padding": "16px", "gap": "16px", "alignItems": "flex-start",
                           "background": BG, "minHeight": "calc(100vh - 60px)"}):
        with solara.Column(style={"width": "270px", "flexShrink": "0"}):
            ControlPanel()
        with solara.Column(style={"flex": "1", "minWidth": "0"}):
            ChartPanel()
