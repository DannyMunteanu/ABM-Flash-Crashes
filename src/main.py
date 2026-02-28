import random
from src.lob_and_market.LimitOrderBook import LimitOrderBook
from src.lob_and_market.Market import Market
from src.Agents.MarketMakerAgent import MarketMakerAgent
from src.Agents.NoisyAgent import NoisyAgent
from src.Agents.FundamentalAgent import FundamentalAgent
from src.Agents.HFTAgent import HFTAgent
import matplotlib.pyplot as plt

def simulationRunner( 
    numTicks= 5000, 
    marketMakerAmount= 20,
    seed = None,
    noisyAmount=10,
    fundamentalAmount =2,
    HFTAmount=3,
    # Danny add your 2 agents and their amounts here
    printEvery=50,):

    if seed is not None:
        random.seed(seed)

    lob = LimitOrderBook()
    market = Market(lob)

    marketMakers = [
        MarketMakerAgent(
            "MM_"+str(i),
            cash= 50000,
            quantity =50,
            spread=0.4,
            maxTradeNum=20,
            inventoryAim=50,
            inventoryCoefficient=0.001,
            inventoryCap=500,
        )
        for i in range(marketMakerAmount)
    ]

    # Danny create your both your Agent Objects here 

    noisyAgents = [
        NoisyAgent(
            "NOISE_" +str(i),
            cash=50000,
            quantity=50,
            tradeProbability=0.5,
            maxTradeNum=2,
        )
        for i in range(noisyAmount)
    ]

    fundamentalAgents = [
        FundamentalAgent(
            "FUND_" + str(i),
            cash=50000,
            quantity =50000,
            maxTradeSize=3,
        )
        for i in range(fundamentalAmount)
    ]

    HFTs = [
        HFTAgent(
            "HFT_" + str(i),
            cash =50000,
            quantity=50,
            mispriceThreshold= 0.05,
            maxTradeNum=3,
            tradeProbability=1.0,
        )
        for i in range(HFTAmount)
    ]
    
    # Danny add your two agents below also as they're not market maker
    allAgentsButMarketMaker = noisyAgents+fundamentalAgents+ HFTs

    for t in range(1, numTicks + 1):
        market.updateFundamental()
        market.updatePrice(t)
    #this is for margincall
        if t == 1 and market.price is not None:
            for agent in marketMakers + allAgentsButMarketMaker:
                agent.initializeValue(market.price)
    #ends here-charis    
        for m in marketMakers:
            m.step(market, lob, t)

        for other in allAgentsButMarketMaker:
            other.step(market,lob, t)
        for agent in marketMakers + allAgentsButMarketMaker:
            agent.checkAndLiquidate(t, market.price, lob)
        
        if printEvery and (t% printEvery == 0):
            print(
                t,
                "price", market.price,
                "bestBid", lob.bestBid(),
                "bestAsk", lob.bestAsk(),
                "totalTrades", len(lob.trades),)
    plt.figure()
    plt.plot(range(len(market.priceHistory)), market.priceHistory)
    plt.plot(range(len(market.fundamentalHistory)), market.fundamentalHistory)
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.title("Market Price and Fundamental Price Over Time")
    plt.show()
if __name__ == "__main__":
    simulationRunner()