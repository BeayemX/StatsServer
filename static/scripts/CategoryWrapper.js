class CategoryWrapper {
    constructor(category, labels, categoryData) {
        this.colorCounter = 0;
        this.labels = {}

        this.wrapper = document.createElement("div");

        let att = document.createAttribute("class");
        att.value = "graphWrapper";
        this.wrapper.setAttributeNode(att);

        // Create category title
        let tr = document.createElement("tr");
        att = document.createAttribute("class");
        att.value = "tr categoryTitle";
        tr.setAttributeNode(att);
        tr.innerText = category.toUpperCase();

        this.wrapper.appendChild(tr);

        // Create rows
        for (const label of labels) {
            this._generateLabelEntry(label, category, categoryData);
        }

        // do once
        // create canvas
        if (!categoryData["settings"].includes("nograph"))
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
            this.wrapper.appendChild(tr);

            // Done building DOM-Tree.
            this.canvas = canvas;
            this.div = tr;
        }
    }

    _generateLabelEntry(label, category, categoryData) {
        const graphWrapper = this.wrapper;
        this.colorCounter += 1

        const rowElement = {};
        const color = categoryData["settings"].includes("monochrome") ? getColor(0): getColor(this.colorCounter);

        rowElement["active"] = true;
        rowElement["color"] = color;

        // Only use different colors if there is a graph
        // if (!categoryData["settings"].includes("nograph"))

        let tr = document.createElement("div");
        let att = document.createAttribute("class");
        att.value = "tr";
        tr.setAttributeNode(att);
        tr.onmousedown = (evt) => {this._categoryRowPressed(evt, rowElement, categoryData, category);};
        rowElement["tr"] = tr;

        // Label
        let td = document.createElement("td");
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

        let canvas = document.createElement("canvas");
        td.appendChild(canvas);

        rowElement["bar"] = canvas;

        tr.appendChild(td);

        att = document.createAttribute("style");
        att.value = "color:" + color;
        tr.setAttributeNode(att);
        graphWrapper.appendChild(tr);

        this.labels[label] = rowElement;

        // if entry is added during runtime
        // make sure that canvas is the last displayed element
        if (this.canvas) {
            console.log("should move canvas to back")
            // move div containing the graph to last position
            this.wrapper.appendChild(this.div);
        }
    }

    _categoryRowPressed(evt, rowElement, categoryData, categoryName) {
        if (categoryData["settings"].includes("nograph"))
            return;

        const oldActive = rowElement["active"];
        const newActive = !oldActive
        const color = newActive ? rowElement["color"] : INACTIVE_COLOR;
        const att = document.createAttribute("style");

        rowElement["active"] = newActive;

        att.value = "color:" + color;
        rowElement["tr"].setAttributeNode(att);

        _updateBars(categoryData, categoryName);

        if (_getActiveEntries(categoryName, categoryData).length == 0)
        {
            this.canvas.remove();
        } else {
            if (oldActive == false && newActive == true)
            {
                this.div.appendChild(this.canvas);
            }

            _updateCanvas(categoryName, categoryData, this.canvas);
        }
    }

    getColorForEntry(label) {
        return this.labels[label].color;
    }
}