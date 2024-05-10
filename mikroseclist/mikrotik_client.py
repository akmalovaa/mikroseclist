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
            logger.info(f"Success connection to host: {self.host}")
        except Exception as e:
            logger.error("Exception:", str(e))

    def disconnect(self):
        if self.connection:
            self.connection.disconnect()

    def fetch_address_list(self) -> list:
        logger.info(f"Fetch firewall address list: {settings.address_list_name}")
        block_list: list = []
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            list_address = mikrotik_api.get_resource("/ip/firewall/address-list")
            mikrotik_block_list = list_address.get(list=settings.address_list_name)
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
                        list=settings.address_list_name,
                        address=ip_address,
                        comment=settings.address_list_comment,
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

    def remove_file(self, file_name: str) -> None:
        """Before upload remove old file, else failure = file already exists"""
        logger.debug(f"remove file {file_name}")
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            mikrotik_files = mikrotik_api.get_resource("/file")
            for file in mikrotik_files.get():
                if file["name"] == file_name:
                    file_id = file["id"]
                    logger.debug(f"Remove file {file_name} id: {file_id}")
                    try:
                        mikrotik_files.remove(id=file_id)
                    except (
                        routeros_api.exceptions.RouterOsApiConnectionError
                    ) as routerError:
                        logger.error(routerError)
                    return
            logger.debug(f"Not found file {file_name}")
        self.disconnect()
        return

    def upload_file(self, file_name: str = "upload.txt", content: str = "") -> None:
        """upload a file with the contents, there are limits files should not be large about 400kb"""
        logger.debug(f"upload file {file_name}")
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            mikrotik_files = mikrotik_api.get_resource("/file")
            try:
                mikrotik_files.add(name=file_name, contents=content)
            except Exception as e:
                logger.error(e)
        self.disconnect()
        return

    def import_from_file(self, file_name: str) -> None:
        """import from a file, like RouterOS command -> import file-name=test.rsc"""
        logger.debug(f"import file-name={file_name}")
        if not self.connection:
            self.connect()

        if self.connection:
            mikrotik_api = self.connection.get_api()
            try:
                mikrotik_api.get_binary_resource("/").call(
                    "import", {"file-name": file_name.encode("utf-8")}
                )
            except Exception as e:
                logger.error(e)
        self.disconnect()
        return
