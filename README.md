# PRTG Gotify Monitor

A little script that relies on Gotify channels to create PRTG sensor data for monitoring of small scripts.

The script searches for defined start/stop messages within a given timespan. If those are not found, or other messages are found, it is assumed something went wrong or needs attention. Known messages that are expected but neither start or stop can be ignored.

# Setup

## server

- Clone repository
- Create venv
- Install requirements from `requirements.txt`
- Create a config.json (see config section below)

Since this is a python script and PRTG relies on bash scripts it is recommended to create a shell script in `/var/prtg/scriptsxml`.

```bash
#!/bin/bash
/path/to/monitor/venv/bin/python /path/to/monitor/query_notify.py /path/to/your/config.json
```

## PRTG

You'll need SSH access from PRTG to the server working. Then, you'll be able to create a SSH Advanced Sensor pointing to the script created above.

### Prerequisites

For this sensor to work, a custom lookup mapping is required. Create a new `*.ovl` file (e.g. `gotifyMonitorLookups.ovl`) in your PRTG core server install node. The path is `[PRTG Install Directory]\lookups\custom`. The content of the file is shown below.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ValueLookup id="gotifyMessages.lookups" desiredValue="1" undefinedState="Warning" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="PaeValueLookup.xsd">
<Lookups>
    <SingleInt state="Ok" value="1">
        OK Status
    </SingleInt>
    <SingleInt state="Warning" value="2">
        OK Status with unexpected Logs
    </SingleInt>
    <SingleInt state="Warning" value="3">
        No Stop Message, within limit
    </SingleInt>
    <SingleInt state="Error" value="4">
        Unexpected Logs or not ended in time
    </SingleInt>
    <SingleInt state="Error" value="5">
        No Logs in requested Time
    </SingleInt>
</Lookups>
</ValueLookup>
```

After creating the file, in PRTG admin interface, go to `Setup -> System Administration -> Administrative Tools` and execute `Load Lookups and File Lists`.

# Configuration

A minimal configuration may looks like this. The minimal required configuration is the base url of the Gotify server and a valid key. The key can be created in Gotify UI under clients.

```json
{
    "gotify_url": "https://gotify.domain.local",
    "gotify_client_key": "abcdef123456",
    "channels": [
        {
            "name": "Kometa",
            "enabled": true,
            "query_hours": 48,
            "max_runtime_minutes": 60,
            "expected_start": "Run Started",
            "expected_stop": "Run Completed",
            "ignored_titles": ["Playlist Modified"]
        }
    ]
}
```

## Channels

A channel has the following configurable options:

| Option | Type | Description |
| --- | --- | --- |
| name | string | The name of the channel in Gotify |
| enabled | bool | If False, the channel will not be monitored |
| query_hours | int | How many hours back from now are messages considered. This value should reflect the interval a script is expected to run at. e.g. if a script runs daily, put 24 in here |
| max_runtime_minutes | int | Max number of minutes the monitored script is expected to finish. This is used to account for scenarios where the script is running while fetching the messages |
| expected_start | string | the title of the script start message |
| expected_stop | string | the title of the script stop message |
| ignored_titles | list of strings | titles of messages that are logged to Gotify that are expected but neither start or stop |
