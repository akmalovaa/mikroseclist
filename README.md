# MikroSecList

## Mikrotik + CrowdSec block lists sync

This app constantly synchronizes and updates the firewall address list in mikrotik.

Actual dangerous IP addresses will already be in the blocked list

[CrowdSec Blocklist mirror](https://docs.crowdsec.net/u/bouncers/blocklist-mirror/#installation/)

Allows you to use a list of IP addresses to add

*`config.yml`*
```yaml | code
blocklists:
  format: mikrotik
```
Output lines for mikrotik, format is `/ip|/ipv6 firewall address-list add list={list_name} address={ip} comment="{scenario} for {duration}"`

The list of dangerous IP addresses is very large ~ 25,000, when updated in this way, all addresses are deleted and added again. It's pointless to do this every time you update.

This service only allows you to edit changes. Delete something, add something

## Guide 

### Prepare block list

[docker-compose crowdsec-blocklist](https://github.com/akmalovaa/crowdsec-blocklist)

Or use your own list of IP addresses, the list should be accessible by url

### Prepare Router OS

Create certifcates
```
/certificate
add name=CA-Template common-name=CAtemp key-usage=key-cert-sign,crl-sign
add name=Server common-name=server
add name=Client common-name=client
```

Certificates should be signed.
```
/certificate
sign CA-Template
sign Client     
sign Server ca-crl-host=192.168.88.1 name=ServerCA
```

Enable API-SSL
```
/ip service
set api-ssl address=192.168.88.0/24 certificate=ServerCA
```

### Docker compose

build
```bash
docker build . -t mikroseclist:latest
```

or use github image

```bash
docker pull . -t mikroseclist:latest
```

using `docker-compose.yaml`

```yaml
services:
  mikroseclist:
    image: mikroseclist:latest
    container_name: mikroseclist
    command: ["python", "-m", "mikroseclist.main"]
    environment:
      MIKROTIK_HOST: ${MIKROTIK_HOST:-'192.168.88.1'}
      MIKROTIK_USER: ${MIKROTIK_USER:-'admin'}
      MIKROTIK_PASSWORD: ${MIKROTIK_PASSWORD:-'password'}
      BLOCKLIST_URL: 'http://blocklist.example.com:41412/security/blocklist?ipv4only'
      SYNC_INTERVAL_MIN: 30
    volumes:
      - ./:/srv/
    restart: unless-stopped
```

change environment variables and run:

```
docker-compose up -d
```

Change Mikrotik Firewall Rules
```
/ip firewall filter
add action=accept chain=input src-address-list=access
add action=drop chain=input in-interface=ether1 src-address-list=block
add action=drop chain=forward in-interface=ether1 src-address-list=block
```