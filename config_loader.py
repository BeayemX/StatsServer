import sys
import json
import argparse

parser = argparse.ArgumentParser(description="A setting-config file can be specified.")
parser.add_argument("-c", "--conf", help="path to the config file")
args = parser.parse_args()

def load():
    config_path = 'config.json'

    if args.conf and os.path.isfile(args.conf):
        conf_path = args.conf
        print("Using alternative config file", conf_path)
        config_path = os.path.join(os.path.dirname(__file__), conf_path)

    try:
        with open(config_path) as jf:
            conf = json.load(jf)
    except Exception as e:
        print(e)
        sys.exit(-1)

    return conf