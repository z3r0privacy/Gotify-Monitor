import requests as r, argparse, os, json
from datetime import datetime, timedelta, timezone
from dateutil import parser


errs = []
dt_placeholder = datetime(1,1,1,0,0,tzinfo=timezone.utc)

def get_channel_id(gotify_url, gotify_apikey, channel_name):
    try:
        resp_channels = r.get(f"{gotify_url}/application", headers={"X-Gotify-Key": gotify_apikey})
        if not resp_channels.ok:
            errs.append(f"{channel_name}: api call returned {resp_channels.status_code}")
            return -1
        for channel in resp_channels.json():
            if channel['name'] == channel_name:
                return channel['id']
    except Exception as e:
        errs.append(repr(e))
        return -1
    errs.append(f"Could not find channel named '{channel_name}'")
    return -1

def query_channel(gotify_url, gotify_apikey, channel):
    cid = get_channel_id(gotify_url, gotify_apikey, channel['name'])
    if cid == -1:
        return
    
    try:
        look_back = datetime.now(timezone.utc) - timedelta(hours=channel['query_hours']+1)
        resp_messages = r.get(f"{gotify_url}/application/{cid}/message", headers={"X-Gotify-Key": gotify_apikey})
        if not resp_messages.ok:
            errs.append(f"{channel['name']}: api call returned {resp_messages.status_code}")
            return None
        newest_start = dt_placeholder
        newest_end = dt_placeholder
        unexpected_tmp = []
        for message in resp_messages.json()['messages']:
            message_date = parser.isoparse(message['date']).astimezone(timezone.utc)
            if message_date >= look_back:
                if message['title'] == channel['expected_start']:
                    if message_date > newest_start:
                        newest_start = message_date
                elif message['title'] == channel['expected_stop']:
                    if message_date > newest_end:
                        newest_end = message_date
                elif message['title'] not in channel['ignored_titles']:
                    unexpected_tmp.append((message_date, message['title']))
        
        unexpected = []
        for dt, msg in unexpected_tmp:
            if dt > newest_start:
                if dt < newest_end or newest_end <= newest_start:
                    unexpected.append(msg)

        return newest_start, newest_end, unexpected
    except Exception as e:
        errs.append(repr(e))
    return None

def create_prtg_xml(results):
    """
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

    <prtg>
        <result>
            <channel>Kometa</channel>
            <value>1</value>
            <ValueLookup>gotifyMessages.lookups</ValueLookup>
        </result>
    </prtg>
    """

    textlist = []
    textlist.extend(errs)

    xml = "<prtg>"
    for channel, max_runtime_minutes, start, end, unexpected in results:
        res = -1
        if end > start and len(unexpected) == 0:
            res = 1
        elif end > start and len(unexpected) > 0:
            res = 2
        elif start == dt_placeholder and end == dt_placeholder and len(unexpected) == 0:
            res = 5
        elif end <= start and (datetime.now(timezone.utc) - start).total_seconds()/60 < max_runtime_minutes:
            res = 3
        elif end < start:
            res = 4
        xml += f"<result><channel>{channel}</channel><value>{res}</value><valueLookup>gotifyMessages.lookups</valueLookup></result>"
        if len(unexpected) > 0:
            textlist.append(f"{channel}: {', '.join(unexpected)}")
    
    if errs:
        xml += "<error>1</error>"
    if len(textlist) > 0:
        xml += "<text>" + '\n'.join(textlist) + "</text>"

    xml += "</prtg>"
    return xml

if __name__ == "__main__":

    arpgarser = argparse.ArgumentParser(description="Reads defined channels from Gotify and creates data for a PRTG sensor channel-wise")
    arpgarser.add_argument("config_file", help="Path to the config.json")

    args = arpgarser.parse_args()

    if not os.path.exists(args.config_file):
        print(f"Could not find {args.config_file}")
        exit(1)

    config = json.load(open(args.config_file))

    results = []
    for channel in config['channels']:
        if channel['enabled']:
            res = query_channel(config['gotify_url'], config["gotify_client_key"], channel)
            if res is not None:
                results.append((channel['name'], channel['max_runtime_minutes'], *res))

    print(create_prtg_xml(results))
