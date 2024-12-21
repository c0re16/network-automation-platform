# network-automation-platform


What it can do on the back end:

- get
- delete
- update
- populate devices variables on device __init__
- establish ssh connections to cisco devices and push configuraiton changes.

What it can do on the front and:
- Endoll device, networks, device interfaces, and device_network_interfaces
- View devices & networks tables

![Screenshot of the dashboard](static/screenshot.png)


## Usage

To set up the environment, please execute some form of the following commands:

`python3 -m venv .env && source .env/bin/activate && pip3 install -r reqirements.txt`

and to run it:

`python3 app.py`