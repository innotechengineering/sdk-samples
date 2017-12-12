"""
An MQTT App example
Reference: https://www.eclipse.org/paho/clients/python/docs/

This app does the following:
- Connects to MQTT test server ‘test.mosquitto.org’
- Subscribes to topic ‘paho/test/single/gps’
- Runs a background thread which publishes router gps info to topic ‘paho/test/single/gps’ every 10 secs.
- Generates a log when the MQTT server sends the published information for topic ‘paho/test/single/gps’
  which was subscribed to.
"""

# A try/except is wrapped around the imports to catch an
# attempt to import a file or library that does not exist
# in NCOS. Very useful during app development if one is
# adding python libraries.
try:
    import cs
    import sys
    import traceback
    import argparse
    import settings
    import json
    import time
    import paho.mqtt.client as mqtt
    import paho.mqtt.publish as publish

    from app_logging import AppLogger
    from threading import Thread

except Exception as e:
    # Output logs indicating what import failed.
    cs.CSClient().log('mqtt_app.py', 'Import failure: {}'.format(e))
    cs.CSClient().log('mqtt_app.py', 'Traceback: {}'.format(traceback.format_exc()))
    sys.exit(-1)


# Create an AppLogger for logging to syslog in NCOS.
log = AppLogger()

# The mqtt_client for publishing to the broker
mqtt_client = None


# Called when the broker responds to our connection request.
def on_connect(client, userdata, flags, rc):
    log.debug("MQTT Client connection results: {}".format(mqtt.connack_string(rc)))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    topics = [(settings.GPS_TOPIC, settings.MQTT_QOS),
              (settings.MODEM_TEMP_TOPIC, settings.MQTT_QOS),
              (settings.WAN_CONNECTION_STATE_TOPIC, settings.MQTT_QOS)]
    try:
        client.subscribe(topics)
    except Exception as ex:
        log.error('Client Subscribe exception. ex={}'.format(ex))


# Called when a message has been received on a topic that the client subscribes
# to and the message does not match an existing topic filter callback. Use
# message_callback_add() to define a callback that will be called for specific
# topic filters. on_message will serve as fallback when none matched.
def on_message(client, userdata, msg):
    log.debug('Published msg received. topic: {}, msg: {}'.format(msg.topic, msg.payload))


# Called when a message that was to be sent using the publish() call has
# completed transmission to the broker. For messages with QoS levels 1
# and 2, this means that the appropriate handshakes have completed. For
# QoS 0, this simply means that the message has left the client. The mid
# variable matches the mid variable returned from the corresponding publish()
# call, to allow outgoing messages to be tracked.
#
# This callback is important because even if the publish() call returns success,
# it does not always mean that the message has been sent.
def on_publish(client, userdata, mid):
    log.debug('Publish response: Message ID={}'.format(mid))


# Called when the broker responds to a subscribe request. The mid variable
# matches the mid variable returned from the corresponding subscribe() call.
# The granted_qos variable is a list of integers that give the QoS level the
# broker has granted for each of the different subscription requests.
def on_subscribe(client, userdata, mid, granted_qos):
    log.debug('Subscribe response: Message ID={}, granted_qos={}'.format(mid, granted_qos))


# This function will periodically publish device data to the MQTT Broker
def publish_thread():
    log.debug('Start publish_thread()')
    while True:
        try:
            gps_lastpos = cs.CSClient().get(settings.GPS_TOPIC).get('data')
            gps_pos = {'logitude': gps_lastpos.get('longitude'),
                       'latitude': gps_lastpos.get('latitude')}

            # Single Topic Publish example
            publish.single(settings.GPS_TOPIC, payload=json.dumps(gps_pos), qos=settings.MQTT_QOS,
                           hostname=settings.MQTT_SERVER, port=settings.MQTT_PORT)

            # Multiple Topics Publish example
            modem_temp = cs.CSClient().get(settings.MODEM_TEMP_TOPIC).get('data', '')
            wan_connection_state = cs.CSClient().get(settings.WAN_CONNECTION_STATE_TOPIC).get('data')

            msgs = [(settings.MODEM_TEMP_TOPIC, modem_temp, settings.MQTT_QOS, False),
                    (settings.WAN_CONNECTION_STATE_TOPIC, wan_connection_state, settings.MQTT_QOS, False)]

            publish.multiple(msgs=msgs, hostname=settings.MQTT_SERVER, port=settings.MQTT_PORT)

            time.sleep(10)
        except Exception as ex:
            log.error('Exception in send_gps(). ex: {}'.format(ex))


def start_mqtt():
    global mqtt_client
    try:
        log.debug('Start MQTT Client')

        mqtt_client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.on_publish = on_publish
        mqtt_client.on_subscribe = on_subscribe

        log.debug('MQTT connect to {}, {}'.format(settings.MQTT_SERVER, settings.MQTT_PORT))
        mqtt_client.connect(settings.MQTT_SERVER, settings.MQTT_PORT)

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        mqtt_client.loop_forever()

    except Exception as ex:
        log.error('Exception in start_mqtt()! exception: {}'.format(ex))
        raise


def start_router_app():
    try:
        log.debug('start_router_app()')

        # Start the MQTT client thread.
        mqtt_thread = Thread(target=start_mqtt, args=())
        mqtt_thread.start()

        publish_thread()

        time.sleep(36000)

    except Exception as ex:
        log.error('Exception during start_router_app()! exception: {}'.format(ex))
        raise


def stop_router_app():
    try:
        log.debug('stop_router_app()')

    except Exception as ex:
        log.error('Exception during stop_router_app()! exception: {}'.format(ex))
        raise


def action(command):
    try:
        log.debug('action({})'.format(command))

        if command == 'start':
            start_router_app()

        elif command == 'stop':
            stop_router_app()

    except Exception as ex:
        log.error('Exception during {}! exception: {}'.format(command, ex))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('opt')
    args = parser.parse_args()

    opt = args.opt.strip()
    if opt not in ['start', 'stop']:
        log.debug('Failed to run command: {}'.format(opt))
        exit()

    action(opt)

    log.debug('App is exiting')
