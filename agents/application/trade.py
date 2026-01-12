from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket

import shutil
import json
import os
from datetime import datetime

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def save_result(command_name: str, data: any, params: dict = None) -> str:
    """Save command result to results folder with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{command_name}_{timestamp}.json"
    filepath = os.path.join(RESULTS_DIR, filename)

    result = {
        "command": command_name,
        "timestamp": datetime.now().isoformat(),
        "params": params or {},
        "data": data
    }

    with open(filepath, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Results saved to: {filepath}")
    return filepath


class Trader:
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()

    def pre_trade_logic(self) -> None:
        self.clear_local_dbs()

    def clear_local_dbs(self) -> None:
        try:
            shutil.rmtree("local_db_events")
        except:
            pass
        try:
            shutil.rmtree("local_db_markets")
        except:
            pass

    def one_best_trade(self) -> None:
        """

        one_best_trade is a strategy that evaluates all events, markets, and orderbooks

        leverages all available information sources accessible to the autonomous agent

        then executes that trade without any human intervention

        """
        trade_data = {"steps": [], "error": None}
        try:
            self.pre_trade_logic()

            events = self.polymarket.get_all_tradeable_events()
            print(f"1. FOUND {len(events)} EVENTS")
            trade_data["steps"].append({"step": 1, "action": "found_events", "count": len(events)})

            filtered_events = self.agent.filter_events_with_rag(events)
            print(f"2. FILTERED {len(filtered_events)} EVENTS")
            trade_data["steps"].append({"step": 2, "action": "filtered_events", "count": len(filtered_events)})

            markets = self.agent.map_filtered_events_to_markets(filtered_events)
            print()
            print(f"3. FOUND {len(markets)} MARKETS")
            trade_data["steps"].append({"step": 3, "action": "found_markets", "count": len(markets)})

            print()
            filtered_markets = self.agent.filter_markets(markets)
            print(f"4. FILTERED {len(filtered_markets)} MARKETS")
            trade_data["steps"].append({"step": 4, "action": "filtered_markets", "count": len(filtered_markets)})

            market = filtered_markets[0]
            best_trade = self.agent.source_best_trade(market)
            print(f"5. CALCULATED TRADE {best_trade}")
            trade_data["steps"].append({"step": 5, "action": "calculated_trade", "trade": str(best_trade)})
            trade_data["best_trade"] = str(best_trade)
            trade_data["market"] = str(market)

            amount = self.agent.format_trade_prompt_for_execution(best_trade)
            trade_data["amount"] = str(amount)
            # Please refer to TOS before uncommenting: polymarket.com/tos
            # trade = self.polymarket.execute_market_order(market, amount)
            # print(f"6. TRADED {trade}")

            save_result("one_best_trade", trade_data, {})

        except Exception as e:
            print(f"Error {e} \n \n Retrying")
            trade_data["error"] = str(e)
            save_result("one_best_trade_error", trade_data, {})
            self.one_best_trade()

    def maintain_positions(self):
        pass

    def incentive_farm(self):
        pass


if __name__ == "__main__":
    t = Trader()
    t.one_best_trade()
