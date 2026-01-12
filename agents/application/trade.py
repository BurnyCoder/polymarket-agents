from agents.application.executor import Executor as Agent
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket

import shutil
import json
import os
import re
import httpx
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

    def get_recommendations(self, limit: int = 10, min_edge: float = 15.0) -> list:
        """
        Get trading recommendations by comparing AI predictions to market prices.

        This method bypasses the RAG pipeline and directly:
        1. Fetches active markets from Gamma API
        2. Gets AI superforecaster predictions for each
        3. Compares predictions to market prices to find edge
        4. Saves results to ./results/ folder

        Args:
            limit: Maximum number of markets to analyze (default: 10)
            min_edge: Minimum edge percentage for BUY signal (default: 15.0)

        Returns:
            List of recommendation dictionaries
        """
        print(f"Fetching markets from Gamma API...")

        # Fetch active markets directly
        response = httpx.get(
            "https://gamma-api.polymarket.com/markets",
            params={"closed": "false", "active": "true", "limit": limit * 2}
        )
        markets_data = response.json()

        # Filter to markets with valid data
        valid_markets = []
        for m in markets_data:
            if m.get("question") and m.get("outcomePrices"):
                try:
                    prices = json.loads(m["outcomePrices"])
                    if len(prices) >= 1:
                        valid_markets.append(m)
                except:
                    pass

        valid_markets = valid_markets[:limit]
        print(f"Found {len(valid_markets)} valid markets to analyze")

        recommendations = []

        for i, market in enumerate(valid_markets):
            market_id = market.get("id", "unknown")
            question = market.get("question", "Unknown")
            event_title = market.get("groupItemTitle", question)

            try:
                prices = json.loads(market["outcomePrices"])
                market_yes_price = float(prices[0]) * 100  # Convert to percentage
            except:
                market_yes_price = 0.0

            print(f"\n[{i+1}/{len(valid_markets)}] Analyzing: {question[:60]}...")

            try:
                # Get AI prediction
                prediction = self.agent.get_superforecast(
                    event_title=event_title,
                    market_question=question,
                    outcome="Yes"
                )

                # Parse prediction probability
                ai_prob = self._parse_probability(prediction)

                # Calculate edge
                edge = ai_prob - market_yes_price

                # Determine signal
                if edge > min_edge:
                    signal = "BUY YES"
                elif edge < -min_edge:
                    signal = "BUY NO"
                else:
                    signal = "HOLD"

                rec = {
                    "market_id": market_id,
                    "question": question,
                    "event_title": event_title,
                    "market_yes_price": market_yes_price,
                    "ai_prediction": ai_prob,
                    "edge": round(edge, 2),
                    "signal": signal,
                    "raw_prediction": prediction
                }
                recommendations.append(rec)

                print(f"   Market: {market_yes_price:.1f}% | AI: {ai_prob:.1f}% | Edge: {edge:+.1f}% | {signal}")

            except Exception as e:
                print(f"   Error: {e}")
                continue

        # Sort by absolute edge
        recommendations.sort(key=lambda x: abs(x["edge"]), reverse=True)

        # Save results
        result_data = {
            "timestamp": datetime.now().isoformat(),
            "total_markets_analyzed": len(recommendations),
            "min_edge_threshold": min_edge,
            "recommendations": recommendations
        }

        filepath = save_result("recommendations", result_data, {"limit": limit, "min_edge": min_edge})

        print(f"\n{'='*60}")
        print(f"RECOMMENDATIONS SUMMARY ({len(recommendations)} markets)")
        print(f"{'='*60}")

        buy_signals = [r for r in recommendations if r["signal"].startswith("BUY")]
        for rec in buy_signals[:5]:
            print(f"\n{rec['signal']}: {rec['question'][:50]}...")
            print(f"   Market: {rec['market_yes_price']:.1f}% | AI: {rec['ai_prediction']:.1f}% | Edge: {rec['edge']:+.1f}%")

        return recommendations

    def _parse_probability(self, prediction: str) -> float:
        """Parse probability from AI prediction text."""
        # Look for likelihood pattern like "likelihood `0.75`" or "likelihood `30.5%`"
        likelihood_match = re.search(r'likelihood\s*`?(0?\.\d+|[0-9]{1,2}(?:\.\d+)?%?)`?', prediction, re.IGNORECASE)
        if likelihood_match:
            val_str = likelihood_match.group(1).rstrip('%')
            val = float(val_str)
            if val <= 1.0:
                return val * 100
            return val

        # Fallback: look for percentage pattern
        pct_match = re.search(r'(\d{1,2}(?:\.\d+)?)\s*%', prediction)
        if pct_match:
            return float(pct_match.group(1))

        # Fallback: look for decimal between 0 and 1
        dec_match = re.search(r'\b(0\.\d+)\b', prediction)
        if dec_match:
            return float(dec_match.group(1)) * 100

        return 50.0  # Default if parsing fails


if __name__ == "__main__":
    import sys
    t = Trader()

    if len(sys.argv) > 1 and sys.argv[1] == "recommendations":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        t.get_recommendations(limit=limit)
    else:
        t.one_best_trade()
