import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from vidya.scraper import EbayScraperError, scrape_ebay
from vidya.utils import ExchangeRateService, calculate_statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

exchange_service = ExchangeRateService()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready() -> None:
    logger.info(f"Logged in as {bot.user}")


@bot.command(name="ebay")
async def ebay_command(ctx: commands.Context, *, query: str) -> None:
    async with ctx.typing():
        try:
            status_message = await ctx.send(
                f"🔍 Fetching completed eBay listings for: {query}..."
            )

            listings = await scrape_ebay(query)
            if not listings:
                await status_message.edit(content="No listings found for your query.")
                return

            stats = await calculate_statistics(
                [listing.price for listing in listings], exchange_service
            )

            url = f"https://www.ebay.com/sch/i.html?_nkw={query.replace(' ', '+')}"

            response = (
                f"**{query} eBay Stats:**\n"
                f"**URL:** {url}\n"
                f"📉 Min Price: ${stats.min_price:.2f} CAD\n"
                f"🔹 Q1 (25th Percentile): ${stats.q1_price:.2f} CAD\n"
                f"🔸 Median (50th Percentile): ${stats.median_price:.2f} CAD\n"
                f"🔹 Q3 (75th Percentile): ${stats.q3_price:.2f} CAD\n"
                f"📈 Max Price: ${stats.max_price:.2f} CAD\n"
                f"🔢 Total Listings: {stats.total_listings}"
            )

            await status_message.edit(content=response)

        except EbayScraperError as e:
            logger.error(f"Scraping error: {e}")
            await ctx.send(f"❌ Error fetching eBay data: {e!s}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=e)
            await ctx.send("❌ An unexpected error occurred. Please try again later.")


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN not found in environment variables")

    bot.run(token)


if __name__ == "__main__":
    main()
