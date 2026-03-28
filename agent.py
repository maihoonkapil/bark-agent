import asyncio
import json
import logging
from scraper import BarkScraper
from ai_brain import process_lead
from models import LeadOutput
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_agent():
    results: list[LeadOutput] = []

    async with BarkScraper() as scraper:
        await scraper.login()
        leads = await scraper.get_leads(max_leads=20)

    logger.info(f"Processing {len(leads)} leads through AI brain...")
    for lead in leads:
        try:
            output = process_lead(lead)
            results.append(output)
        except Exception as e:
            logger.error(f"Failed to process lead: {e}")

    # Persist results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"leads_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump([r.model_dump() for r in results], f, indent=2)

    # Summary
    high_value = [r for r in results if r.scored_lead.score > 0.8]
    logger.info(f"\n{'='*50}")
    logger.info(f"Total leads processed: {len(results)}")
    logger.info(f"High-value leads (score > 0.8): {len(high_value)}")
    logger.info(f"Results saved to: {output_file}")

    for r in high_value:
        print(f"\n[SCORE: {r.scored_lead.score:.2f}] {r.scored_lead.lead.title}")
        print(f"Signals: {', '.join(r.scored_lead.key_signals)}")
        print(f"\nPITCH:\n{r.pitch}\n")
        print("—" * 50)


if __name__ == "__main__":
    asyncio.run(run_agent())