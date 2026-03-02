import random
from decimal import Decimal
from src.lob_and_market.LimitOrderBook import LimitOrderBook
from src.lob_and_market.Market import Market
from src.Agents.MarketMakerAgent import MarketMakerAgent
from src.Agents.NoisyAgent import NoisyAgent
from src.Agents.FundamentalAgent import FundamentalAgent
from src.Agents.HFTAgent import HFTAgent


def simulationRunner(
    numTicks=5000,
    marketMakerAmount=15,
    seed=None,
    noisyAmount=7,
    fundamentalAmount=3,
    HFTAmount=2,
    printEvery=20,
):
    if seed is not None:
        random.seed(seed)

    lob = LimitOrderBook()
    market = Market(lob)

    marketMakers = [
    MarketMakerAgent(
        "MM_" + str(i),
        cash=5000,
        quantity=50,
        spread=0.7,
        maxTradeNum=7,
        inventoryAim=50,
        inventoryCoefficient=0.001,
        inventoryCap=500,
        movingWindowForPrices=random.randint(95, 105),
        withdrawTicks=random.randint(30, 35),
        durationForWithdrawal=10,
        withdrawCooldownTicks=random.randint(80, 120),
        withdrawalMinDepth=35,          
        inventoryPressureTicks=5,       
        checkDepth=10           
    )
    for i in range(marketMakerAmount)
]

    noisyAgents = [
        NoisyAgent(
            "NOISE_" + str(i),
            cash=5000,
            quantity=50,
            tradeProbability=0.5,
            maxTradeNum=4,
        )
        for i in range(noisyAmount)
    ]

    fundamentalAgents = [
        FundamentalAgent(
            "FUND_" + str(i),
            cash=5000,
            quantity=50,
            maxTradeSize=3,
        )
        for i in range(fundamentalAmount)
    ]
    # Danny add ur agents 
    HFTs = [
        HFTAgent(
            "HFT_" + str(i),
            cash=5000,
            quantity=5,
            maxTradeNum=3,
            tradeProbability=1.0,
            inventoryCap=40,
            bufferBeforeReachingCap=4,
        )
        for i in range(HFTAmount)
    ]

    # Danny add ur agents to the below line
    allAgentsButMarketMaker = noisyAgents + fundamentalAgents + HFTs

    agents = marketMakers + allAgentsButMarketMaker

    crashDuration = 25

    crashProb = 0.002

    noCrashesForFirstNTicks = 250

    waitTillNextCrash = 350

    activeCrashTicks = 0

    crashCooldown = 0

    bidLiquidityDepthMeasure = 25    

    shockAmount = Decimal("25") 

    basePressure = 80              

    maxSell = Decimal("0.98") 
    
    perTickSellSweep = 6             

    for t in range(1, numTicks + 1):
        market.updateFundamental()

        random.shuffle(agents)
   
        if marketMakers:
            m = agents.index(random.choice(marketMakers))
            agents[0],agents[m] = agents[m], agents[0]

       
        for a in agents:
            a.step(market, lob, t)

       
        if crashCooldown> 0:
            crashCooldown -= 1
        else:
            if (
                t>= noCrashesForFirstNTicks and activeCrashTicks == 0 and lob.bestBid() is not None
                and (lob.depth("buy", levels=3) or 0) >= 20 and random.random()< crashProb
            ):
                activeCrashTicks = crashDuration
                crashCooldown = waitTillNextCrash
                print(
                    f"FLASH CRASH t={t} fundamental={float(market.fundamentalPrice):.2f}"
                )

        
        if activeCrashTicks> 0:
            if lob.bestBid() is None:
                activeCrashTicks = 0
            else:
                
                if fundamentalAgents:
                    aggressor=random.choice(fundamentalAgents)
                elif noisyAgents:
                    aggressor=random.choice(noisyAgents)
                else:
                    aggressor=random.choice(agents)

                
                for s in range(perTickSellSweep):
                    if lob.bestBid() is None:
                        
                        break

                    bidD = lob.depth("buy",levels=bidLiquidityDepthMeasure) or 0
                    availableBidAmount = sum(lob.bidQty.values())

                    if availableBidAmount<= 0:
                        availableBidAmount = bidD

                    if availableBidAmount<= 0:

                        break

                    panicSize = min( int(max(basePressure, float(shockAmount) * float(bidD))),
                    int(Decimal(availableBidAmount) * maxSell))

                    if panicSize > 0:
                        lob.submitMarketOrder("sell", panicSize, aggressor, t)

                activeCrashTicks-= 1

        market.updatePrice(t)

        if printEvery and (t% printEvery== 0):
            print(t,
                "price",
                market.price,
                "fund",
                float(market.fundamentalPrice),
                "bestBid",
                lob.bestBid(),
                "bestAsk",
                lob.bestAsk(),
                "bidDepth",
                lob.depth("buy"),
                "askDepth",
                lob.depth("sell"),
                "totalTrades",
                len(lob.trades),
            )


if __name__ == "__main__":
    simulationRunner()