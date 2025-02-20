import logging
import os
from io import BytesIO

import discord
import matplotlib.pyplot as plt
from discord.ext import commands
from dotenv import load_dotenv

from vidya.moderation import ContentModerator
from vidya.scraper import EbayScraperError, build_ebay_url, scrape_ebay
from vidya.utils import ExchangeRateService, calculate_statistics

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
load_dotenv()

exchange_service = ExchangeRateService()
moderator = ContentModerator()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def create_price_visualization(prices: list[float], exchange_rate: float) -> BytesIO:
    cad_prices = [price * exchange_rate for price in prices]

    plt.figure(figsize=(10, 6))
    plt.boxplot(cad_prices, vert=True, labels=["Prices"])

    plt.scatter([1] * len(cad_prices), cad_prices, alpha=0.4, color="red", zorder=2)

    plt.title("Price Distribution (CAD)")
    plt.ylabel("Price (CAD)")
    plt.grid(True, alpha=0.3, axis="y")

    plt.xticks(rotation=0)

    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.2f}"))

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
    plt.close()
    buffer.seek(0)
    return buffer


@bot.event
async def on_ready() -> None:
    logger.info(f"Logged in as {bot.user}")
    logger.info(f"Bot is ready in {len(bot.guilds)} guilds")


async def handle_moderation(ctx: commands.Context, query: str) -> bool:
    result = await moderator.check_content(query, ctx.author.id)
    if not result.allowed:
        if result.message:
            await ctx.send(result.message)
            logger.info(
                f"Moderated query from {ctx.author.id}: {query}"
                f" - Reason: {result.reason}"
            )
        return False
    return True


@bot.command(name="ebay")
async def ebay_command(ctx: commands.Context, *, query: str) -> None:
    if not query.strip():
        await ctx.send("❌ Please provide a search query.")
        return

    if not await handle_moderation(ctx, query):
        return

    async with ctx.typing():
        try:
            status_message = await ctx.send(
                f"🔍 Fetching completed eBay listings for: {query}..."
            )

            url = build_ebay_url(query)
            listings = await scrape_ebay(query)

            if not listings:
                await status_message.delete()
                await ctx.send("📭 No listings found for your query.")
                return

            prices = [listing.price for listing in listings]
            exchange_rate = await exchange_service.get_rate()
            stats = await calculate_statistics(prices, exchange_service)

            viz_buffer = create_price_visualization(prices, exchange_rate)
            viz_file = discord.File(viz_buffer, filename="price_distribution.png")

            response = (
                f"**{query} eBay Stats:**\n"
                f"**URL:** {url}\n"
                f"📊 **Price Statistics (CAD)**\n"
                f"📉 Lowest: ${stats.min_price:.2f}\n"
                f"🔹 25th Percentile: ${stats.q1_price:.2f}\n"
                f"📊 Median: ${stats.median_price:.2f}\n"
                f"🔹 75th Percentile: ${stats.q3_price:.2f}\n"
                f"📈 Highest: ${stats.max_price:.2f}\n"
                f"🔢 Total Listings: {stats.total_listings}"
            )

            await status_message.delete()
            await ctx.send(content=response, file=viz_file)
            logger.info(
                f"Successfully processed query: {query} with "
                f"{stats.total_listings} results"
            )

        except EbayScraperError as e:
            logger.error(f"Scraping error for query '{query}': {e}")
            await ctx.send(f"❌ Error fetching eBay data: {e!s}")
        except Exception as e:
            logger.error(
                f"Unexpected error processing query '{query}': {e}", exc_info=True
            )
            await ctx.send("❌ An unexpected error occurred. Please try again later.")


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN not found in environment variables")

    logger.info("Starting bot...")
    bot.run(token)


if __name__ == "__main__":
    main()
