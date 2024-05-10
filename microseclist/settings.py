import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    mikrotik_host: str  = '192.168.88.1'
    mikrotik_user: str  = 'admin'
    mikrotik_password: str ='12345'
    address_list_name: str = "block"
    address_list_comment: str = "mikrotik-sync-list"
    blocklist_url: str = 'http://blocklist:41412/security/blocklist?ipv4only'
    blocklist_filename: str = "blocklist.txt"
    sync_interval_min: int = 5
    log_level: str = "INFO"


settings: Settings = Settings()
