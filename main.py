import machine, onewire, ds18x20
import ubinascii as binascii

from umqtt.simple import MQTTClient

from config import broker, ow_pin

# var declaration
machine_id = binascii.hexlify(machine.unique_id())
ds = None #OneWwire temperature sensor
roms = [] # temperature senor list
temp = 0
tim2 = machine.Timer(-1) # Timer


print(b"Machine ID: {}".format(machine_id))

strip = None
client = None
led = None
#relay1 = None
#relay2 = None
relays = {}

def initOW(ow_pin):
    global ds
    global roms
    global client
    try:
        dat = machine.Pin(ow_pin) #pinu według arduino
        ds = ds18x20.DS18X20(onewire.OneWire(dat))
        roms = ds.scan()
        print(b"znalezionych czujnikow : {}".format(len(roms)))
    except ValueError:
        print(b"Niepoprawny numer Pin :{}".format(ow_pin))
        client.publish(topic_name(b"error"), b"OW - invalid pin number:{}".format(ow_pin))
    except Exception as e :
        print(b"Błąd w initOW :{}".format(e))
        client.publish(topic_name(b"error"), b"OW - init error:{}".format(e))
    #print(b"znalezionych czujnikow DS: {}".format(roms))
    return len(roms)

def getTemp(p):
    global ds
    global client
    for rom in roms:
        temperature = round(ds.read_temp(rom),2)
        str_rom = binascii.hexlify(rom)
        #client.publish(topic_name(b"temperature"), b"{}:{}".format(str_rom, temperature))
        client.publish(topic_name(b"temperature"), b"{}".format(temperature))
        print(b"{}:{}".format(str_rom, temperature))

def startConv(p = 0):
    global ds
    ds.convert_temp()
    tim2.init(period=750, mode=machine.Timer.ONE_SHOT, callback=getTemp)

def callback(topic, msg):
    global realys
    if topic == topic_name(b"cmd"):
        try:
            if b":" in msg :
                msg_type, payload = msg.split(b":", 1)
                if msg_type == b"relay1":
                    relay_manage(msg_type, payload)
                elif msg_type == b"relay2":
                    relay_manage(msg_type, payload)
            else:
                payload = msg
                if payload == b"reboot":
                    machine.reset()
                if payload == b"ow_reboot":
                    initOW(ow_pin)
                else:
                    print("Unknown payload, ignoring [{}]".format(payload))
        except Exception as e:
            print("Couldn't parse/handle message, ignoring. Topic:{} Payload:{} ->e:{}".format(topic,msg, e))
    elif topic == topic_name(b"config"):
        load_config(msg)

def publish_state(p=1):
    global relays
    if relays['relay1'].value():
        client.publish(topic_name(b"relay1"), b"on")
    else:
        client.publish(topic_name(b"relay1"), b"off")
    print("Relay state: {}".format("on" if relays['relay1'].value() else "off"))

def topic_name(topic):
    return b"/".join([b"light", machine_id, topic])

def relay_manage(relay, msg): #depracated
    global led
    global relays
    msg = msg.decode("utf-8") if isinstance(msg, bytes) else msg
    relay = relay.decode("utf-8") if isinstance(relay, bytes) else relay
    try:
        if msg == 'on':
            relays[relay].on()
        elif msg == 'off':
            relays[relay].off()
        #publish_state()
        print("rely: {}, state: {}".format(relay,relays[relay].value()))
    except Exception as e:
        print("blad ->{}". format(e))

def connect_and_subscribe():
    global client
    client = MQTTClient(machine_id, broker)
    client.set_callback(callback)
    try:
        client.connect()
        print("Connected to {}".format(broker))
        for topic in (b'config', b'cmd', b'relay1'):
            t = topic_name(topic)
            client.subscribe(t)
            print("Subscribed to {}".format(t))
    except OSError as e :
        print(b"mqtt error: {}".format(e))
        #OSError: [Errno 113] EHOSTUNREACH

def load_config(msg):
    import ujson as json
    try:
        config = json.loads(msg)
    except (OSError, ValueError):
        print("Couldn't load config : {} from JSON, bailing out.".format(msg))
    else:
        set_power(config['power'])

#def pub_status(p=1):
#    global client
#    client.publish('{}/{}'.format(CONFIG['topic'],
#                                          CONFIG['client_id']),
#                                          bytes(str(data), 'utf-8'))
#    print('Sensor state: {}'.format(data))
#    print("1")

def setup():
    global led
    global relays
    from config import led_pin, relay1_pin, relay2_pin

    try:
        relays['relay1'] = machine.Signal(machine.Pin(relay1_pin, machine.Pin.OUT), invert=True)
    except (OSError, ValueError):
        print(b"Couldn't config pin {}".format(relay1_pin))
    try:
        relays['relay2'] = machine.Signal(machine.Pin(relay2_pin, machine.Pin.OUT), invert=True)
    except (OSError, ValueError):
        print(b"Couldn't config pin {}".format(relay2_pin))

    connect_and_subscribe()
    sensor_count = initOW(ow_pin)
    if sensor_count > 0:
        tim = machine.Timer(-1) # timer
        startConv()
        tim.init(period=300000, mode=machine.Timer.PERIODIC, callback=startConv) # 5 min
    #checker = machine.Timer(-1)
    #checker.init(period=500000, mode=machine.Timer.PERIODIC, callback=publish_state)



def main_loop():
    while 1:
        client.wait_msg()

def teardown():
    try:
        client.disconnect()
        print("Disconnected.")
    except Exception:
        print("Couldn't disconnect cleanly.")

if __name__ == '__main__':
    setup()
    try:
        main_loop()
    finally:
        teardown()
