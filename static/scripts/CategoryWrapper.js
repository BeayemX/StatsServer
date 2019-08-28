const scaleUnits = ["", " %", "byte", " °C"];

class CategoryWrapper {
    get_name_for_local_storage() {
        return this.category + "_unit";
    }

    constructor(category, labels, categoryData) {
        // Caching, not sure if needed
        this.category = category;
        this.initialCategoryData = categoryData; // This will not be updated!

        // Configuration
        this.autoScale = true;
        this.showCircleHighlight = true;

        // this.unit = JSON.parse(localStorage.getItem(this.get_name_for_local_storage()));
        this.initialUnitIndex = localStorage.getItem(this.get_name_for_local_storage()) || 0;
        this.unit = scaleUnits[this.initialUnitIndex];

        // Members
        this.labels = {}
        this.wrapper = document.createElement("div");

        // Initialization
        let att = document.createAttribute("class");
        att.value = "graphWrapper";
        this.wrapper.setAttributeNode(att);

        // Create category title
        const categoryHeader = document.createElement("div");

        att = document.createAttribute("class");
        att.value = "tr categoryHeader";
        categoryHeader.setAttributeNode(att);

        const leftIcons = document.createElement("div");
        att = document.createAttribute("class");
        att.value = "tr categoryTitle";
        leftIcons.setAttributeNode(att);
        categoryHeader.appendChild(leftIcons);

        const circleHighlight = document.createElement('div');
        att = document.createAttribute("class");
        att.value = "categoryheadericon";
        circleHighlight.setAttributeNode(att);

        circleHighlight.innerText = "◯";
        circleHighlight.onmousedown = (evt) => this.toggleCircleHighlight();
        leftIcons.appendChild(circleHighlight);

        /*
        const circleHighlight2 = document.createElement('div');
        att = document.createAttribute("class");
        att.value = "categoryheadericon";
        circleHighlight2.setAttributeNode(att);
        circleHighlight2.innerText = "X";
        circleHighlight2.onmousedown = (evt) => this.toggleCircleHighlight();
        leftIcons.appendChild(circleHighlight2);
        //*/




        const headerLabel = document.createElement("div");
        att = document.createAttribute("class");
        att.value = "tr categoryTitle";
        headerLabel.setAttributeNode(att);
        headerLabel.innerText = category.toUpperCase();
        categoryHeader.appendChild(headerLabel);

        // right icons
        const rightIcons = document.createElement("div");
        att = document.createAttribute("class");
        att.value = "tr categoryTitle";
        rightIcons.setAttributeNode(att);
        //rightIcons.innerText = "↕";
        //rightIcons.onmousedown = (evt) => this.toggleAutoScale();
        categoryHeader.appendChild(rightIcons);


        //*
        const autoscaleToggle = document.createElement("div");
        att = document.createAttribute("class");
        att.value = "categoryheadericon";
        autoscaleToggle.setAttributeNode(att);

        autoscaleToggle.innerText = "↕";
        autoscaleToggle.onmousedown = (evt) => this.toggleAutoScale();
        rightIcons.appendChild(autoscaleToggle);
        // */

        const unitDropdown = document.createElement('select');
        att = document.createAttribute("class");
        att.value = "unitselection unitselectionLabel categoryheadericon";
        unitDropdown.setAttributeNode(att);

        // asdf
        unitDropdown.onchange = () => {
            this.unit = scaleUnits[unitDropdown.selectedIndex];
            localStorage.setItem(this.get_name_for_local_storage(), unitDropdown.selectedIndex);
            this.redraw();
        };

        let option;

        for (let unit of scaleUnits) {
            option = document.createElement('option');
            option.value = unit;
            option.innerHTML = unit;
            unitDropdown.appendChild(option);
        }
        unitDropdown.selectedIndex = this.initialUnitIndex;
        rightIcons.appendChild(unitDropdown);

        /*
        const autoscaleToggle2 = document.createElement("div");
        att = document.createAttribute("class");
        // att.value = "tr categoryTitle";
        //rightIcons.setAttributeNode(att);
        autoscaleToggle2.innerText = "↕";
        autoscaleToggle2.onmousedown = (evt) => this.toggleAutoScale();
        rightIcons.appendChild(autoscaleToggle2);
        //*/


        this.wrapper.appendChild(categoryHeader);

        // Create rows
        for (const label of labels) {
            this._generateLabelEntry(label, category, categoryData);
        }

        // do once
        // create canvas
        let tr;
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
        const rowElement = {};
        rowElement["active"] = true;

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
        td.innerText = label;

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
        rowElement["htmlnode"] = tr;

        tr.appendChild(td);

        graphWrapper.appendChild(tr);

        this.labels[label] = rowElement;

        this._sortLabelEntries();
    }

    _setRowColor(htmlNode, color) {
        const att = document.createAttribute("style");
        att.value = "color:" + color;
        htmlNode.setAttributeNode(att);
    }

    _sortLabelEntries() {
        let colorCounter = 0;

        let items = Object.keys(this.labels).map((key) =>  {
            return [key, this.labels[key]];
        });

        items.sort((first, second) => {
            return first[1]["label"].innerText.localeCompare(second[1]["label"].innerText);
        });

        this.recalculateAvailableColors(items.length);
        for (let item of items) {
            const color = this.initialCategoryData["settings"].includes("monochrome") ? this.getColor(0): this.getColor(colorCounter);
            item[1]["color"] = color;

            const htmlNode = item[1]["htmlnode"]
            this._setRowColor(htmlNode, color);
            this.wrapper.appendChild(htmlNode);

            colorCounter += 1;
        }

        // if entry is added during runtime
        // make sure that canvas is the last displayed element
        if (this.canvas) {
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

    toggleAutoScale() {
        this.autoScale = !this.autoScale;
        _updateCanvas(this.category, cachedData["categories"][this.category], this.canvas);
    }

    toggleCircleHighlight() {
        this.showCircleHighlight = !this.showCircleHighlight;
        _updateCanvas(this.category, cachedData["categories"][this.category], this.canvas);
    }

    redraw() { // HACK
        let categoryData = cachedData["categories"][this.category];
        _updateBars(categoryData, this.category);
        _updateCanvas(this.category, categoryData, elements[this.category].canvas);
        console.log("Should redraw: ", this.unit)
    }

    recalculateAvailableColors(maxNum) {
        maxNum = Math.max(maxNum, 6);
        const useWhite = true;

        this.availableColors = [];
        if (useWhite) {
            this.availableColors.push("#ddddddff");
            maxNum -= 1;
        }

        const stepsize = 1.0 / maxNum;
        const offset = stepsize * (maxNum/2);
        const SATURATION = 0.75;

        for (let i=0; i<maxNum; ++i) {
            this.availableColors.push(this._HSLToRGB(offset - i * stepsize, SATURATION, 0.5));
        }
    }

    _HSLToRGB(h,s,l) {
        let r, g, b;

        if(s == 0) {
            r = g = b = l; // achromatic
        } else {
            let hue2rgb = function hue2rgb(p, q, t){
                if(t < 0) t += 1;
                if(t > 1) t -= 1;
                if(t < 1/6) return p + (q - p) * 6 * t;
                if(t < 1/2) return q;
                if(t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                return p;
            }

            let q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            let p = 2 * l - q;

            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }

        r = Math.round(r * 255);
        g = Math.round(g * 255);
        b = Math.round(b * 255);

        return `rgba(${r}, ${g}, ${b}, 1)`;
    }


    getColor(idx) {
        return this.availableColors[idx % this.availableColors.length];
    }
}