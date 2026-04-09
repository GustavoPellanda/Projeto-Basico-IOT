# Orange Pi Zero como Servidor MQTT para IoT

Guia completo para configurar um Orange Pi Zero como servidor MQTT, usando o controle de uma lâmpada como exemplo prático e expansível para outros projetos IoT.

## Arquitetura

```
PC / Celular  →  publica mensagem  →  Broker MQTT (Orange Pi)  →  Script Python  →  Relé  →  Lâmpada
```

O Orange Pi funciona como o cérebro central da rede IoT: roda o broker MQTT, processa os comandos e aciona os dispositivos físicos. Outros dispositivos (PC, celular, ESP32) se comunicam com ele via rede.

---

## Materiais Necessários

### Hardware
- Orange Pi Zero com header de 26 pinos soldado
- Módulo relé 5V com placa (bornier com pinos VCC/GND/IN e NO/COM/NC)
- Lâmpada com cabo desencapado
- Tomada com cabo desencapado
- Jumpers (cabos de protoboard macho-fêmea)
- Cartão microSD (8GB ou mais)
- Cabo micro-USB (fonte 5V/2A para alimentação)
- Cabo de rede ethernet (necessário para o primeiro acesso)

### Software
- [Balena Etcher](https://balena.io/etcher) — para gravar a imagem no cartão SD
- [Armbian Minimal/IOT](https://www.armbian.com/orange-pi-zero/) — sistema operacional
- Python 3 + paho-mqtt — no PC para enviar comandos

---

## 1. Preparando o Cartão SD

Baixe a versão **Minimal / IOT** do Armbian para Orange Pi Zero. A versão XFCE tem interface gráfica desnecessária para este projeto.

Abra o Balena Etcher, selecione a imagem `.img` baixada, selecione o cartão microSD e clique em **Flash**. O Etcher apaga e grava automaticamente — não é necessário formatar antes.

> ⚠️ Verifique com atenção o destino no Etcher para não sobrescrever um HD do seu PC.

---

## 2. Primeiro Acesso via SSH

Insira o cartão no Orange Pi, conecte o cabo de rede ao roteador e ligue a alimentação via micro-USB. Após ~60 segundos ele estará disponível na rede.

### Descobrindo o IP

Tente primeiro pelo hostname:

```bash
ping orangepizero.local
```

Se não funcionar, use este script Python no seu PC para escanear a rede:

```python
import subprocess, platform

def ping(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    r = subprocess.run(['ping', param, '1', '-w', '500', ip],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0

for i in range(1, 255):
    ip = f'192.168.1.{i}'  # ajuste para sua faixa de rede
    if ping(ip): print(f'Ativo: {ip}')
```

### Conectando

```bash
ssh root@<IP_DO_ORANGE_PI>
```

A senha padrão do Armbian é `1234`. No primeiro acesso ele pedirá para criar uma nova senha e um usuário comum.

---

## 3. Configurando o Sistema

### Atualizar pacotes

```bash
apt update && apt upgrade -y
```

### Instalar dependências

```bash
apt install mosquitto mosquitto-clients python3-pip -y
pip3 install OPi.GPIO paho-mqtt --break-system-packages
```

### Configurar o Mosquitto

Por padrão o Mosquitto só aceita conexões locais. Para aceitar conexões externas, edite o arquivo de configuração:

```bash
nano /etc/mosquitto/mosquitto.conf
```

Adicione ao final:

```
listener 1883
allow_anonymous true
```

Salve e reinicie:

```bash
systemctl restart mosquitto
systemctl enable mosquitto
```

---

## 4. Montagem do Hardware

> ⚠️ Sempre faça as conexões com o Orange Pi **desligado**. A parte de alta tensão só deve ser conectada depois que tudo estiver montado e verificado.

### Pinout do header de 26 pinos

O pino 1 fica no canto do header, identificado pelo pad quadrado no PCB. Contagem: ímpares à esquerda, pares à direita.

```
[P01 - 3.3V ][P02 - 5V   ] ← VCC do relé
[P03 - SDA  ][P04 - 5V   ]
[P05 - SCK  ][P06 - GND  ] ← GND do relé
[P07 - PA6  ][P08 - TX   ] ← IN do relé
...
```

| Pino | Função   | Conectar em | Cor sugerida |
|------|----------|-------------|--------------|
| P02  | 5V       | VCC do relé | Vermelho     |
| P06  | GND      | GND do relé | Preto        |
| P07  | PA6/PWM1 | IN do relé  | Amarelo      |

### Conexões de alta tensão

Com a tomada **desligada da parede**:

- **COM** → fio de fase da tomada
- **NO** → fio de fase da lâmpada
- O fio **neutro** da tomada vai direto para o neutro da lâmpada, sem passar pelo relé
- **NC** → deixe vazio

> ⚠️ Nunca toque nos bornes de alta tensão com o circuito energizado.

---

## 5. Código Python

### Servidor MQTT — Orange Pi (`mqtt_server.py`)

Para criar um arquivo Python no Orange Pi via SSH, use o editor nano:
```bash
nano mqtt_server.py
```

```python
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
```

### Cliente MQTT — PC (`mqtt_client.py`)

```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("192.168.100.200", 1883)  # IP fixo do Orange Pi

comando = input("Digite 'ligar' ou 'desligar': ")
client.publish("casa/lampada", comando)
print(f"Comando '{comando}' enviado!")
```

Instale a biblioteca no PC:

```bash
pip install paho-mqtt
```

---

## 6. Execução Automática na Inicialização

Para que tudo suba automaticamente quando o Orange Pi ligar, sem precisar de SSH ou intervenção manual, configure três coisas:

### 6.1 IP fixo

Acesse o menu de configuração do Armbian:

```bash
armbian-config
```

Navegue em **Network → WiFi** (ou Ethernet), escolha **static** e defina um IP fixo como `192.168.100.200/24`. Assim o Orange Pi sempre estará no mesmo endereço na rede.

### 6.2 Wi-Fi automático

No mesmo menu `armbian-config → Network → WiFi`, conecte à sua rede Wi-Fi. O Armbian vai salvar as credenciais e reconectar automaticamente a cada inicialização, eliminando a necessidade do cabo de rede.

### 6.3 Script Python como daemon (systemd)

Crie o arquivo de serviço:

```bash
nano /etc/systemd/system/lampada.service
```

Conteúdo:

```ini
[Unit]
Description=Servidor MQTT Lampada
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /root/mqtt_server.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

Ative o serviço:

```bash
systemctl daemon-reload
systemctl enable lampada
systemctl start lampada
```

### Resultado

A partir de agora, ao ligar o Orange Pi na energia:

```
Liga na energia
  → conecta no Wi-Fi automaticamente
  → Mosquitto sobe (systemctl enable mosquitto)
  → mqtt_server.py sobe (systemctl enable lampada)
  → pronto para receber comandos
```

### Comandos úteis para gerenciar o serviço

```bash
systemctl status lampada      # ver se está rodando
systemctl stop lampada        # parar
systemctl restart lampada     # reiniciar
journalctl -u lampada -f      # ver logs em tempo real
```

---
