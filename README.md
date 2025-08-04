# Devices
* AI Thinker ESP32-CAM

# Run the project
## Backend .env setup
* **[!]** Set valid **Resend** API Key on [Resend](https://resend.com).
* **[!]** Point the backend to your MQTT host.
```c
MQTT_BROKER_URL=YOUR_PC_LAN_IP; // e.g. 192.168.x.x
```

## Build docker images
* Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* Open powershell and run from the project root:
```bash
docker compose up --build --force-recreate
```

## Arduino IDE setup
* I used version 2.2.1, download [here](https://github.com/arduino/arduino-ide/releases).
* Install ESP32 board, follow this [instruction](https://randomnerdtutorials.com/installing-esp32-arduino-ide-2-0).
* Open `esp32/main/main.ino` in the IDE and set:
```c
const char* mqttServer = "YOUR_PC_LAN_IP"; // e.g. 192.168.x.x
```
* In the same file, change `IMGBB_API_KEY` obtained from [here](https://api.imgbb.com).
* Compile and upload code to the ESP32-CAM, see instructions [here](https://www.youtube.com/watch?v=hSr557hppwY&t=942s&pp=ygUJZXNwMzIgY2Ft).
* Click the CAM's reset (RST) button to run.

## Webb access
* By default, web is hosted on `localhost:9000`.

# ESP32 features (for now)
* Create an Access Point to host a Wi-Fi configuration website at `192.168.4.1` (IP may change).
* Capture photos every 10s (changable).
* Send captures to Imgbb and publish urls to a MQTT topic.

# Web features (for now)
* **Log in** / **sign up** / **sign in** system using database to stored uer information.
* **Sign up** account using OTP sent via mail.
* Dashboard with latest captured image viewer which fetch images from Imgbb urls.

# TO DO
* API encryption
* IOT communication
* Forget password mail
* Dashboard
* Admin panel
* Prettier CSS, better UI

> Dont worry, I've rotated my ImgBB API key.
