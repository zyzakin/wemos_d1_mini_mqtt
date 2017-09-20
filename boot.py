def do_connect():
    import network
    import time
    from config import ssid, psk
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    if ap_if.active():
        ap_if.active(False)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid, psk)
        count = 0
        while not sta_if.isconnected():
            time.sleep_ms(1)
            count += 1
            if count==10000:
                print("Don't conected to {}".format(ssid))
                break

    if sta_if.isconnected() :
        print('WIFI config: ', sta_if.ifconfig())
        from ntptime import settime
        try:
            settime()
        except OSError as e:
            print(b"settime error: {}".format(e))
            time.sleep_ms(1000)
            settime()
            #[Errno 110] ETIMEDOUT
do_connect()
import webrepl
webrepl.start()
gc.collect()
