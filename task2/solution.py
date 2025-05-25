import asyncio
import aiohttp
from bs4 import BeautifulSoup
import csv
from collections import Counter
from typing import List, Optional, Dict, Set
import logging
from dataclasses import dataclass

# --- Configuration ---
@dataclass(frozen=True)
class ScraperConfig:
    """Configuration settings for the scraper."""
    RUSSIAN_ALPHABET: str = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    BASE_WIKI_URL: str = "https://ru.wikipedia.org"
    DEFAULT_USER_AGENT: str = 'Mozilla/5.0 (Windows NT 1.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    MAX_CONCURRENT_REQUESTS: int = 5
    REQUEST_TIMEOUT_SECONDS: int = 15
    POLITE_DELAY_SECONDS: float = 0.2
    MAX_PAGES_TO_SCRAPE: int = 250 # Default max pages, can be overridden
    LOG_LEVEL: int = logging.INFO
    LOG_FORMAT: str = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

# --- Logging Setup ---
def setup_logging(level: int, log_format: str):
    """Configures basic logging."""
    logging.basicConfig(level=level, format=log_format)

logger = logging.getLogger(__name__) # Logger for this module

class PageFetcher:
    """
Responsible for fetching HTML content from a URL asynchronously.
It uses an asyncio.Semaphore to limit concurrent requests and
includes a small polite delay.
    """
    def __init__(self, semaphore: asyncio.Semaphore, user_agent: str, polite_delay: float, timeout: int):
        """
Initializes the PageFetcher.

Args:
semaphore: An asyncio.Semaphore to control concurrency.
user_agent: The User-Agent string to use for requests.
polite_delay: Seconds to wait before making a request under semaphore.
timeout: Request timeout in seconds.
        """
        self._semaphore = semaphore
        self._headers = {'User-Agent': user_agent}
        self._polite_delay = polite_delay
        self._timeout = timeout
        self._logger = logging.getLogger(self.__class__.__name__)

    async def fetch(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """
Fetches HTML content from the given URL.

Args:
session: An aiohttp.ClientSession for making requests.
url: The URL to fetch.

Returns:
The HTML content as a string if successful, otherwise None.
        """
        self._logger.info(f"Attempting to fetch: {url}")
        try:
            async with self._semaphore:
                await asyncio.sleep(self._polite_delay)
                async with session.get(url, headers=self._headers, timeout=self._timeout) as response:
                    response.raise_for_status()
                    content = await response.text()
                    self._logger.info(f"Successfully fetched: {url} (status: {response.status})")
                    return content
        except aiohttp.ClientResponseError as e:
            self._logger.error(f"HTTP error fetching {url}: {e.status} {e.message}")
        except aiohttp.ClientError as e:
            self._logger.error(f"AIOHTTP client error fetching {url}: {type(e).__name__} - {e}")
        except asyncio.TimeoutError:
            self._logger.error(f"Timeout error fetching {url} after {self._timeout}s")
        except Exception as e:
            self._logger.exception(f"Unexpected error fetching {url}: {type(e).__name__} - {e}")
        return None

class PageParser:
    """
Responsible for parsing HTML content to extract animal names and
the URL for the next page in a Wikipedia category listing.
    """
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def extract_animal_names(self, html_content: str) -> List[str]:
        """
Extracts animal or entry names from Wikipedia category page HTML.
Targets items within 'div.mw-category-group' inside 'div#mw-pages'.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        names: List[str] = []

        mw_pages_div = soup.find('div', id='mw-pages')
        if not mw_pages_div:
            self._logger.warning("Could not find 'div#mw-pages' in HTML content.")
            return []

        category_groups = mw_pages_div.find_all('div', class_='mw-category-group')

        if not category_groups:
            self._logger.debug("No 'div.mw-category-group' found. Trying fallback to 'div.mw-category'.")
            category_content_div = mw_pages_div.find('div', class_='mw-category')
            if category_content_div:
                uls = category_content_div.find_all('ul')
                for ul_tag in uls:
                    self._extract_names_from_list_items(ul_tag.find_all('li', recursive=False), names)
            else:
                self._logger.warning("Fallback 'div.mw-category' also not found within 'div#mw-pages'.")
            return names

        for group in category_groups:
            uls = group.find_all('ul')
            for ul_tag in uls:
                self._extract_names_from_list_items(ul_tag.find_all('li', recursive=False), names)

        self._logger.debug(f"Extracted {len(names)} potential names.")
        return names

    def _extract_names_from_list_items(self, list_items: List[BeautifulSoup], names_list: List[str]):
        """Helper to extract names from a list of <li> elements."""
        for item in list_items:
            link = item.find('a', recursive=False)
            if link and link.get('title'):
                entry_name = link.get_text(strip=True)
                if entry_name:
                    names_list.append(entry_name)

    def get_next_page_url(self, html_content: str, base_url: str) -> Optional[str]:
        """
Extracts the URL for the 'next page' link from the HTML.
Avoids links within the Table of Contents.
        """
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        possible_link_texts = ['Следующая страница', 'next page']

        for link_text in possible_link_texts:
            links = soup.find_all('a', string=link_text)
            for link in links:
                href = link.get('href')
                if not href or not href.strip():
                    continue

                is_toc_link = any(
                    parent.name == 'div' and 'ts-module-Индекс_категории' in parent.get('class', [])
                    for parent in link.parents
                )
                if is_toc_link:
                    continue

                link_title = link.get('title', '')
                # Prioritize links with explicit category title or "next page" title
                if "Категория:Животные по алфавиту" in link_title or link_text in link_title:
                    self._logger.debug(f"Found 'next page' URL by title: {href}")
                    return base_url + href

                # Broader check for typical pagination parameters if title is not specific enough
                if not link_title and ("pagefrom=" in href or "after=" in href or "from=" in href):
                    self._logger.debug(f"Found 'next page' URL by href parameters: {href}")
                    return base_url + href

        self._logger.debug("No valid 'next page' URL found.")
        return None


class AnimalDataStore:
    """
Stores collected animal names and computes counts by their first letter.
    """
    def __init__(self, alphabet_chars: Set[str]):
        """
Initializes the AnimalDataStore.

Args:
alphabet_chars: A set of valid first letters to count.
        """
        self._letter_counts: Counter = Counter()
        self._alphabet_chars: Set[str] = alphabet_chars
        self._all_collected_names: Set[str] = set()
        self._logger = logging.getLogger(self.__class__.__name__)

    def add_names(self, names: List[str]):
        """
Adds a list of names to the store, updating letter counts for unique names.
        """
        newly_added_count = 0
        for name in names:
            if name and name not in self._all_collected_names:
                self._all_collected_names.add(name)
                newly_added_count +=1
                first_char = name[0].upper()
                if first_char in self._alphabet_chars:
                    self._letter_counts[first_char] += 1
        if newly_added_count > 0:
            self._logger.debug(f"Added {newly_added_count} new unique names to store.")

    def get_counts_by_letter(self) -> Dict[str, int]:
        """Returns a dictionary mapping each letter to its count."""
        return dict(self._letter_counts)

class CSVReportGenerator:
    """
Generates a CSV report from animal count data.
    """
    def __init__(self, alphabet_order: str):
        """
Initializes the CSVReportGenerator.

Args:
alphabet_order: A string defining the order of letters in the CSV.
        """
        self._alphabet_order = alphabet_order
        self._logger = logging.getLogger(self.__class__.__name__)

    def write_report(self, filepath: str, counts_data: Dict[str, int]):
        """Writes the counts to a CSV file."""
        self._logger.info(f"Writing animal counts to {filepath}...")
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                for letter in self._alphabet_order:
                    writer.writerow([letter, counts_data.get(letter, 0)])
            self._logger.info(f"Successfully wrote report to {filepath}")
        except IOError as e:
            self._logger.error(f"Error writing CSV file {filepath}: {e}")

class WikipediaAnimalScraper:
    """
Orchestrates the Wikipedia animal scraping process.
    """
    def __init__(self,
                 fetcher: PageFetcher,
                 parser: PageParser,
                 data_store: AnimalDataStore,
                 reporter: CSVReportGenerator,
                 base_wiki_url: str):
        self._fetcher = fetcher
        self._parser = parser
        self._data_store = data_store
        self._reporter = reporter
        self._base_wiki_url = base_wiki_url
        self._visited_urls: Set[str] = set()
        self._logger = logging.getLogger(self.__class__.__name__)

    async def _scrape_single_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Handles the scraping of a single page."""
        if url in self._visited_urls:
            self._logger.warning(f"URL already visited, skipping: {url}")
            return None
        self._visited_urls.add(url)

        html = await self._fetcher.fetch(session, url)
        if not html:
            return None

        animal_names = self._parser.extract_animal_names(html)
        self._data_store.add_names(animal_names)
        self._logger.info(f"Extracted {len(animal_names)} potential names from {url} (unique additions handled by store).")

        return self._parser.get_next_page_url(html, self._base_wiki_url)

    async def run(self, start_url: str, output_filepath: str, max_pages_to_scrape: int):
        """Executes the scraping process."""
        self._logger.info(f"Starting asynchronous animal scraping from: {start_url}")

        async with aiohttp.ClientSession() as session:
            current_url: Optional[str] = start_url
            pages_scraped_count = 0

            while current_url and pages_scraped_count < max_pages_to_scrape:
                self._logger.info(f"--- Processing page {pages_scraped_count + 1} (URL: {current_url}) ---")
                next_page_url = await self._scrape_single_page(session, current_url)

                if current_url == next_page_url:
                    self._logger.warning(f"Next page URL is the same as current ({current_url}). Stopping to prevent loop.")
                    break

                current_url = next_page_url
                pages_scraped_count += 1

                if not current_url:
                    self._logger.info("No 'next page' link found or processed. Ending scrape.")
                    break

            if pages_scraped_count >= max_pages_to_scrape:
                self._logger.info(f"Reached maximum limit of {max_pages_to_scrape} pages. Stopping.")

        final_counts = self._data_store.get_counts_by_letter()
        self._reporter.write_report(output_filepath, final_counts)

        self._logger.info("Scraping process finished.")
        self._logger.info("Summary of counts (also in CSV):")
        for letter_char in self._reporter._alphabet_order: # Accessing from reporter instance
            count = final_counts.get(letter_char, 0)
            if count > 0:
                self._logger.info(f"{letter_char},{count}")

async def main_run_scraper():
    """Sets up dependencies and initiates the WikipediaAnimalScraper."""
    config = ScraperConfig()
    setup_logging(config.LOG_LEVEL, config.LOG_FORMAT)

    scraper_semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

    page_fetcher_instance = PageFetcher(
        semaphore=scraper_semaphore,
        user_agent=config.DEFAULT_USER_AGENT,
        polite_delay=config.POLITE_DELAY_SECONDS,
        timeout=config.REQUEST_TIMEOUT_SECONDS
    )
    page_parser_instance = PageParser()
    animal_data_store_instance = AnimalDataStore(alphabet_chars=set(config.RUSSIAN_ALPHABET))
    csv_reporter_instance = CSVReportGenerator(alphabet_order=config.RUSSIAN_ALPHABET)

    scraper = WikipediaAnimalScraper(
        fetcher=page_fetcher_instance,
        parser=page_parser_instance,
        data_store=animal_data_store_instance,
        reporter=csv_reporter_instance,
        base_wiki_url=config.BASE_WIKI_URL
    )

    initial_url = "https://ru.wikipedia.org/wiki/Категория:Животные_по_алфавиту"
    output_csv_file = 'beasts.csv'

    await scraper.run(
        start_url=initial_url,
        output_filepath=output_csv_file,
        max_pages_to_scrape=config.MAX_PAGES_TO_SCRAPE
    )

if __name__ == '__main__':
    config = ScraperConfig() # For initial print statements
    logger.info(f"Max concurrent requests: {config.MAX_CONCURRENT_REQUESTS}")
    logger.info(f"Request timeout: {config.REQUEST_TIMEOUT_SECONDS}s")
    logger.info("------------------------------------")

    asyncio.run(main_run_scraper())

    logger.info("Script execution finished.")
