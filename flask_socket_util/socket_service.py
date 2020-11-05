import os
import logging
import json
import requests
from threading import Thread

import eventlet

from flask import Blueprint, jsonify, request
from flask_socketio import SocketIO, emit, join_room

from kafka import KafkaConsumer
from kafka.errors import KafkaError

'''
The socket endpoint for web services.
We have "rooms" for experiments; the client's join the rooms for updates.
The server side intercepts Kafka messages and posts these back to the client.
In addition, one can send custom messages back to the client by POSTing to the send_message_to_client.
Do this using requests.post to avoid thread deadlock issues; that is, don't call the method directly, instead use requests.post
'''

__author__ = 'jacob.defilippis@cosylab.com'

logger = logging.getLogger(__name__)

# Socket context
socketio = SocketIO()
socket_service_blueprint = Blueprint('socket_service_api', __name__)
security = None


class Manager(object):
    clients = 0
manager = Manager()


def init_app(app, securityobj, kafkatopics=None):
    '''
    Initialize and register the socket service.
    The socket service is always registered on the path /ws/socket.
    :param: app - The Flask application. We register the socketio blueprint and initialize socketio.
    :param: securityobj - The flask_authnz object used for authentication and authorization.
    :param: kafkatopics - Specify a list of Kafka topics so subscribe to. Messgaes on these topics are routed to the browser as websocket events.
    '''
    app.register_blueprint(socket_service_blueprint, url_prefix="/ws/socket")
    global security
    security = securityobj
    socketio.init_app(app, async_mode="eventlet", cors_allowed_origins='*')
    if kafkatopics:
        kafka_2_websocket(kafkatopics)

@socketio.on('connect', namespace='/psdm_ws')
def connect():
    """
    New client connects to the socket.
    """
    logger.info("New connection attempt")
    manager.clients += 1

@socketio.on('join', namespace='/psdm_ws')
def on_join(experiment_name):
    if security.check_privilege_for_experiment('read', experiment_name):
        logger.info("User %s joined socketio room for experiment %s" % (security.get_current_user_id(), experiment_name))
        join_room(experiment_name)
    else:
        logger.warn("User %s does not have permission for socketio room for experiment %s" % (security.get_current_user_id(), experiment_name))
        join_room("Noop")

@socketio.on('disconnect', namespace='/psdm_ws')
def disconnect():
    """
    Client disconnects from socket.
    :return:
    """
    manager.clients -= 1




@socket_service_blueprint.route("/send_message_to_client/<experiment_name>/<message_type>", methods=["POST"])
def sock_send_message_to_client(experiment_name, message_type):
    """
    Send the message to all clients connected to this experiment's room
    :param: experiment_name - The experiment_name; for example, diadaq13
    :param: message_type - The message type/business object type of the message; for example, elog
    """
    # Push update only if some clients are connected.
    if manager.clients > 0:
        request.json['psdm_ws_msg_type'] = message_type;
        socketio.emit("psdm_ws_msg", request.json, namespace='/psdm_ws' , room=experiment_name)

    return jsonify(success=True)


# Subscribe to Kafka messages for these topics and send them across to the client.
def kafka_2_websocket(topics):
    """
    Subscribe to a list of topics from Kafka.
    Route messages on these topics to the web socket clients.
    :param: topics - The list of topics that we want to subscribe to.
    """
    app_server_ip_port = os.environ["SERVER_IP_PORT"]
    # We categorize Kafka messages by experiment for performance reasons.
    # However; this means that UI's that span experiments are at a loss as to which room to subscribe to
    # So, we cross publish a subset of topics (really only one - experiments ) to a global "the_global_room"
    global_room_topics = ["experiments"]

    def subscribe_kafka():
        if os.environ.get("SKIP_KAFKA_CONNECTION", False):
            logger.warn("Skipping Kafka connection")
            return
        consumer = KafkaConsumer(bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVER", "localhost:9092").split(","))
        consumer.subscribe(topics)

        for msg in consumer:
            logger.info("Message from Kafka %s", msg)
            info = json.loads(msg.value)
            logger.info("JSON from Kafka %s", info)
            message_type = msg.topic
            exp_name = info['experiment_name']
            requests.post("http://" + app_server_ip_port + "/ws/socket/send_message_to_client/" + exp_name + "/" + message_type, json=info)
            if message_type in global_room_topics:
                requests.post("http://" + app_server_ip_port + "/ws/socket/send_message_to_client/the_global_room/" + message_type, json=info)


    # Create thread for kafka consumer
    kafka_client_thread = Thread(target=subscribe_kafka)
    kafka_client_thread.start()
