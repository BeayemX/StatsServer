const RECONNECT_TIMEOUT = 2500;

let ws;

function connectToWebSocket() {
    ws = new WebSocket(ws_host);

    // Connect to websockets
    ws.addEventListener('open', (event) => {
        console.log("Connected");
    	_requestData();
    });

    ws.addEventListener('message', (event) => {
        // console.log("Message: ", event.data);
        const jsonData = JSON.parse(event.data);

        if (jsonData['type'] == 'update_data') {
            handleDataUpdate(jsonData['data']);
        }
    });

    ws.addEventListener('close', (event) => {
        console.log("Websocket close");
        setTimeout(() => {
            console.log("Trying to reconnect...")
            connectToWebSocket()
        }, RECONNECT_TIMEOUT);
    });

    ws.addEventListener('error', (event) => {
        console.log("Websocket error connecting.");
    });
}

function send(sendData) {
    // sendData['client_id'] = clientID; // TODO implement client_id?
    try {
        ws.send(JSON.stringify(sendData));
    } catch (error) {
        console.log("Error when sending via WebSocket", error)
        return false;
    }
    return true;
}

