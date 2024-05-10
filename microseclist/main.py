import sys
import time

import requests
from loguru import logger
from schedule import every, repeat, run_pending

from microseclist.mikrotik_client import MikroTikClient
from microseclist.settings import settings

logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:DD.MM.YY HH:mm:ss} {level} {message}")

mikrotik = MikroTikClient(settings.mikrotik_host, settings.mikrotik_user, settings.mikrotik_password)


def download_blocklist_file() -> None:
    logger.debug(f"Get request to url: {settings.blocklist_url}")
    try:
        response = requests.get(settings.blocklist_url)
    except requests.exceptions.RequestException as e:
        logger.error(f"Get request to url:{settings.blocklist_url} exceptions: {e}")
        sys.exit()
    if response.status_code == 200:
        with open(settings.blocklist_filename, "wb") as file:
            file.write(response.content)
        logger.info(f"Save crowdsec blocklist to file: {settings.blocklist_filename}")
    else:
        logger.error("Addresses list could not be downloaded")
    return


def fetch_crowdsec_block_list() -> list:
    logger.debug(f"Fetch data from file: {settings.blocklist_filename}")
    block_list: list = []
    download_blocklist_file()
    with open(settings.blocklist_filename, "r") as file:
        for line in file:
            block_list.append(line.strip())  
    return block_list


def upload_blocklist_file(crowdsec_block_list: list) -> None:
    """With a large list of addresses for initial synchronization, it will be faster if you send the entire file"""
    logger.info(f"Start upload block list addresses via file")
    temp_ip_count: int = 0
    all_ip_count: int = len(crowdsec_block_list)
    content: str = ""
    for address in crowdsec_block_list:
        if temp_ip_count >= 500 or all_ip_count == 1:
            mikrotik.remove_file(settings.blocklist_filename)
            mikrotik.upload_file(settings.blocklist_filename, content)
            mikrotik.import_from_file(settings.blocklist_filename)
            content = ""
            temp_ip_count = 0
        line = (
            f"/ip firewall address-list add list={settings.address_list_name} "
            f"address={address} "
            f"comment={settings.address_list_comment}" + "\n"
        )
        content += line
        temp_ip_count += 1
        all_ip_count -= 1


def sync_addres_list() -> None:
    mikrotik_block_list: list  = mikrotik.fetch_address_list()
    crowdsec_block_list: list = fetch_crowdsec_block_list()
    mikrotik_add_list:list = []
    mikrotik_delete_list:list = []
    # Compare lists and update differences
    difference = set(mikrotik_block_list) ^ set(crowdsec_block_list)
    if difference:
        for item in difference:
            if item in mikrotik_block_list:
                logger.debug(f"Mikrotik delete address: {item}")
                mikrotik_delete_list.append(item)
            else:
                logger.debug(f"Mikrotik add address: {item}")
                mikrotik_add_list.append(item)
    else:
        logger.info(f"Nothing update, total count crowdsec addresses {len(crowdsec_block_list)}")
        return
    logger.info(
        f"Starting synchronization, total count crowdsec addresses {len(crowdsec_block_list)}"
    )
    if len(mikrotik_delete_list) > 1000 or len(mikrotik_add_list) > 3000:
        upload_blocklist_file(crowdsec_block_list)
        return
    if mikrotik_delete_list:
        mikrotik.delete_address_list(mikrotik_delete_list)
    if mikrotik_add_list:
        mikrotik.add_address_list(mikrotik_add_list)


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
    logger.info("Mikrotik firewall address list sync started")
    sync_addres_list()
    run_scheduler()
