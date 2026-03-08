import matplotlib
import solara

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import sys, os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from Simulation.model import FlashCrashModel

# reactove state parameters
model_state = solara.reactive(None)
running = solara.reactive(False)
step_count = solara.reactive(0)

# market Parameters
n_market_maker = solara.reactive(15)
n_noisy = solara.reactive(7)
n_fundamental = solara.reactive(3)
n_hft = solara.reactive(2)
n_momentum = solara.reactive(3)
n_stoploss = solara.reactive(3)
fundamental_vol = solara.reactive(0.2)
mm_spread = solara.reactive(0.7)
crash_prob = solara.reactive(0.002)


def make_model():
    return FlashCrashModel(
        n_market_maker=n_market_maker.value,
        n_noisy=n_noisy.value,
        n_fundamental=n_fundamental.value,
        n_hft=n_hft.value,
        n_momentum=n_momentum.value,
        n_stoploss=n_stoploss.value,
        fundamental_vol=fundamental_vol.value,
        mm_spread=mm_spread.value,
        crash_prob=crash_prob.value,
    )


# colours
PANEL_BG = "#161b22"
GRID_COL = "#21262d"
TEXT_COL = "#e6edf3"
BID_COL = "#2ea043"
ASK_COL = "#f85149"
PRICE_COL = "#58a6ff"
FUND_COL = "#d29922"
SPREAD_COL = "#bc8cff"
TRADE_COL = "#ff7b72"
CRASH_COL = "#ff4500"
MOM_COL = "#3fb950"
SL_COL = "#ffa657"
DARK_BG = "#21262d"


def apply_dark_style(ax, title=""):
    ax.set_facecolor(DARK_BG)
    ax.tick_params(colors=TEXT_COL, labelsize=8)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
    ax.grid(True, color=GRID_COL, linewidth=0.5, alpha=0.7)
    if title:
        ax.set_title(title, color=TEXT_COL, fontsize=9, fontweight="bold", pad=6)


# chart rendering
def render_price_chart(model):
    fig, axes = plt.subplots(2, 1, figsize=(7, 5), facecolor=DARK_BG)
    fig.subplots_adjust(hspace=0.35, left=0.1, right=0.97, top=0.93, bottom=0.1)

    df = model.datacollector.get_model_vars_dataframe()

    ax1 = axes[0]
    apply_dark_style(ax1, "Price & Fundamental Value")

    if "MidPrice" in df.columns and df["MidPrice"].dropna().any():
        ax1.plot(df.index, df["MidPrice"], color=PRICE_COL, linewidth=1.5, label="Mid Price")
    if "Fundamental" in df.columns:
        ax1.plot(df.index, df["Fundamental"], color=FUND_COL, linewidth=1.2,
                 linestyle="--", label="Fundamental", alpha=0.85)

    # Mark crash events as vertical red bands
    for crash_t in model.crash_events:
        ax1.axvline(crash_t, color=CRASH_COL, linewidth=1.5, alpha=0.8, linestyle=":")
    # Add one label entry for legend
    if model.crash_events:
        ax1.axvline(model.crash_events[-1], color=CRASH_COL, linewidth=1.5,
                    alpha=0.8, linestyle=":", label="Flash Crash")

    ax1.set_ylabel("Price", color=TEXT_COL, fontsize=8)
    ax1.legend(facecolor=PANEL_BG, edgecolor=GRID_COL, labelcolor=TEXT_COL, fontsize=7)

    ax2 = axes[1]
    apply_dark_style(ax2, "Bid-Ask Spread")
    if "Spread" in df.columns and df["Spread"].dropna().any():
        spread_vals = df["Spread"].ffill()
        ax2.fill_between(df.index, spread_vals, color=SPREAD_COL, alpha=0.4)
        ax2.plot(df.index, spread_vals, color=SPREAD_COL, linewidth=1.2)
        # Shade crash periods on spread too
        for crash_t in model.crash_events:
            ax2.axvline(crash_t, color=CRASH_COL, linewidth=1.5, alpha=0.6, linestyle=":")
    ax2.set_ylabel("Spread", color=TEXT_COL, fontsize=8)
    ax2.set_xlabel("Step", color=TEXT_COL, fontsize=8)

    return fig


def render_order_book(model):
    fig, ax = plt.subplots(figsize=(5, 5), facecolor=DARK_BG)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.1)
    apply_dark_style(ax, "Live Order Book (Top 10 Levels)")

    bid_data, ask_data = model.get_order_book_snapshot(levels=10)

    if not bid_data and not ask_data:
        ax.text(0.5, 0.5, "No orders in book", transform=ax.transAxes,
                ha="center", va="center", color=TEXT_COL, fontsize=10)
        return fig

    if bid_data:
        bid_prices = [d["price"] for d in bid_data]
        bid_qtys = [d["qty"] for d in bid_data]
        ax.barh(bid_prices, bid_qtys, color=BID_COL, alpha=0.75, height=0.015, label="Bids")

    if ask_data:
        ask_prices = [d["price"] for d in ask_data]
        ask_qtys = [d["qty"] for d in ask_data]
        ax.barh(ask_prices, ask_qtys, color=ASK_COL, alpha=0.75, height=0.015, label="Asks")

    mid = model.lob.midPrice()
    if mid:
        ax.axhline(mid, color=PRICE_COL, linewidth=1.2, linestyle="--", alpha=0.8,
                   label=f"Mid: {mid:.2f}")

    # Flash crash indicator on order book
    if model.active_crash_ticks > 0:
        ax.set_title("Live Order Book ⚠ CRASH ACTIVE", color=CRASH_COL,
                     fontsize=9, fontweight="bold", pad=6)

    ax.set_xlabel("Quantity", color=TEXT_COL, fontsize=8)
    ax.set_ylabel("Price", color=TEXT_COL, fontsize=8)
    ax.legend(facecolor=PANEL_BG, edgecolor=GRID_COL, labelcolor=TEXT_COL, fontsize=7)
    return fig


def render_depth_chart(model):
    fig, ax = plt.subplots(figsize=(5, 3.5), facecolor=DARK_BG)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.12)
    apply_dark_style(ax, "Cumulative Book Depth")

    bid_data, ask_data = model.get_order_book_snapshot(levels=20)

    if not bid_data and not ask_data:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                ha="center", va="center", color=TEXT_COL, fontsize=10)
        return fig

    if bid_data:
        b_prices = sorted([d["price"] for d in bid_data])
        b_qtys = [next(d["qty"] for d in bid_data if d["price"] == p) for p in b_prices]
        b_cumul = np.cumsum(b_qtys[::-1])[::-1]
        ax.fill_between(b_prices, b_cumul, color=BID_COL, alpha=0.5, step="post")
        ax.plot(b_prices, b_cumul, color=BID_COL, linewidth=1.2, drawstyle="steps-post")

    if ask_data:
        a_prices = sorted([d["price"] for d in ask_data])
        a_qtys = [next(d["qty"] for d in ask_data if d["price"] == p) for p in a_prices]
        a_cumul = np.cumsum(a_qtys)
        ax.fill_between(a_prices, a_cumul, color=ASK_COL, alpha=0.5, step="post")
        ax.plot(a_prices, a_cumul, color=ASK_COL, linewidth=1.2, drawstyle="steps-post")

    ax.set_xlabel("Price", color=TEXT_COL, fontsize=8)
    ax.set_ylabel("Cumulative Qty", color=TEXT_COL, fontsize=8)
    bid_patch = mpatches.Patch(color=BID_COL, label="Bid Depth", alpha=0.7)
    ask_patch = mpatches.Patch(color=ASK_COL, label="Ask Depth", alpha=0.7)
    ax.legend(handles=[bid_patch, ask_patch], facecolor=PANEL_BG,
              edgecolor=GRID_COL, labelcolor=TEXT_COL, fontsize=7)
    return fig


def render_agent_activity(model):
    fig, axes = plt.subplots(1, 2, figsize=(7, 3), facecolor=DARK_BG)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.15, wspace=0.35)

    ax1 = axes[0]
    ax1.set_facecolor(DARK_BG)
    ax1.set_title("Agent Composition", color=TEXT_COL, fontsize=9, fontweight="bold")

    counts = [
        len(model._market_makers),
        len(model._fundamental),
        len(model._noisy),
        len(model._hft),
        len(model._momentum),
        len(model._stoploss),
    ]
    labels = ["Mkt Maker", "Fundamental", "Noisy", "HFT", "Momentum", "Stop Loss"]
    colors = [BID_COL, FUND_COL, PRICE_COL, TRADE_COL, MOM_COL, SL_COL]

    # Filter out zero-count agents
    non_zero = [(c, l, col) for c, l, col in zip(counts, labels, colors) if c > 0]
    if non_zero:
        c_, l_, col_ = zip(*non_zero)
        wedges, texts, autotexts = ax1.pie(
            c_, labels=l_, colors=col_, autopct="%1.0f%%",
            textprops={"color": TEXT_COL, "fontsize": 7},
            wedgeprops={"edgecolor": DARK_BG, "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_color(DARK_BG)
            at.set_fontsize(7)

    ax2 = axes[1]
    apply_dark_style(ax2, "Cumulative Trade Count")
    df = model.datacollector.get_model_vars_dataframe()
    if "TradeCount" in df.columns:
        ax2.plot(df.index, df["TradeCount"], color=TRADE_COL, linewidth=1.5)
        ax2.fill_between(df.index, df["TradeCount"], color=TRADE_COL, alpha=0.2)
        for crash_t in model.crash_events:
            ax2.axvline(crash_t, color=CRASH_COL, linewidth=1.5, alpha=0.7, linestyle=":")
    ax2.set_xlabel("Step", color=TEXT_COL, fontsize=8)
    ax2.set_ylabel("Trades", color=TEXT_COL, fontsize=8)
    return fig


# solara components
@solara.component
def ControlPanel():
    with solara.Column(style={"background": "#161b22", "borderRadius": "8px",
                              "padding": "16px", "gap": "8px"}):

        solara.Text("⚡ Flash Crash ABM",
                    style={"color": "#58a6ff", "fontWeight": "bold",
                           "fontSize": "16px", "marginBottom": "8px"})

        # run controls
        with solara.Row(style={"gap": "6px", "marginBottom": "4px", "flexWrap": "wrap"}):
            def on_reset():
                model_state.set(make_model())
                step_count.set(0)
                running.set(False)

            def on_step():
                m = model_state.value
                if m is not None:
                    m.step()
                    step_count.set(step_count.value + 1)

            def on_step10():
                m = model_state.value
                if m is not None:
                    for _ in range(10):
                        m.step()
                    step_count.set(step_count.value + 10)

            def on_step50():
                m = model_state.value
                if m is not None:
                    for _ in range(50):
                        m.step()
                    step_count.set(step_count.value + 50)

            def on_run_toggle():
                running.set(not running.value)

            solara.Button("↺ Reset", on_click=on_reset,
                          style={"background": "#21262d", "color": "#e6edf3",
                                 "border": "1px solid #30363d", "borderRadius": "6px"})
            solara.Button("+1", on_click=on_step,
                          style={"background": "#21262d", "color": "#e6edf3",
                                 "border": "1px solid #30363d", "borderRadius": "6px"})
            solara.Button("+10", on_click=on_step10,
                          style={"background": "#21262d", "color": "#e6edf3",
                                 "border": "1px solid #30363d", "borderRadius": "6px"})
            solara.Button("+50", on_click=on_step50,
                          style={"background": "#21262d", "color": "#e6edf3",
                                 "border": "1px solid #30363d", "borderRadius": "6px"})

        with solara.Row(style={"gap": "6px", "marginBottom": "8px"}):
            label = "⏸ Pause" if running.value else "▷ Run"
            solara.Button(label, on_click=on_run_toggle,
                          style={"background": "#1f6feb" if not running.value else "#388bfd",
                                 "color": "#ffffff", "borderRadius": "6px", "width": "100%"})

        solara.Text(f"Step: {step_count.value}",
                    style={"color": "#8b949e", "fontSize": "12px"})

        # manual flash crash trigger
        solara.Text("── Flash Crash ──",
                    style={"color": "#ff4500", "fontSize": "11px", "marginTop": "8px"})

        m = model_state.value
        crash_status = ""
        if m is not None:
            if m.active_crash_ticks > 0:
                crash_status = f"⚠ CRASH ACTIVE ({m.active_crash_ticks} ticks left)"
            elif m.crash_cooldown > 0:
                crash_status = f"Cooldown: {m.crash_cooldown} ticks"
            else:
                crash_status = f"Events: {len(m.crash_events)}"
        solara.Text(crash_status,
                    style={"color": CRASH_COL if (m and m.active_crash_ticks > 0) else "#8b949e",
                           "fontSize": "11px", "fontWeight": "bold"})

        def on_trigger_crash():
            m = model_state.value
            if m is not None:
                m.trigger_manual_crash()
                step_count.set(step_count.value)  # force re-render

        solara.Button("💥 Trigger Flash Crash", on_click=on_trigger_crash,
                      style={"background": "#8b0000" if (m and m.active_crash_ticks > 0) else "#3d0000",
                             "color": "#ff6b6b", "border": "1px solid #ff4500",
                             "borderRadius": "6px", "fontWeight": "bold"})

        solara.SliderFloat("Crash Probability", value=crash_prob,
                           min=0.0, max=0.02, step=0.001)

        # agent counts
        solara.Text("── Agent Counts ──",
                    style={"color": "#8b949e", "fontSize": "11px", "marginTop": "8px"})
        solara.SliderInt("Market Makers", value=n_market_maker, min=0, max=20)
        solara.SliderInt("Noisy Agents", value=n_noisy, min=0, max=20)
        solara.SliderInt("Fundamental", value=n_fundamental, min=0, max=10)
        solara.SliderInt("HFT Agents", value=n_hft, min=0, max=10)
        solara.SliderInt("Momentum", value=n_momentum, min=0, max=10)
        solara.SliderInt("Stop Loss", value=n_stoploss, min=0, max=10)

        # market parameters
        solara.Text("── Market Parameters ──",
                    style={"color": "#8b949e", "fontSize": "11px", "marginTop": "8px"})
        solara.SliderFloat("Fundamental Vol", value=fundamental_vol,
                           min=0.01, max=2.0, step=0.01)
        solara.SliderFloat("MM Spread", value=mm_spread,
                           min=0.1, max=3.0, step=0.05)

        # live statistics
        if m is not None:
            solara.Text("── Live Stats ──",
                        style={"color": "#8b949e", "fontSize": "11px", "marginTop": "8px"})
            mid = m.lob.midPrice()
            spread = m.lob.spread()
            fund = float(m.market.fundamentalPrice)
            trades = len(m.lob.trades)
            stats = [
                ("Mid Price", f"{mid:.2f}" if mid else "—"),
                ("Fundamental", f"{fund:.2f}"),
                ("Spread", f"{spread:.4f}" if spread else "—"),
                ("Total Trades", str(trades)),
                ("Bid Depth", str(m.lob.depth("buy", 10))),
                ("Ask Depth", str(m.lob.depth("sell", 10))),
                ("Crash Events", str(len(m.crash_events))),
            ]
            for label, val in stats:
                with solara.Row(style={"justifyContent": "space-between"}):
                    solara.Text(label, style={"color": "#8b949e", "fontSize": "11px"})
                    solara.Text(val, style={"color": "#e6edf3", "fontSize": "11px",
                                            "fontWeight": "bold"})


@solara.component
def ChartPanel():
    m = model_state.value
    if m is None:
        with solara.Column(style={"alignItems": "center", "justifyContent": "center",
                                  "height": "400px"}):
            solara.Text("Click ↺ Reset to initialise the model",
                        style={"color": "#8b949e", "fontSize": "14px"})
        return

    _ = step_count.value  # subscribe so panel re-renders on every step

    with solara.Column(style={"gap": "16px"}):
        with solara.Row(style={"gap": "16px", "alignItems": "flex-start"}):
            with solara.Column(style={"flex": "1"}):
                fig_ob = render_order_book(m)
                solara.FigureMatplotlib(fig_ob)
                plt.close(fig_ob)

                fig_depth = render_depth_chart(m)
                solara.FigureMatplotlib(fig_depth)
                plt.close(fig_depth)

            with solara.Column(style={"flex": "1.4"}):
                fig_price = render_price_chart(m)
                solara.FigureMatplotlib(fig_price)
                plt.close(fig_price)

                fig_agents = render_agent_activity(m)
                solara.FigureMatplotlib(fig_agents)
                plt.close(fig_agents)


@solara.component
def Page():
    solara.Style("""
        body { background-color: #0d1117; margin: 0;
               font-family: 'Courier New', monospace; }
    """)

    async def auto_stepper():
        while True:
            await asyncio.sleep(0.3)
            if running.value and model_state.value is not None:
                model_state.value.step()
                step_count.set(step_count.value + 1)

    solara.lab.use_task(auto_stepper, dependencies=[])

    with solara.Row(style={"background": "#161b22", "borderBottom": "1px solid #21262d",
                           "padding": "12px 24px", "alignItems": "center", "gap": "12px"}):
        solara.Text("📈 Flash Crash ABM Simulator",
                    style={"color": "#e6edf3", "fontWeight": "bold", "fontSize": "18px"})
        solara.Text("Mesa + Solara  ·  with Manual Crash Trigger",
                    style={"color": "#8b949e", "fontSize": "13px"})

    with solara.Row(style={"padding": "16px", "gap": "16px", "alignItems": "flex-start",
                           "background": "#0d1117",
                           "minHeight": "calc(100vh - 60px)"}):
        with solara.Column(style={"width": "270px", "flexShrink": "0"}):
            ControlPanel()
        with solara.Column(style={"flex": "1", "minWidth": "0"}):
            ChartPanel()
