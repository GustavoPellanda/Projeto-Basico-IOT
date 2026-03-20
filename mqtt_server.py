import paho.mqtt.client as mqtt
import OPi.GPIO as GPIO

GPIO.setmode(GPIO.SUNXI)
GPIO.setup("PA6", GPIO.OUT)
GPIO.output("PA6", GPIO.LOW)  # começa desligado

def on_connect(client, userdata, flags, rc):
    print("Broker conectado!")
    client.subscribe("casa/lampada")

def on_message(client, userdata, msg):
    comando = msg.payload.decode()
    print(f"Comando recebido: {comando}")
    if comando == "ligar":
        GPIO.output("PA6", GPIO.HIGH)
        print("Lâmpada LIGADA")
    elif comando == "desligar":
        GPIO.output("PA6", GPIO.LOW)
        print("Lâmpada DESLIGADA")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
print("Aguardando comandos...")
client.loop_forever()