# flask_socket_util
This is a small utility for using websockets from within Flask for PSDM web services.
It consists of a Flask blueprint for web sockets and some client Javascript.

## Usage
- To initialize the socket service, in your `start.py`
```
from flask_socket_util import socket_service

socket_service.init_app(app, security, kafkatopics = ["elog"])
```
  - You'll need to pass in the Flask `app` and the `flask_authzn` security object for authorization.
  - You can pass in an optional list of Kafka topics; messages on these topics are routed to the browser.
  - The socket_service establishes a Flask endpoint at `/ws/socket`.
  - If you need to pass other messages to the browser, use `requests.post` to POST JSON to the socket service endpoint.
```
app_server_ip_port = os.environ["SERVER_IP_PORT"]
requests.post("http://" + app_server_ip_port + "/ws/socket/send_message_to_client/" + experiment_name + "/" + message_type, json=your_json)
``` 
- The client Javascript is part of the Python package. Include it in your template like so
```
  <script type="text/javascript" src="../../js/socket.io/node_modules/socket.io-client/dist/socket.io.js"></script>
  <script type="text/javascript" src="../../js/python/flask_socket_util/websocket_client.js"></script>
```
and add the Python hook in your `js` resolver.
```
import pkg_resources

@pages_blueprint.route('/js/<path:path>')
def send_js(path):
	pathparts = os.path.normpath(path).split(os.sep)
	if pathparts[0] == 'python':
	    # This is code for gettting the JS file from the package data of the python module.
	    filepath = pkg_resources.resource_filename(pathparts[1], os.sep.join(pathparts[2:]))
	    if os.path.exists(filepath):
	        return send_file(filepath)

```

In your client JS, add these lines in your document.ready function
```
	var experiment_name = "{{ experiment_name }}";

    WebSocketConnection.connect();
    $(document).on('elog', function(event, elogData) {
    	console.log("Processing elog event for experiment " + experiment_name);

```


### Debugging websocket configuration
Websocket is typically routed thru Apache (or another web server) to Python.
Some tips for making sure everything is set up correctly.
- First make sure, your application is responding correctly. If your `gunicorn` is listening on port 5000, check the `socket.io` endpoint using
```
curl -v -H "Upgrade: WebSocket" -H "Connection: Upgrade" "http://localhost:5000/socket.io/?EIO=3"
```
You should see a `HTTP/1.1 200 OK` response from `gunicorn`.
- Create a separate section in Apache configuration for the socket connections. For example, if your app is served thru `psdm`, create a location for `psdm_socketio` like so
```
<LocationMatch "^/psdm_socketio/(.*)$">
  ... Other configuration like WebAuth headers etc
  ProxyPass ws://localhost:5000/$1
  ProxyPassReverse ws://localhost:5000/$1
</LocationMatch>

```
- Now test the same URL thru the web server.
```
curl -v -H "Upgrade: WebSocket" -H "Connection: Upgrade" "http://localhost/psdm_socketio/socket.io/?EIO=3"
```
You should get a proper response from `socket.io`. For example,
```
	?0{"sid":"xxx","upgrades":["websocket"],"pingTimeout":60000,"pingInterval":25000}....
```
