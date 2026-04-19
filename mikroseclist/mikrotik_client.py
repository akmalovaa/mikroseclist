import routeros_api
from loguru import logger

from mikroseclist.settings import settings


class MikroTikAuthError(Exception):
    pass


class MikroTikConnectionError(Exception):
    pass


class MikroTikClient:
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.connection = None
        self._api = None

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
            logger.error(f"Failed to create connection pool to {self.host}: {e}")

    def get_api(self):
        if self._api:
            return self._api
        if not self.connection:
            self.connect()
        if not self.connection:
            return None
        try:
            self._api = self.connection.get_api()
            return self._api
        except routeros_api.exceptions.RouterOsApiCommunicationError:
            logger.error(f"Authentication failed for user '{self.user}' on {self.host}")
            self.connection = None
            raise MikroTikAuthError(f"Authentication failed for user '{self.user}' on {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {e}")
            self.connection = None
            return None

    def disconnect(self):
        self._api = None
        if self.connection:
            self.connection.disconnect()

    def fetch_address_list(self) -> list:
        logger.info(
            f"Fetch firewall address list: {settings.mikrotik_address_list_name}"
        )
        block_list: list = []
        mikrotik_api = self.get_api()
        if not mikrotik_api:
            logger.error("Failed to fetch block list: Connection to MikroTik not established.")
            return block_list
        try:
            if settings.mikrotik_log_message:
                mikrotik_api.get_binary_resource("/").call(
                    "log/info",
                    {"message": b"Mikroseclist: firewall blocklist synchronization"},
                )
            list_address = mikrotik_api.get_resource("/ip/firewall/address-list")
            mikrotik_block_list = list_address.get(
                list=settings.mikrotik_address_list_name
            )
        except routeros_api.exceptions.RouterOsApiConnectionError as e:
            logger.error(f"Connection to {self.host} lost: {e}")
            self._api = None
            raise MikroTikConnectionError(f"Connection to {self.host} lost: {e}")
        for ip_address in mikrotik_block_list:
            address = ip_address.get("address")
            if address:
                block_list.append(address)
        return block_list

    def add_address_list(self, ip_addresses: list) -> None:
        logger.info(f"Start adding addresses (count): {len(ip_addresses)}")
        mikrotik_api = self.get_api()
        if not mikrotik_api:
            logger.error("Failed to add addresses: Connection to MikroTik not established.")
            return
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
            except routeros_api.exceptions.RouterOsApiConnectionError as e:
                logger.error(f"Connection to {self.host} lost while adding addresses: {e}")
                self._api = None
                raise MikroTikConnectionError(f"Connection to {self.host} lost: {e}")
        logger.info("Finish adding ip addresses")

    def delete_address_list(self, ip_addresses: list) -> None:
        """Deleting is not the fastest process, unlike other requests"""
        logger.info(f"Start removing addresses (count): {len(ip_addresses)}")
        mikrotik_api = self.get_api()
        if not mikrotik_api:
            logger.error("Failed to remove addresses: Connection to MikroTik not established.")
            return
        list_address = mikrotik_api.get_resource("/ip/firewall/address-list")
        for ip_address in ip_addresses:
            try:
                find_address = list_address.get(address=ip_address)
                fetch_id = find_address[0]["id"]
                list_address.remove(id=fetch_id)
            except routeros_api.exceptions.RouterOsApiConnectionError as e:
                logger.error(f"Connection to {self.host} lost while removing addresses: {e}")
                self._api = None
                raise MikroTikConnectionError(f"Connection to {self.host} lost: {e}")
            except Exception as e:
                logger.error(f"Cannot delete address: {ip_address}. Error: {e}")
        logger.info("Finish removing addresses")
