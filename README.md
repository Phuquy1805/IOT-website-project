

# Run
* Install and Open [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* Open powershell and run:
```bash
docker compose up --build --force-recreate
```
* By default, the web is on localhost:9000
# NOTE
Change `mqttServer` in **esp32/main/main.ino** to your device's IP running docker.
# TO DO
* API encryption
* IOT communication
* Forget password mail
* Dashboard
* Admin panel
* Prettier CSS, better UI
