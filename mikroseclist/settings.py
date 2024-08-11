import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    log_level: str = "INFO"
    mikrotik_host: str  = '192.168.88.1'
    mikrotik_user: str  = 'admin'
    mikrotik_password: str ='12345'
    mikrotik_address_list_name: str = "block"
    mikrotik_address_list_comment: str = "github.com/akmalovaa/mikroseclist"
    mikrotik_log_message: bool = True  # mikrotik log notification of the start sync
    blocklist_url: str = 'http://blocklist:41412/security/blocklist?ipv4only'
    blocklist_filename: str = "blocklist.txt"
    sync_interval_min: int = 30


settings: Settings = Settings()
