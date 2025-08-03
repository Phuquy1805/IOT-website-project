FROM eclipse-mosquitto:2.0

COPY config/mosquitto.conf /mosquitto/config/mosquitto.conf

EXPOSE 1883

CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
