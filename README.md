# StatsServer

This project is used to give you an overview of a computer and its system resources.
There are graphs showing the history of the data. You can zoom in on the graphs and select any given moment on the graph to see the data for this time.

![Screenshot from 2019-03-30 14-51-05](https://user-images.githubusercontent.com/3453076/55277078-4a1a8900-52fc-11e9-89e6-4c66d082e14a.png)
![Screenshot from 2019-03-30 14-51-41](https://user-images.githubusercontent.com/3453076/55277083-5a326880-52fc-11e9-969a-e415f589fdf9.png)
![Screenshot from 2019-03-30 14-52-07](https://user-images.githubusercontent.com/3453076/55277085-5dc5ef80-52fc-11e9-8303-aa85dd0b2bfb.png)


# How to run everything
There are two files you have to run. One is the `generator.py` which stores the data in an SQLite-database.

```
python3 generator.py # assuming Python 3.6

```

The other file is the `server.py` which runs a flask server where clients can connect to using a browser. 
At the moment the client is designed to be accessed from a mobile phone. You can even use the website as a Progressive Web App.

```
python3 server.py # assuming Python 3.6
```

Then you can connect to the server using a browser by visiting `<ip-address>:5050`.

# Used software
- Python 3.6+
- Flask + FlaskSocketIO
- SQLite
- psutils

Install all python dependencies by running:

```
pip install requirements -r --user
```
# The client
At the moment the client is only designed for mobile phones. (A desktop version will follow soon).

The client can update automatically or only when you press the refresh button.
You can adjust the timerange of the graphs with the dropdown on the top-left.

You can use pinch to zoom the graph.

When using one touch in the upper half of the graph you can move the cursor.

When using one touch in the lower half of the graph you can move the graph.

# Settings
The project stores the database in `/var/ramdisk/`. If you want to use a different directory you have to adjust this in `generator.py`.

You can also adjust the port to connect to. By default the port is `5050`. This can be adjusted in the `server.py` at the bottom of the file.

By default data is gathered every 10 seconds. You can adjust this by setting `TIME_STEP` in `generator.py`.

Data will be stored 24 hours. Every dataset older than this will be deleted. This can be adjusted in `generator.py` by setting the variable `MAX_AGE`.

# How to add your own data to the graphs
You can add your own data by modifying the `gather_data()` function in `generator.py`.
Just add your own data to the `data`-dictionary. By using `create_category` you will get an object with all the needed fields which you can then fill with data.
The key will be used as the label for the category. Your data has to have a field `entries` where you store your current values.

There is also a field `settings`. At the moment the only value that can be used is `nograph` to avoid showing graphs. By default this is used to avoid showing graphs for the remaining space of the disks. 

For some examples more just check out the already existing functions called in `gather_data()` to provide data.

# Future
Make UI responsive to be able to be used from the desktop.
