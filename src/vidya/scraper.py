import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser, Node

logger = logging.getLogger(__name__)


@dataclass
class EbayListing:
    title: str
    price: float
    url: str | None = None


class EbayScraperError(Exception):
    pass


class RateLimitError(EbayScraperError):
    pass


class ParseError(EbayScraperError):
    pass


async def scrape_ebay(
    query: str, retries: int = 3, delay: float = 1.0
) -> list[EbayListing]:
    url = build_ebay_url(query)
    logger.info(f"Scraping eBay URL: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(retries):
            try:
                response = await client.get(url)
                response.raise_for_status()

                if "robot check" in response.text.lower():
                    raise RateLimitError("eBay robot check detected")

                return await parse_ebay_listings(response.text)

            except httpx.HTTPError as e:
                logger.error(f"HTTP error occurred: {e}")
                if attempt == retries - 1:
                    raise EbayScraperError(
                        f"Failed to fetch eBay data after {retries} attempts"
                    ) from e
                await asyncio.sleep(delay * (attempt + 1))

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise EbayScraperError(f"Unexpected error while scraping: {e!s}") from e


def build_ebay_url(query: str) -> str:
    base_url = "https://www.ebay.com/sch/i.html"
    params = {
        "_nkw": quote_plus(query),
        "LH_Complete": "1",
        "LH_Sold": "1",
        "LH_Auction": "1",
        "_sop": "1",
        "_dmd": "1",
        "LH_ItemCondition": "3000",
        "_ipg": "60",
    }
    return f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"


async def parse_ebay_listings(html_content: str) -> list[EbayListing]:
    try:
        if "Results matching fewer words" in html_content:
            html_content = html_content.split("Results matching fewer words")[0]

        tree = HTMLParser(html_content)
        listings = tree.css("li.s-item")

        parsed_listings: list[EbayListing] = []

        for item in listings:
            if listing := parse_listing(item):
                parsed_listings.append(listing)

        # first two listings are not relevant
        return parsed_listings[2:]

    except Exception as e:
        logger.error(f"Failed to parse HTML content: {e}")
        raise ParseError("Failed to parse eBay listings") from e


def parse_listing(item: Node) -> EbayListing | None:
    try:
        title_tag = item.css_first(".s-item__title")
        price_tag = item.css_first(".s-item__price")
        link_tag = item.css_first(".s-item__link")

        if not all([title_tag, price_tag]):
            return None

        title = title_tag.text(strip=True)
        price_text = price_tag.text(strip=True).replace("$", "").replace(",", "")
        url = link_tag.attributes.get("href") if link_tag else None

        try:
            price = float(price_text)
            return EbayListing(title=title, price=price, url=url)
        except ValueError:
            logger.warning(f"Failed to parse price: {price_text} for listing: {title}")
            return None

    except Exception as e:
        logger.warning(f"Failed to parse listing: {e}")
        return None
