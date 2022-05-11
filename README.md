# Dichroview

Dashboard for viewing live data, as it is collected and published
to a bluesky-compatible event stream. Includes an API for notifying
the viewer when new data stream and data sream events are available.

In this proof-of-concept example, live data is emulated by replaying
a data stream from a databroker instance. The data is streamed to a 
publisher object that can be registered as a callback to a bluesky
RunEngine instance. The publisher makes calls to the Dichroview API 
to notofify the dashboard viewer that data is available for display.

This project brings together a number of notable features:

* In-the-browser visualization of a "live" data stream
    * Uses plotly dash for rapid prototyping and customization
    * Same experience for on-site and remote beamline users
* Web-based API for push-based data stream notifications
* Websockets for subscribing multiple viewer clients
    * Push notifications go to all subscribers
* Data stream publisher that can be registered as a callback to
  a bluesky RunEngine

The data from this example is a seeries of XMCD spectra collected
at ALS Beamline 4.0.2 (_XMCD_ = x-ray magnetic circular dichroism).

Usage
---

1. Clone this repository

    ```bash
    git clone https://github.com/als-computing/dichroview.git
    ```

2. Create an isolated environment

    ```bash
    conda env create --file environment.yml
    ```

3. Copy 'catalogs.yml' to the path where 'intake' looks for catalogs

    ```bash
    cp catalogs.yml ~/opt/miniconda3/envs/dash_fastapi_2/share/intake/
    ```

2. Set up the needed ENVironment VARiables

    ```bash
    DATABROKER_MONGO_HOST=<HOST-NAME-OR-IP>:<27017 or PORT>
    DATABROKER_MONGO_USER=<User with read access to Mongo db>
    DATABROKER_MONGO_PASSWORD=<Password for MONGO_USER>

    DEBUG=False  # or True for debug mode
    ```

3. Start the DichroView server

    ```bash
    uvicorn dichroview:app --port 8003

    # or get the same result by running the 'dichroview' script
    python dichroview.py
    ```

4. Open a DichroView client in one or more browsers

    ```
    URL -- http://127.0.0.1:8003/dash
    ```

5. Start the data stream

    ```
    python newest_run.py
    ```

6. Watch data being broadcast to each client

    * If data does not display correctly, it might be because
      events are being streamed too quickly for the dichroview server
      to keep up. Try reducing the rate of the data stream.
    * In 'newest_run.py': Increase the delay time used by the 
      `ApiDelayedCallback` object that publishes data to the API.

    ```python
    # Default delay value is 0.1 sec.
    send_to_api = ApiDelayedCallback(port=8003, delay=0.1)

    # Increase the delay value to 0.2 sec.
    send_to_api = ApiDelayedCallback(port=8003, delay=0.2)
    ```

Demonstration
---

[This video](https://github.com/als-computing/dichroview/blob/main/assets/dichroview.mov) 
shows two browser tabs, each running a DichroView client, as data
is streamed from a separate process.
