// Settings
let availableColors = [
    "#ddddddff", // white
    "#19c7f2ff", // cyan
    "#00e700ff", // green
    "#f4ff1cff", // yellow
    "#ffac1cff", // orange
    "#f03f3fff", // red
    "#e534d4ff", // magenta
    "#4c67ffff", // blue
    "rgba(0, 0, 0, 1)",
    "rgba(255, 0, 0, 1)",
    "rgba(0, 255, 0, 1)",
    "rgba(0, 0, 255, 1)",
    "rgba(255, 255, 0, 1)",
    "rgba(255, 0, 255, 1)",
    "rgba(0, 255, 255, 1)",
    "rgba(255, 0, 255, 1)"
];

const DEFAULT_AUTO_RELOAD = true;
const DEFAULT_TIME_RANGE = 60*60;
const RELOAD_MINIMUM_TIME_MS = 2000;

const nbsp = "\xa0";
const maxBars = 56;

const timeRanges = [60, 60*5, 60*10, 60*30, 60*60, 60*60 * 6, 60*60 * 12, 60*60*24];

// Members
let _cursorPos = 0; // timestamp
let last_server_sync_timestamp = 0;
let cachedData = null;

let _timeRange;
let rightValueBound = 0; // timestamp
let storedTimeout = null;
let elements = null;

let oldestTimeStamp = 0;

let debugMode = false;
let debugCounter = 0;

let socket;

let averageData = false;
let graphSteps = 110;


let interval = null;

let autoReload = true;
let reloadState;

let touchStartX = null;
let singleTouchStart = null;
let currentPinchDiff = 0;

// Stored DOM elements
let infoLine;
let timeDisplay;
let timeRangeDisplay;

let debugOverlay;
let debugArea;
let prepareDataButton;

let timedropdown;
let customOptionSelect;

function onLoad() {
    restoreSettings();

    // Find DOM elements
    wrapper = document.getElementById("wrapper");
    infoLine = document.getElementById("infoline");

    timeRangeDisplay = document.getElementById("timerangedisplayLabel");
    timeDisplay = document.getElementById("timedisplay");

    debugOverlay = document.getElementById("debugoverlay");
    debugArea = document.getElementById("debugarea");
    prepareDataButton = document.getElementById("preparedatabutton");

    reloadState = document.getElementById("reloadstate");

    // create dropdown entries
    timedropdown = document.getElementById("timedropdown");
    customOptionSelect = document.createElement('option');

    let option = customOptionSelect
    option.value = _getTimeRange();
    option.innerHTML = _secondsToTime(_getTimeRange());

    timedropdown.appendChild(option);

    for (let time of _getTimeRanges()) {
        option = document.createElement('option');
        option.value = time;
        option.innerHTML = _secondsToTime(time);
        timedropdown.appendChild(option);
    }




    // Set up DOM elements / Initialize elements
    _updateDebugMode(false);

    // Update UI
    updateTimeRangeDisplay();

    _updateReloadState();
    _updateDebugMode();


    // Connect to websockets
    socket = io.connect('http://' + document.domain + ':' + location.port, { 'transports': ['websocket'] });

    socket.on('connect', function() {
        //socket.emit('my event', {data: 'I\'m connected!'});
        //socket.send('string argument');
        // not working even though on the server there is a on('json') callback
        // maybe old version?
        // socket.send({
        //    data: "i am a json"
        // });
    });


    socket.on('update_data', (msg) => {
        handleDataUpdate(msg);
    })

    if (autoReload)
        activateAutoUpdate();


    _requestData();
    changePreparationResolution(0); // calling _updateGraphs() (initially unnecessary)
}

function _requestData(){
    socket.emit("request_data", {
        "last_server_sync_timestamp": last_server_sync_timestamp,
        });

    log("Requesting data...");
}

function activateAutoUpdate() {
    if (interval)
        clearInterval(interval);

    interval = setInterval(_requestData, RELOAD_MINIMUM_TIME_MS);
}

function handleDataUpdate(data_json_s) {
    log("Handle update... " + humanizeBytes(roughSizeOfObject(data_json_s)));
    newServerData = JSON.parse(data_json_s);
    // console.log(newServerData)

    // Store last server sync and show time of last update
    last_server_sync_timestamp = newServerData["last_server_sync_timestamp"];

    // jump to newest value when new data arrives
    // if (!autoReload)
    {
        rightValueBound = last_server_sync_timestamp;
        _cursorPos = last_server_sync_timestamp;
    }


    // Show time of last update
    timeDisplay.innerText =  `Last update: ${_timestampToTime(last_server_sync_timestamp)}`;

    // Store data on client
    if (cachedData == null)
        cachedData = newServerData
    else {
        let categories = newServerData["categories"];
        for (let categoryName in categories)
        {
            let category_data = categories[categoryName];
            for (let entryName in category_data["entries"])
            {
                let entryData = category_data["entries"][entryName];
                cachedData["categories"][categoryName]["entries"][entryName] = cachedData["categories"][categoryName]["entries"][entryName].concat(entryData);
            }
        }
    }

    // Initial creation of dom tree
    if (elements == null) {
        elements = {};
        let categories = newServerData["categories"];
        for (let category in categories) {
            let category_data = categories[category];
            console.log(category);
            console.log(category_data);
            _generateEntry(category, Object.keys(category_data["entries"]), category_data);
        }
    }

    _updateGraphs();
}

function _updateGraphs() {
    if (!cachedData)
        return;

    // Prepare for drawing
    _updateOldestTimeStamp();
    _updateTimeRangeOffset();

    // Actual drawing
    for (let categoryName in elements) {

        let category_data = cachedData["categories"][categoryName]
        _updateBars(category_data, categoryName);
        _updateCanvas(category_data, elements[categoryName]["canvas"]);
    }
}

function getCursorTime() {
    return _cursorPos;
}

function _getValueAtCursor(categoryData, key) {
    let allValues = _getValuesForVisibleTimeRange(categoryData, key);
    let cursorTimestamp = getCursorTime();

    let i = 0;

    for (; i<allValues.length; ++i){
        if (allValues[i][0] >= cursorTimestamp) {
            if (i > 0) {

                const lowerIDistance = Math.abs(allValues[i-1][0] - cursorTimestamp);
                const higherIDistance = Math.abs(allValues[i][0] - cursorTimestamp);

                if (lowerIDistance < higherIDistance) {
                    i = i-1;
                }
            }

            break;
        }
    }

    i = Math.min(i, allValues.length-1); // Clamp to last array-value if no break occurs
    let value = allValues[i];

    return value;
}

function _updateBars(categoryData, categoryName) {
    for (const key of Object.keys(categoryData["entries"])) {
        // Label
        elements[categoryName][key]["label"].innerText = key;

        // Value
        let value = _getValueAtCursor(categoryData, key)[1];
        elements[categoryName][key]["value"].innerText = (Math.round(value * 100) / 100) + categoryData["unit"];

        // Bar
        let min = categoryData["min"];
        let max = categoryData["max"];
        let needed = Math.round(((value - min) / (max - min)) * maxBars);
        let text = "";

        for (let i=0; i<maxBars; ++i) {
            if (i < needed)
                text += "|";
            else
                text += nbsp;
        }

        elements[categoryName][key]["bar"].innerText = text;
    }
}

function _timestampToTime(timestamp, wrap24hours = false) {
    let date = new Date(timestamp * 1000);
    let hour = date.getHours().toString().padStart(2, '0');
    let min = date.getMinutes().toString().padStart(2, '0');
    let sec = date.getSeconds().toString().padStart(2, '0');
    return `${hour}:${min}:${sec}`;

}

function _secondsToTime(seconds) {
    seconds = Math.round(seconds);

    let hour = Math.floor(seconds / 60 / 60);
    const min = Math.floor(seconds / 60);
    const sec = seconds - min * 60;


    let text = "";
    text += hour + ":";
    text += (min % 60).toString().padStart(2, '0') + ":";
    text += sec.toString().padStart(2, '0');

    return text;
}

function updateTimeRangeDisplay() {
    timedropdown.selectedIndex = 0;
    customOptionSelect.value = _getTimeRange();
    customOptionSelect.innerHTML = _secondsToTime(_getTimeRange());
}

function _getValuesForVisibleTimeRange(categoryData, entryName) {
    const values = categoryData["entries"][entryName];
    let timeRange = _getTimeRange();

    // Find first value that does not fall into timerange
    let beginIndex = 0;
    let endIndex = values.length;

    for (let i=values.length - 1; i > 0; --i) {
        if (values[i][0] <= rightValueBound) {
            endIndex = i;
            break;
        }
    }
    for (let i=values.length - 1; i > 0; --i) {
        if (values[i][0] < rightValueBound - timeRange) {
            beginIndex = i;
            break;
        }
    }

    // Use values before and after to avoid empty spaces on the sides of the graph
    beginIndex = Math.max(0, beginIndex - 1);
    endIndex = endIndex + 2; // no check necessary, slice stops when out of bounds
    return _prepareData(values.slice(beginIndex, endIndex));
}

function _prepareData(values) {
    if (!averageData)
        return values;

    const newArray = [];

    const stepTimeRange = Math.round(_getTimeRange() / parseFloat(graphSteps));

    let avgSum = [0, 0];
    let startTimestamp = values[0][0];
    let avgCounter = 0;

    // Add first value manually to always have a value on the left side
    newArray.push(values[0]);

    // Prepare data
    for (let i=1; i<values.length - 1; ++i) {
        if (values[i][0] - startTimestamp > stepTimeRange && avgCounter > 0)
        {
            startTimestamp = values[i][0];

            newArray.push([avgSum[0] / avgCounter, avgSum[1] / avgCounter]);
            avgSum = [0, 0];
            avgCounter = 0;
        }

        avgSum[0] += values[i][0];
        avgSum[1] += values[i][1];
        ++avgCounter;
    }

    // when loop exists without completing last set
    if (avgCounter > 0){
        newArray.push([avgSum[0] / avgCounter, avgSum[1] / avgCounter]);
    }

    // add last value manually to be always accurate
    newArray.push(values[values.length-1]);

    // console.log("From ", values.length, " to ", newArray.length, "values.")
    return newArray;
}

function _updateCanvas(category_data, canvas) {
    if (category_data["settings"].includes("nograph"))
        return;

    let keys = Object.keys(category_data["entries"])
    let ctx = canvas.getContext("2d");

    let width = canvas.scrollWidth;
    let height = canvas.scrollHeight;
    canvas.width = width;
    canvas.height = height;

    // find highest value
    let minValue = category_data["max"];
    let maxValue = category_data["min"];
    let avg = 0;
    let avgCounter = 0;

    for (const key of keys) {
        let allValues = _getValuesForVisibleTimeRange(category_data, key);

        // find minValue and maxValue
        for (let i=1; i<allValues.length; ++i)
        {
            let actualValue = allValues[i][1];
            maxValue = Math.max(maxValue, actualValue);
            minValue = Math.min(minValue, actualValue);
            avg += actualValue;
            ++avgCounter;
        }
    }
    avg /= avgCounter;

    let timeStampConsideringServerDelay = 0;

    for (const key of keys) {
        const allValues = category_data["entries"][key];
        timeStampConsideringServerDelay = Math.max(timeStampConsideringServerDelay, allValues[allValues.length -1][0])
    }

    // Avoid gap on the right side due to server delay
    const serverDelta = last_server_sync_timestamp - timeStampConsideringServerDelay;

    function _getX(timestamp) {
        let diff = rightValueBound - timestamp - serverDelta;
        let x =  width - diff / _getTimeRange() * width;
        return x;
    }

    function _getY(min, max, value) {
        let range = max - min;
        let factor = (value-min) / range;
        let result = factor * height;
        return height - result;
    }

    // Draw grid
    ctx.strokeStyle = "#666";
    ctx.lineWidth = 1;
    ctx.beginPath();

    // Horizontal lines
    const y = _getY(category_data["min"], category_data["max"], (category_data["min"] + category_data["max"]) / 2);
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);

    ctx.moveTo(0, y*0.5);
    ctx.lineTo(width, y*0.5);

    ctx.moveTo(0, y * 1.5);
    ctx.lineTo(width, y * 1.5);

    // Vertical lines
    const right = rightValueBound;
    const timerange = _getTimeRange();
    const left = Math.round(rightValueBound - timerange);

    function _drawSeparators(everyNthSeconds) {
        everyNthSeconds = Math.round(everyNthSeconds);
        for (let i = 0; i < timerange; ++i)
        {
            if ((left + i) % everyNthSeconds == 0) {
                ctx.moveTo(_getX(left + i), 0);
                ctx.lineTo(_getX(left + i), height);
            }
        }
    }

    // TODO improve
    if (false) _drawSeparators(timerange / 4);
    else if (false) _drawSeparators(Math.round((timerange / 60) * 10) / 10*60);
    else if (timerange <= 60*1.25) _drawSeparators(7);
    else if (timerange <= 60*2.5) _drawSeparators(15);
    else if (timerange <= 60*5) _drawSeparators(30);
    else if (timerange <= 60*10) _drawSeparators(60);
    else if (timerange <= 60*20) _drawSeparators(60*2);
    else if (timerange <= 60*40) _drawSeparators(60*4);
    else if (timerange <= 60*80) _drawSeparators(60*8);
    else if (timerange <= 60*160) _drawSeparators(60*16);
    else if (timerange <= 60*320) _drawSeparators(60*32);
    else if (timerange <= 60*60*24) _drawSeparators(60*60);

    else {
            ctx.moveTo(width * 0.25, 0);
            ctx.lineTo(width * 0.25, height);

            ctx.moveTo(width * 0.5, 0);
            ctx.lineTo(width * 0.5, height);

            ctx.moveTo(width * 0.75, 0);
            ctx.lineTo(width * 0.75, height);
    }

    ctx.stroke();

    // Create lines in graph
    colorCounter = 0;
    for (const key of keys) {
        let color = availableColors[colorCounter % availableColors.length];

        colorCounter += 1;

        let allValues = _getValuesForVisibleTimeRange(category_data, key);

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(_getX(allValues[0][0]), _getY(category_data["min"], category_data["max"], allValues[0][1]));

        for (let i=1; i<allValues.length; ++i)
        {
            let val = allValues[i];
            let timestamp = val[0];
            let actualValue = val[1];

            ctx.lineTo(
                _getX(timestamp),
                _getY(category_data["min"], category_data["max"], actualValue)
            );
        }
        ctx.stroke();
    }

    function _drawLimit(value, drawLine=true, label="") {
        let limitY = _getY(category_data["min"], category_data["max"], value);

        // Draw line
        if (drawLine) {
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 1;
            ctx.setLineDash([15, 15]);

            ctx.beginPath();
            ctx.moveTo(0, limitY);
            ctx.lineTo(width, limitY);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Draw text
        let text = Math.round(value*100)/100 + category_data["unit"]
        let fontSize = 36;
        let fontOffset = fontSize * 0.5;
        let fontPosY = limitY + fontOffset;
        fontPosY = Math.max(fontOffset * 2, Math.min(height-fontOffset * 0.5, fontPosY))

        ctx.font = fontSize + "px Oswald";
        ctx.textAlign = "left";
        ctx.strokeStyle = "#333";
        ctx.lineWidth = 12;
        ctx.strokeText(label + text, 10, fontPosY);
        ctx.fillStyle = "#ddd";
        ctx.fillText(label + text, 10, fontPosY);
    }
    _drawLimit(category_data["min"], false);
    _drawLimit(category_data["max"], false);
    _drawLimit(minValue);
    _drawLimit(maxValue);
    // _drawLimit(avg, true, "Average: ");

    // Draw cursor
    ctx.strokeStyle = "#0f0";
    ctx.lineWidth = 1;
    ctx.setLineDash([15, 15]);

    // FIXME key is not needed here
    let cursorTimeSnapped;
    for (const key of keys) {
        cursorTimeSnapped = _getValueAtCursor(category_data, key)[0];
        // Should not 'break' if values would be written to DB in different time steps
        // But would need to find closest match
        break;
    }
    const cursorX = _getX(cursorTimeSnapped);
    ctx.beginPath();
    ctx.moveTo(cursorX, 0);
    ctx.lineTo(cursorX, height);
    ctx.stroke();

    /* // Draw cursor position without snapping
    ctx.strokeStyle = "#0ff";
    ctx.beginPath();
    ctx.moveTo(_getX(_cursorPos), 0);
    ctx.lineTo(_getX(_cursorPos), height);
    ctx.stroke();
    // */
    ctx.setLineDash([]);

    let text = _timestampToTime(cursorTimeSnapped, true);
    let fontSize = 36;
    let fontPosX = Math.max(0, Math.min(cursorX, width));
    let fontPosY = fontSize + 5;

    ctx.font = fontSize + "px Oswald";
    if (cursorTimeSnapped < rightValueBound - _getTimeRange() * 0.75) // lower quarter
        ctx.textAlign = "left";
    else if (cursorTimeSnapped > rightValueBound - _getTimeRange() * 0.25) // upper quarter
        ctx.textAlign = "right";
    else
        ctx.textAlign = "center";

    ctx.strokeStyle = "#333";
    ctx.lineWidth = 12;
    ctx.strokeText(text, fontPosX, fontPosY);
    ctx.fillStyle = "#0f0";
    ctx.fillText(text, fontPosX, fontPosY);
}

function _generateEntry(category, keys, category_data) {
    categoryElements = {};

    // Create text table rows
    let table = document.getElementById("table");

    let graphWrapper = document.createElement("div");
    let att = document.createAttribute("class");
    att.value = "graphWrapper";
    graphWrapper.setAttributeNode(att);

    // Create category title
    let tr = document.createElement("tr");
    att = document.createAttribute("class");
    att.value = "tr categoryTitle";
    tr.setAttributeNode(att);
    tr.innerText = category.toUpperCase();

    graphWrapper.appendChild(tr);

    // Create rows
    let colorCounter = 0;
    for (const key of keys)
    {
        let rowElement = {};
        let color = availableColors[colorCounter % availableColors.length];

        // Only use different colors if there is a graph
        // if (!category_data["settings"].includes("nograph"))
        colorCounter += 1;

        tr = document.createElement("div");
        att = document.createAttribute("class");
        att.value = "tr";
        tr.setAttributeNode(att);

        // Label
        td = document.createElement("td");
        att = document.createAttribute("class");
        att.value = "td collabel";
        td.setAttributeNode(att);

        rowElement["label"] = td;

        tr.appendChild(td);

        // Value
        td = document.createElement("td");
        att = document.createAttribute("class");
        att.value = "td colval";
        td.setAttributeNode(att);

        rowElement["value"] = td;
        tr.appendChild(td);

        att = document.createAttribute("align");
        att.value = "right";
        td.setAttributeNode(att);

        // Bar
        td = document.createElement("td");
        att = document.createAttribute("class");
        att.value = "td";
        td.setAttributeNode(att);

        att = document.createAttribute("align");
        att.value = "right";
        td.setAttributeNode(att);

        att = document.createAttribute("class");
        att.value = "td bar";
        td.setAttributeNode(att);

        rowElement["bar"] = td;

        tr.appendChild(td);

        att = document.createAttribute("style");
        att.value = "color:" + color;
        tr.setAttributeNode(att);
        graphWrapper.appendChild(tr);

        categoryElements[key] = rowElement;
    }

    // do once
    // create canvas
    if (!category_data["settings"].includes("nograph"))
    {
        tr = document.createElement("tr");
        att = document.createAttribute("class");
        att.value = "tr canvastd";
        tr.setAttributeNode(att);

        let canvas = document.createElement("canvas");
        canvas.onmousedown = (ev) => {_onCanvasMouseDown(ev, canvas)};
        canvas.onmouseup = (ev) => {_onCanvasMouseUp(ev, canvas)};
        canvas.onmousemove = (ev) => {_onCanvasMouseMove(ev, canvas)};

        canvas.ontouchstart = (ev) => {_onCanvasMouseDown(ev, canvas)};
        canvas.ontouchend = (ev) => {_onCanvasMouseUp(ev, canvas)};
        canvas.ontouchmove = (ev) => {_onCanvasMouseMove(ev, canvas)};

        tr.appendChild(canvas);
        graphWrapper.appendChild(tr);

        // Done building DOM-Tree.
        categoryElements["canvas"] = canvas;
    }
    elements[category] = categoryElements;
    table.appendChild(graphWrapper);
}

function storeSettings() {
    localStorage.setItem('autoreload', autoReload);
    localStorage.setItem('timerange', _timeRange);
    localStorage.setItem('debugmode', debugMode);
}

function restoreSettings() {
    autoReload = JSON.parse(localStorage.getItem('autoreload'));
    _timeRange = JSON.parse(localStorage.getItem('timerange'));
    debugMode = JSON.parse(localStorage.getItem('debugmode'));

    // Load defaults if value is missing in local storage
    if (autoReload === null)
        autoReload = DEFAULT_AUTO_RELOAD;
    if (isNaN(_timeRange))
        _timeRange = DEFAULT_TIME_RANGE;
    if (debugMode === null)
        debugMode = false;
}

function toggleAutoReload() {
    autoReload = !autoReload;
    storeSettings();

    if (autoReload) {
        _requestData();
        activateAutoUpdate();
    } else {
        clearInterval(interval);
        interval = null;
    }

    _updateReloadState();
}

function reloadOnce() {
    if (!autoReload)
        _requestData();

}

function _updateReloadState() {
    if (autoReload) {
        reloadState.innerHTML = ("Reloading data");
        reloadState.style.color = "#000";
        reloadState.style.backgroundColor = "#33a130"; // green
    } else {
        reloadState.innerHTML = ("Paused");
        reloadState.style.color = "#ddd";
        reloadState.style.backgroundColor = "#666";
    }
}

function _getTimeRanges() {
    return timeRanges;
}

function setTimeRange(dropdownIndex) { // TODO return [leftBound, rightBound]?

    _timeRange = _getTimeRanges()[dropdownIndex - 1]; // -1 because of 'custom' entry showing current timerange
    changeTimeRange(0); // to trigger necessary updates
}

function _getTimeRange() {
    return _timeRange;
}

function _updateOldestTimeStamp() {
    let categories = cachedData["categories"];
    let tmpOldestTimestamp = last_server_sync_timestamp;

    for (let categoryName in categories)
    {
        const category_data = categories[categoryName];
        for (let entryName in category_data["entries"]) {
            const allValues = category_data["entries"][entryName];
            tmpOldestTimestamp = Math.min(tmpOldestTimestamp, allValues[0][0])
        }
    }
    oldestTimeStamp = tmpOldestTimestamp;
}

function changeTimeRange(delta) {
    // Calculate timerangeOffset based on cursor

    // Store previous values
    const oldTimeRange = _getTimeRange();
    const oldRight = rightValueBound;

    const percRight = (oldRight - _cursorPos) / oldTimeRange;

    // Change to new timerange
    //currentTimeIndex += delta;
    _timeRange += delta;

    _timeRange = Math.max(10, Math.min(last_server_sync_timestamp - oldestTimeStamp, _timeRange)); // TODO CLAMP
    _timeRange = Math.round(_timeRange);

    // Calculate new timerange position
    rightValueBound = _cursorPos + _getTimeRange() * (percRight);

    // Update UI
    updateTimeRangeDisplay();
    _updateGraphs();

    storeSettings();
}

function highlightClick(button) {
    let origColor = button.style.backgroundColor;

    button.style.backgroundColor = "#999";

    setTimeout(() => {
        button.style.backgroundColor = origColor;
    }, 150);
}

function _updateDebugMode(check=true) {
    if (debugMode)
        enableDebugMode(check);
    else
        disableDebugMode(check);
}

function enableDebugMode(check=true) {
    if (debugMode === true && check)
        return;

    debugMode = true;
    wrapper.appendChild(debugArea);
    wrapper.appendChild(debugOverlay);

    storeSettings();
}

function disableDebugMode(check=true) {
    if (debugMode === false && check)
        return;

    debugMode = false;
    debugCounter = 0;

    debugArea.remove();
    debugOverlay.remove();

    storeSettings();
}

function timedisplayClicked() {
    debugCounter += 1;

    if (debugCounter >= 3)
        enableDebugMode();
}

function onDebugPressed() {
    disableDebugMode();
}

function _onCanvasMouseDown(ev, canvas) {
    const rect = ev.target.getBoundingClientRect();
    const clientY = ev.touches[0].clientY - rect.top;

    if (ev.touches.length == 1) {
        if (clientY < canvas.height * 0.5) {
            singleTouchStart = ev.touches[0].clientX - rect.left;

            // Place cursor where touch happened
            // Comment out to scrub to change position without placing initially
            const timeRange = _getTimeRange(); // same as == 2
            const rightBound = rightValueBound;
            const leftBound = rightBound - timeRange;

            _cursorPos = (singleTouchStart * timeRange / parseFloat(canvas.width)) + leftBound;
            _cursorPos = Math.min(rightBound, Math.max(leftBound, _cursorPos));

            window.requestAnimationFrame(_updateGraphs);

            ev.preventDefault();

        } else {
            touchStartX = 0;
            for (let touch of ev.touches){
                touchStartX += touch.clientX;
            }
            touchStartX /= ev.touches.length;
            ev.preventDefault();
        }
    } else if (ev.touches.length == 2) {
        _onCanvasMouseUp(ev); // cancel one-touch stuff
        currentPinchDiff = Math.abs(ev.touches[0].clientX - ev.touches[1].clientX);
    }

}

function _onCanvasMouseUp(ev, canvas) {
    singleTouchStart = null;
    touchStartX = null;
    ev.preventDefault();
}

function _onCanvasMouseMove(ev, canvas) {
    const rect = ev.target.getBoundingClientRect();
    // const clientY = ev.touches[0].clientY - rect.top;
    const timeRange = _getTimeRange();

    if (ev.touches.length == 1){

        if (singleTouchStart) {
            const clientX = ev.touches[0].clientX - rect.left;
            _cursorPos += (clientX - singleTouchStart) * timeRange / canvas.width;

            singleTouchStart = clientX;

        } else if (touchStartX) {
            let clientX = 0;
            let scrollWidth = canvas.width;

            for (let touch of ev.touches) {
                clientX += touch.clientX;
            }

            clientX /= ev.touches.length;


            rightValueBound -= (clientX - touchStartX) * timeRange / scrollWidth;
            _updateTimeRangeOffset();

            touchStartX = clientX;
        }
    } else if (ev.touches.length == 2) {
        const previousPinchDiff = currentPinchDiff;
        currentPinchDiff = Math.abs(ev.touches[0].clientX - ev.touches[1].clientX);

        let delta = previousPinchDiff - currentPinchDiff;
        changeTimeRange(delta * timeRange / canvas.width);
    }

    _clampCursorToVisibleRange();
    window.requestAnimationFrame(_updateGraphs);
    ev.preventDefault();
}

function _updateTimeRangeOffset() {
    const timeRange = _getTimeRange();
    const smallestValue = oldestTimeStamp + timeRange;

    rightValueBound = Math.min(last_server_sync_timestamp, Math.max(smallestValue, rightValueBound))

    // Align lines to the right if not enough information to fill graph completely
    if (last_server_sync_timestamp - oldestTimeStamp < timeRange)
        rightValueBound = last_server_sync_timestamp;
}

function toggleDataPreparation() {
    averageData = !averageData;
    _updatePrepareDataButtonLabel();
    _updateGraphs();
}

function changePreparationResolution(delta) {
    if (delta != 0) // needed for initial call...
        averageData = true;

    graphSteps *= 1 + (delta * 0.2);
    graphSteps = Math.round(Math.max(12, Math.min(graphSteps, 500)));

    _updatePrepareDataButtonLabel();
    _updateGraphs();
}

function _updatePrepareDataButtonLabel() {
    if (averageData)
        prepareDataButton.innerHTML = "Steps: " + graphSteps;
    else
        prepareDataButton.innerHTML = "No steps";
}

function _clampCursorToVisibleRange() {
    _cursorPos = Math.min(rightValueBound, Math.max(rightValueBound - _getTimeRange(), _cursorPos));
    _cursorPos = Math.max(_cursorPos, oldestTimeStamp); // avoid going to ranges where there are no value
}

function log(text) {
    infoLine.innerHTML = text;
}

// source: https://stackoverflow.com/questions/1248302/how-to-get-the-size-of-a-javascript-object
function roughSizeOfObject( object ) {
    var objectList = [];
    var stack = [ object ];
    var bytes = 0;

    while ( stack.length ) {
        var value = stack.pop();

        if ( typeof value === 'boolean' ) {
            bytes += 4;
        }
        else if ( typeof value === 'string' ) {
            bytes += value.length * 2;
        }
        else if ( typeof value === 'number' ) {
            bytes += 8;
        }
        else if
        (
            typeof value === 'object'
            && objectList.indexOf( value ) === -1
        )
        {
            objectList.push( value );

            for( var i in value ) {
                stack.push( value[ i ] );
            }
        }
    }
    return bytes;
}
function humanizeBytes(bytes) {
    return (Math.round((bytes / 1024 / 1024) * 1000) / 1000) + " MB";
}