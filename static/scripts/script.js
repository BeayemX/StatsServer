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
const RELOAD_MINIMUM_TIME_MS = 1000;
const INACTIVE_COLOR = "#777";
const timeRanges = [60, 60*5, 60*10, 60*30, 60*60, 60*60 * 6, 60*60 * 12, 60*60*24];

const INCLUDE_CURRENT_VALUE = false;
const autoscale = true; // TODO should be category setting
const autoScaleOuterSpaceFactor = 0.1;

const drawSnappingCircles = true; // TODO should be category setting
const useSnappedValueColorForCursor = true;

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

    // Setting value and innerHTML for customOptionSelect not needed
    // Will trigger update automatically when values are loaded
    let option = customOptionSelect
    timedropdown.appendChild(option);

    for (let time of _getTimeRanges()) {
        option = document.createElement('option');
        option.value = time;
        option.innerHTML = _humanizeTime(time);
        timedropdown.appendChild(option);
    }




    // Set up DOM elements / Initialize elements
    _updateDebugMode(false); // TODO why is this called two times?

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

let waitingForRequest = false;
function _requestData() {
    if (waitingForRequest) {
        return;
    }

    waitingForRequest = true;

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
    waitingForRequest = false;

    console.log("handleDataUpdate")
    newServerData = JSON.parse(data_json_s);
    log("Handle update... " + humanizeBytes(newServerData["size"]));

    if (newServerData["use_delta_compression"]) {
        let categories = newServerData["categories"];
        for (let categoryName in categories)
        {
            let categoryData = categories[categoryName];
            for (let entryName in categoryData["entries"])
            {
                let entryData = categoryData["entries"][entryName];
                let values = entryData["values"];

                for (let i = 1; i < values.length; ++i) {
                    for (let j = 0; j < values[i].length; ++j) {
                        values[i][j] = values[i-1][j] + values[i][j];
                    }
                }
            }
        }
    }

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
    // TODO maybe special case for initial load not needed?
    if (cachedData == null) // Just started the app, cache new data
    {
        cachedData = newServerData;

        // Add current value to values
        if (INCLUDE_CURRENT_VALUE) {
            let categories = newServerData["categories"];
            for (let categoryName in categories)
            {
                let categoryData = categories[categoryName];
                for (let label in categoryData["entries"])
                {
                    let entryData = categoryData["entries"][label];
                    cachedData["categories"][categoryName]["entries"][label]["values"].push([last_server_sync_timestamp, entryData["value"]]); // add current value to values
                }
            }
        }
    } else { // add new values to cached data
        // TODO extract some variables?
        let categories = newServerData["categories"];
        for (let categoryName in categories)
        {
            let categoryData = categories[categoryName];
            for (let label in categoryData["entries"])
            {
                let entryData = categoryData["entries"][label];
                if (INCLUDE_CURRENT_VALUE) {
                    cachedData["categories"][categoryName]["entries"][label]["value"] = entryData["value"];
                }

                if (INCLUDE_CURRENT_VALUE)
                    cachedData["categories"][categoryName]["entries"][label]["values"].pop(); // remove PREVIOUS current ["value"]
                if (cachedData["categories"][categoryName]) {
                    if (cachedData["categories"][categoryName]["entries"][label]) {
                        cachedData["categories"][categoryName]["entries"][label]["values"] = cachedData["categories"][categoryName]["entries"][label]["values"].concat(entryData["values"]); // add new value-list to cached value-list
                    } else { // new label, not existing on initial load
                        cachedData["categories"][categoryName]["entries"][label] = entryData;
                        elements[categoryName]._generateLabelEntry(label, categoryName, categoryData);
                    }
                } else { // new category, not existing on initial load
                    cachedData["categories"][categoryName] = newServerData["categories"][categoryName]
                    _createDomCategory(categoryName, newServerData["categories"][categoryName])
                }
                if (INCLUDE_CURRENT_VALUE) {
                    cachedData["categories"][categoryName]["entries"][label]["values"].push([last_server_sync_timestamp, entryData["value"]]); // add NEW current value to values
                }
            }
        }
    }

    // Initial creation of dom tree
    if (elements == null) {
        elements = {};
        let categories = newServerData["categories"]; // TODO use cached data?
        for (let category in categories) {
            let categoryData = categories[category];
            _createDomCategory(category, categoryData)
        }
    }

    _updateGraphs();
}
function _createDomCategory(category, categoryData) {
    console.log(category);
    console.log(categoryData);
    _generateEntry(category, Object.keys(categoryData["entries"]), categoryData);
}

function _updateGraphs() {
    if (!cachedData)
        return;

    // Prepare for drawing
    _updateOldestTimeStamp();
    _updateTimeRangeOffset();

    // Actual drawing
    for (let categoryName in elements) {

        let categoryData = cachedData["categories"][categoryName]
        _updateBars(categoryData, categoryName);
        _updateCanvas(categoryName, categoryData, elements[categoryName].canvas);
    }
}

function getCursorTime() {
    return _cursorPos;
}

function _getValueAtCursor(categoryData, label) {
    let allValues = _getValuesForVisibleTimeRange(categoryData, label); // ASDF cursor snapping should work for all labels not just [0]
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

    for (const label of Object.keys(categoryData["entries"])) {
        const color = _getElementColor(categoryName, label);

        // Label
        elements[categoryName].labels[label]["label"].innerText = label;

        // Value
        const value = _getValueAtCursor(categoryData, label)[1];

        if (categoryData["entries"][label]["unit"] == "byte") {
            elements[categoryName].labels[label]["value"].innerText = humanizeBytes(value);
        } else {
            elements[categoryName].labels[label]["value"].innerText = (Math.round(value * 100) / 100) + categoryData["entries"][label]["unit"];
        }

        // Bar
        let min = categoryData["entries"][label]["min"];
        let max = categoryData["entries"][label]["max"];
        let neededPerc = ((value - min) / (max - min));
        let text = "";
        let canvas = elements[categoryName].labels[label]["bar"];

        let width = canvas.scrollWidth;
        let height = canvas.scrollHeight;
        canvas.width = width;
        canvas.height = height;

        let ctx = canvas.getContext("2d");
        let indicatorSize = 3;

        let catElement = elements[categoryName].labels[label]

        ctx.strokeStyle = catElement["active"] ? catElement["color"] : color;
        ctx.lineWidth = height;
        ctx.setLineDash([indicatorSize, indicatorSize * 2]);

        // Snap to full bar size
        let length = Math.round(neededPerc * width / indicatorSize) * indicatorSize;
        let halfHeight = height * 0.5;
        ctx.beginPath();
        ctx.moveTo(0, halfHeight);
        ctx.lineTo(length, halfHeight);
        ctx.stroke();

        if (debugMode)
        {
            ctx.lineWidth = indicatorSize;
            let targetY = height - indicatorSize * 0.5;
            ctx.beginPath();
            ctx.moveTo(0, targetY);
            ctx.lineTo(width, targetY);
            ctx.stroke();
        }

        ctx.setLineDash([]);
    }
}

function _timestampToTime(timestamp) {
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
    if (hour > 0)
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
    const values = categoryData["entries"][entryName]["values"];
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

function _getActiveEntries(categoryName, categoryData) {
    const activeEntries = [];

    for (const entryName of Object.keys(categoryData["entries"]))
    {
        if (elements[categoryName].labels[entryName]["active"])
            activeEntries.push(entryName);
    }

    return activeEntries;
}

function _updateCanvas(categoryName, categoryData, canvas) {
    if (categoryData["settings"].includes("nograph"))
        return;

    let labels = _getActiveEntries(categoryName, categoryData);
    let ctx = canvas.getContext("2d");

    // TODO why do this on update, wouldnt it be sufficient to do it when creating?
    // maybe because when creating canvas it is not in the DOM tree yet and therefore it
    // won't have any size...
    let width = canvas.scrollWidth;
    let height = canvas.scrollHeight;
    canvas.width = width;
    canvas.height = height;

    const minMaxValues = {};

    minMaxValues["globalMin"] = Infinity;
    minMaxValues["globalMax"] = -Infinity;

    for (const label of labels) {
        let minValue = Infinity;
        let maxValue = -Infinity;
        let avg = 0;
        let avgCounter = 0;

        // find min / max values
        let allValues = _getValuesForVisibleTimeRange(categoryData, label);

        for (let i = 1; i < allValues.length; ++i)
        {
            let actualValue = allValues[i][1];
            minValue = Math.min(minValue, actualValue);
            maxValue = Math.max(maxValue, actualValue);

            minMaxValues["globalMin"] = Math.min(minMaxValues["globalMin"], actualValue);
            minMaxValues["globalMax"] = Math.max(minMaxValues["globalMax"], actualValue);

            avg += actualValue;
            ++avgCounter;
        }

        avg /= avgCounter;

        minMaxValues[label] = {};
        minMaxValues[label]["min"] = minValue;
        minMaxValues[label]["max"] = maxValue;

        minMaxValues[label]["avg"] = avg;
    }

    function _getX(timestamp) {
        const diff = rightValueBound - timestamp;
        return width - diff / _getTimeRange() * width;
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
    ctx.moveTo(0, height * 0.25);
    ctx.lineTo(width, height * 0.25);

    ctx.moveTo(0, height * 0.5);
    ctx.lineTo(width, height * 0.5);

    ctx.moveTo(0, height * 0.75);
    ctx.lineTo(width, height * 0.75);

    // Vertical lines
    // const right = rightValueBound;
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


    // Create graph lines
    for (const label of labels) {
        if (!elements[categoryName].labels[label]["active"])
            continue;

        let allValues = _getValuesForVisibleTimeRange(categoryData, label);
        const color = _getElementColor(categoryName, label);

        // Draw graph
        let minValue = categoryData["entries"][label]["min"];
        let maxValue = categoryData["entries"][label]["max"];

        if (elements[categoryName].autoScale) {
            const range = minMaxValues["globalMax"] - minMaxValues["globalMin"];

            minValue = minMaxValues["globalMin"] - range * autoScaleOuterSpaceFactor;
            maxValue = minMaxValues["globalMax"] + range * autoScaleOuterSpaceFactor;
        }

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(_getX(allValues[0][0]), _getY(minValue, maxValue, allValues[0][1]));

        for (let i=1; i<allValues.length; ++i)
        {
            let val = allValues[i];
            let timestamp = val[0];
            let actualValue = val[1];

            ctx.lineTo(
                _getX(timestamp),
                _getY(minValue, maxValue, actualValue)
            );
        }
        ctx.stroke();
    }
    // HACK, due to missing min/max information
    categoryData["min"] = 0
    categoryData["max"] = 100
    let usedMin = categoryData["min"];
    let usedMax = categoryData["max"];

    if (elements[categoryName].autoScale) {
        usedMin = minMaxValues["globalMin"];
        usedMax = minMaxValues["globalMax"];

        const range = minMaxValues["globalMax"] - minMaxValues["globalMin"];
        usedMin = minMaxValues["globalMin"] - range * autoScaleOuterSpaceFactor;
        usedMax = minMaxValues["globalMax"] + range * autoScaleOuterSpaceFactor;
    }
    // HACK end

    categoryData["unit"] = "%";
    // Draw global limits
    if (categoryData["settings"].includes("draw_global_limits") || categoryData["settings"].includes("draw_global_limit_min") || categoryData["settings"].includes("draw_global_limit_max")) {
        if (categoryData["settings"].includes("draw_global_limits") || categoryData["settings"].includes("draw_global_limit_min"))
            _drawLimit(minMaxValues["globalMin"], usedMin, usedMax, categoryData["unit"], "#ddd");
        if (categoryData["settings"].includes("draw_global_limits") || categoryData["settings"].includes("draw_global_limit_max"))
            _drawLimit(minMaxValues["globalMax"], usedMin, usedMax, categoryData["unit"], "#ddd");
    }
    if (categoryData["settings"].includes("draw_outer_limits") || categoryData["settings"].includes("draw_outer_limit_min")) {
        _drawLimit(usedMin, usedMin, usedMax, categoryData["unit"], "#ddd", false);
    }
    if (categoryData["settings"].includes("draw_outer_limits") || categoryData["settings"].includes("draw_outer_limit_max")) {
        _drawLimit(usedMax, usedMin, usedMax, categoryData["unit"], "#ddd", false);
    }

    // Draw individual limits

    for (const label of labels) {
        // let allValues = _getValuesForVisibleTimeRange(categoryData, label); // was probably used for calculating average?
        const color = _getElementColor(categoryName, label);

        if (categoryData["settings"].includes("draw_individual_limits") || categoryData["settings"].includes("draw_individual_limit_min") || categoryData["settings"].includes("draw_individual_limit_max")) {
            const minValue = minMaxValues[label]["min"];
            const maxValue = minMaxValues[label]["max"];

            // Draw limits
            if (categoryData["settings"].includes("draw_individual_limits") || categoryData["settings"].includes("draw_individual_limit_min"))
                _drawLimit(minValue, categoryData["entries"][label]["min"], categoryData["entries"][label]["max"], categoryData["entries"][label]["unit"], color, !elements[categoryName].autoScale);
            if (categoryData["settings"].includes("draw_individual_limits") || categoryData["settings"].includes("draw_individual_limit_max"))
                _drawLimit(maxValue, categoryData["entries"][label]["min"], categoryData["entries"][label]["max"], categoryData["entries"][label]["unit"], color, !elements[categoryName].autoScale);
            // _drawLimit(avg, label, color, true, "Average: ");
        }
    }

    function _drawLimit(value, min, max, unit, color, drawLine=true, label="") {
        let limitY = _getY(min, max, value);

        // Draw line
        if (drawLine) {
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.setLineDash([15, 15]);

            ctx.beginPath();
            ctx.moveTo(0, limitY);
            ctx.lineTo(width, limitY);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Draw text
        let text = "";
        if (unit == "byte") {
            text = humanizeBytes(value);
        } else {
            text = Math.round(value * 100) / 100 + unit;
        }

        let fontSize = 36;
        let fontOffset = fontSize * 0.5;
        let fontPosY = limitY + fontOffset;
        fontPosY = Math.max(fontOffset * 2, Math.min(height-fontOffset * 0.5, fontPosY))

        ctx.font = fontSize + "px Oswald";
        ctx.textAlign = "left";
        ctx.strokeStyle = "#333";
        ctx.lineWidth = 12;
        ctx.strokeText(label + text, 10, fontPosY);
        ctx.fillStyle = color; // "#ddd";
        ctx.fillText(label + text, 10, fontPosY);
    }

    // Snap cursor to closes value (considering all lines)
    let cursorTimeSnapped;
    const contenders = {};
    for (const label of labels) {
        const snappedValue = _getValueAtCursor(categoryData, label);
        cursorTimeSnapped = snappedValue[0];
        cursorTimeSnappedValue = snappedValue[1];

        // Should not 'break' if values would be written to DB in different time steps
        // But would need to find closest match
        contenders[label] = (cursorTimeSnapped);
        if (drawSnappingCircles) {
            ctx.beginPath();
            ctx.lineWidth = 2;
            ctx.strokeStyle = elements[categoryName].getColorForEntry(label);
            ctx.setLineDash([]);
            ctx.arc(_getX(cursorTimeSnapped), _getY(usedMin, usedMax, cursorTimeSnappedValue), 15, 0, 360);
            ctx.stroke();
        }
    }

    let contenderLabel = 0; // not needed?
    let contenderDist = Infinity;

    // for (let i = 0; i < contenders.length; ++i) {
    for (let label in contenders) {
        const newDist = Math.abs(getCursorTime() - contenders[label]);

        if (newDist < contenderDist) {
            contenderDist = newDist;
            contenderLabel = label;
        }
    }

    cursorTimeSnapped = contenders[contenderLabel];

    // Draw cursor
    if (useSnappedValueColorForCursor)
        ctx.strokeStyle = elements[categoryName].getColorForEntry(contenderLabel);
    else
        ctx.strokeStyle = "#0f0";

    ctx.lineWidth = 1;
    ctx.setLineDash([15, 15]);

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

    let text = _timestampToTime(cursorTimeSnapped);
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

function _generateEntry(category, labels, categoryData) {
    // Create text table rows
    let table = document.getElementById("table");

    const categoryDiv = new CategoryWrapper(category, labels, categoryData);
    elements[category] = categoryDiv;

    table.appendChild(categoryDiv.wrapper);
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
        //reloadState.innerHTML = ("&#x25BA;");
        reloadState.innerHTML = ("Live updates");
        reloadState.style.color = "#000";
        reloadState.style.backgroundColor = "#33a130"; // green
    } else {
        //reloadState.innerHTML = ("&#x25A0;");
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
        const categoryData = categories[categoryName];
        for (let entryName in categoryData["entries"]) {
            const allValues = categoryData["entries"][entryName]["values"];
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

    _updateGraphs(); // to show/hide lenght indicator dots for bars
}

function enableDebugMode(check = true) {
    if (debugMode === true && check)
        return;

    debugMode = true;
    wrapper.appendChild(debugArea);
    wrapper.appendChild(debugOverlay);

    storeSettings();
    _updateGraphs(); // to update lenght indicator for bars
}

function disableDebugMode(check=true) {
    if (debugMode === false && check)
        return;

    debugMode = false;
    debugCounter = 0;

    debugArea.remove();
    debugOverlay.remove();

    storeSettings();
    _updateGraphs(); // to update lenght indicator for bars
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

const conversionFactor = 1024.0;
const units = ["B", "KB", "MB", "GB", "TB", "PB"];

function humanizeBytes(bytes) {
    bytes = Math.round(bytes); // when calculating average bytes can be float

    let idx = 0;
    while (bytes >= conversionFactor && idx < units.length - 1) {
        bytes = bytes / conversionFactor;
        idx += 1;
    }

    const decimals = bytes >= 100 ? 1 : 2;
    return roundToDecimals(bytes, decimals) + " " + units[idx];
}

// UTILITIES
function roundToDecimals(value, decimals) {
    const power = Math.pow(10, decimals);
    return (Math.round(value * power) / power);
}

function _humanizeTime(sec) {
    const hours   = Math.floor(sec / 3600);
    const minutes = Math.floor((sec - (hours * 3600)) / 60);
    const seconds = sec - (hours * 3600) - (minutes * 60);

    let text = "";

    if(hours > 0)
    {
        text += hours   + ' hour';
        if (hours != 1)
            text += 's';
        text += ' ';
    }

    if(minutes > 0)
    {
        text += minutes + ' minute';
        if (minutes != 1)
            text += 's';
        text += ' ';
    }

    if(seconds > 0)
    {
        text += seconds + ' second';
        if(seconds != 1)
            text += 's';
    }

    return text;
}

function getColor(idx) {
    return availableColors[idx % availableColors.length];
}

function _getElementColor(categoryName, label) {
    return elements[categoryName].labels[label]["active"] ? elements[categoryName].labels[label]["color"] : INACTIVE_COLOR;
}