import ipaddress
import sys
import time

import requests
from loguru import logger
from schedule import every, repeat, run_pending

from mikroseclist.mikrotik_client import MikroTikClient
from mikroseclist.settings import settings

logger.remove()
logger.add(
    sys.stderr,
    level=settings.log_level,
    format="{time:DD.MM.YY HH:mm:ss} {level} {message}",
)

mikrotik = MikroTikClient(
    settings.mikrotik_host, settings.mikrotik_user, settings.mikrotik_password
)


def download_blocklist_file() -> None:
    logger.info(f"Fetch blocklist from url: {settings.blocklist_url}")
    try:
        response = requests.get(settings.blocklist_url)
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Fetch blocklist from url: {settings.blocklist_url} exceptions: {e}"
        )
        sys.exit()
    if response.status_code == 200:
        with open(settings.blocklist_filename, "wb") as file:
            file.write(response.content)
        logger.debug(f"Save crowdsec blocklist to file: {settings.blocklist_filename}")
    else:
        logger.error("Addresses list could not be downloaded")
    return


def fetch_crowdsec_block_list() -> list:
    logger.debug(f"Fetch data from file: {settings.blocklist_filename}")
    block_list: list = []
    download_blocklist_file()
    with open(settings.blocklist_filename, "r") as file:
        for line in file:
            stripped_line = line.strip()
            if stripped_line:
                try:
                    ipaddress.ip_address(stripped_line)
                    block_list.append(stripped_line)
                except ValueError:
                    logger.warning(
                        f"Invalid IP address found and skipped: {stripped_line}"
                    )
    return block_list


def sync_addres_list() -> None:
    logger.info(f"Run synchronization")
    mikrotik_block_list: list = mikrotik.fetch_address_list()
    crowdsec_block_list: list = fetch_crowdsec_block_list()
    mikrotik_add_list: list = list(set(crowdsec_block_list) - set(mikrotik_block_list))
    mikrotik_delete_list: list = list(
        set(mikrotik_block_list) - set(crowdsec_block_list)
    )
    if mikrotik_add_list:
        logger.debug(f"Found {len(mikrotik_add_list)} new addresses to add")
        mikrotik.add_address_list(mikrotik_add_list)
    else:
        logger.debug(f"No addresses found to add")
    if mikrotik_delete_list:
        logger.debug(f"Found {len(mikrotik_delete_list)} new addresses to delete")
        mikrotik.delete_address_list(mikrotik_delete_list)
    else:
        logger.debug(f"No addresses found to delete")
    logger.info(
        f"Successful synchronization. Total block list addresses: {len(crowdsec_block_list)}"
    )


@repeat(every(settings.sync_interval_min).minutes)
def run_sync_list() -> None:
    logger.info("sync mikrotik firewall address list")
    sync_addres_list()


def run_scheduler() -> None:
    logger.info(
        f"Run scheduler: sync address list every {settings.sync_interval_min} minutes"
    )
    while True:
        run_pending()
        time.sleep(60)


if __name__ == "__main__":
    logger.info("Mikrotik firewall address list synchronization started")
    sync_addres_list()
    run_scheduler()
