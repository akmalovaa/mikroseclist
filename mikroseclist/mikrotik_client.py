import routeros_api
from loguru import logger

from mikroseclist.settings import settings


class MikroTikClient:
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        try:
            self.connection = routeros_api.RouterOsApiPool(
                self.host,
                username=self.user,
                password=self.password,
                use_ssl=True,
                ssl_verify=False,
                plaintext_login=True,
            )
            logger.info(f"Start connection to host: {self.host}")
        except Exception as e:
            logger.error("Exception:", str(e))

    def disconnect(self):
        if self.connection:
            self.connection.disconnect()

    def fetch_address_list(self) -> list:
        logger.info(
            f"Fetch firewall address list: {settings.mikrotik_address_list_name}"
        )
        block_list: list = []
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            if settings.mikrotik_log_message:
                mikrotik_api.get_binary_resource("/").call(
                    "log/info",
                    {"message": b"Mikroseclist: firewall blocklist synchronization"},
                )
            list_address = mikrotik_api.get_resource("/ip/firewall/address-list")
            mikrotik_block_list = list_address.get(
                list=settings.mikrotik_address_list_name
            )
            for ip_address in mikrotik_block_list:
                address = ip_address.get("address")
                if address:
                    block_list.append(address)
        else:
            logger.error(
                "Failed to fetch block list: Connection to MikroTik not established."
            )
        self.disconnect()
        return block_list

    def add_address_list(self, ip_addresses: list) -> None:
        logger.info(f"Start adding addresses (count): {len(ip_addresses)}")
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            list_address = mikrotik_api.get_resource("/ip/firewall/address-list")
            for ip_address in ip_addresses:
                try:
                    list_address.add(
                        list=settings.mikrotik_address_list_name,
                        address=ip_address,
                        comment=settings.mikrotik_address_list_comment,
                    )
                except routeros_api.exceptions.RouterOsApiCommunicationError as roteros_error:
                    logger.error(f"{ip_address=} already have such entry")
                    logger.error(roteros_error)
        else:
            logger.error(
                "Failed to add addresses: Connection to MikroTik not established."
            )

        self.disconnect()
        logger.info("Finish adding ip addresses")

    def delete_address_list(self, ip_addresses: list) -> None:
        """Deleting is not the fastest process, unlike other requests"""
        logger.info(f"Start removing addresses (count): {len(ip_addresses)}")
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            list_address = mikrotik_api.get_resource("/ip/firewall/address-list")
            for ip_address in ip_addresses:
                try:
                    find_address = list_address.get(address=ip_address)
                    fetch_id = find_address[0]["id"]
                    list_address.remove(id=fetch_id)
                except Exception as e:
                    logger.error(f"Cannot delete address: {ip_address}. Error: {e}")
                    logger.error(e)
        else:
            logger.error(
                "Failed to remove addresses: Connection to MikroTik not established."
            )

        self.disconnect()
        logger.info("Finish removing addresses")
