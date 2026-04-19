import ipaddress
import sys
import time

import requests
from loguru import logger
from schedule import every, repeat, run_pending

from mikroseclist.mikrotik_client import MikroTikAuthError, MikroTikConnectionError, MikroTikClient
from mikroseclist.settings import settings

REQUEST_TIMEOUT = 30

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="{time:DD.MM.YY HH:mm:ss} {level} {message}",
)

mikrotik = MikroTikClient(
    settings.mikrotik_host, settings.mikrotik_user, settings.mikrotik_password
)


def download_blocklist(url: str) -> list[str]:
    logger.info(f"Fetch blocklist from url: {url}")
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.error(f"Fetch blocklist from url: {url} exceptions: {e}")
        return []
    if response.status_code != 200:
        logger.error(f"Blocklist could not be downloaded from: {url} (status {response.status_code})")
        return []
    ips = []
    for line in response.text.splitlines():
        stripped = line.strip()
        if stripped:
            try:
                network = ipaddress.ip_network(stripped, strict=False)
                if network.prefixlen == network.max_prefixlen:
                    ips.append(str(network.network_address))
                else:
                    ips.append(str(network))
            except ValueError:
                logger.warning(f"Invalid IP address found and skipped: {stripped}")
    logger.debug(f"Fetched {len(ips)} addresses from {url}")
    return ips


def fetch_block_list() -> list[str]:
    urls = [u.strip() for u in settings.blocklist_urls.split(",") if u.strip()]
    all_ips: set[str] = set()
    for url in urls:
        ips = download_blocklist(url)
        all_ips.update(ips)
    logger.info(f"Total unique addresses from {len(urls)} source(s): {len(all_ips)}")
    return list(all_ips)


def sync_addres_list() -> None:
    logger.info("Run synchronization")
    mikrotik_block_list: list = mikrotik.fetch_address_list()
    blocklist: list = fetch_block_list()
    mikrotik_add_list: list = list(set(blocklist) - set(mikrotik_block_list))
    mikrotik_delete_list: list = list(
        set(mikrotik_block_list) - set(blocklist)
    )
    if mikrotik_add_list:
        logger.debug(f"Found {len(mikrotik_add_list)} new addresses to add")
        mikrotik.add_address_list(mikrotik_add_list)
    else:
        logger.debug("No addresses found to add")
    if mikrotik_delete_list:
        logger.debug(f"Found {len(mikrotik_delete_list)} new addresses to delete")
        mikrotik.delete_address_list(mikrotik_delete_list)
    else:
        logger.debug("No addresses found to delete")
    mikrotik.disconnect()
    logger.info(
        f"Successful synchronization. Total block list addresses: {len(blocklist)}"
    )


@repeat(every(settings.sync_interval_min).minutes)
def run_sync_list() -> None:
    logger.info("sync mikrotik firewall address list")
    try:
        sync_addres_list()
    except MikroTikAuthError:
        logger.error("Exiting due to authentication failure. Check MIKROTIK_USER and MIKROTIK_PASSWORD.")
        sys.exit(1)
    except MikroTikConnectionError:
        logger.warning("Synchronization skipped due to connection error. Will retry next cycle.")


def run_scheduler() -> None:
    logger.info(
        f"Run scheduler: sync address list every {settings.sync_interval_min} minutes"
    )
    while True:
        run_pending()
        time.sleep(60)


if __name__ == "__main__":
    logger.info("Mikrotik firewall address list synchronization started")
    try:
        sync_addres_list()
    except MikroTikAuthError:
        logger.error("Exiting due to authentication failure. Check MIKROTIK_USER and MIKROTIK_PASSWORD.")
        sys.exit(1)
    except MikroTikConnectionError:
        logger.warning("Initial synchronization failed due to connection error. Will retry on schedule.")
    run_scheduler()
