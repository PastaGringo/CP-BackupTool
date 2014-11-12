#!/usr/bin/env python
import sys
import urllib
import os.path
import ConfigParser
import json 
from pprint import pprint 
import argparse

# Validate mandatory values
def validateConf(config, section, confFile):
    default_host = 'localhost'
    default_port = 5050
    default_ssl = "off"
    config_list = config.items(section)
    for item in config_list:
        # Check host value in cfg
        if item[0] == 'host' and not item[1]:
            print "No value found for '%s' in cfg %s" % (item[0], confFile)
            print "Writing default value '%s' in cfg %s"  % (default_host, confFile)
            config.set(section, item[0], default_host)
            writeConf(config, confFile)

        # Check port value in cfg
        if item[0] == 'port' and not item[1]:
            print "No value found for '%s' in cfg %s" % (item[0], confFile)
            print "Writing default value '%s' in cfg %s"  % (default_port, confFile)
            config.set(section, item[0], str(default_port))
            writeConf(config, confFile)

        # Check apikey value in cfg
        if item[0] == 'apikey' and not item[1]:
            raise ValueError("'%s' can't be empty in cfg %s" % (item[0], confFile))

        # Check ssl value in cfg
        if item[0] == 'ssl' and not item[1]:
            print "No value found for '%s' in cfg %s" % (item[0], confFile)
            print "Writing default value '%s' in cfg %s"  % (default_ssl, confFile)
            config.set(section, item[0], str(default_ssl))
            writeConf(config, confFile)

def writeConf(config, confFile):
    with open(confFile, "w") as conf:
        config.write(conf)
    conf.close()

def apiCall(url):
    print "Opening URL:", url
    try:
        urlObj = urllib.urlopen(url)
    except:
        print "Failed to open URL:", url
        print "Caught following:"
        raise

    result = json.load(urlObj)
    if result:
        return result
    else:
        return None

def process(type, backup):
    config = ConfigParser.ConfigParser()
    if args.cfg:
        configFilename = args.cfg 
    else:
        configFilename = os.path.join(os.path.dirname(sys.argv[0]), "couch.cfg")

    print "Loading config from:", configFilename
    with open(configFilename, "r") as conf:
        config.readfp(conf)

    # Validate config
    validateConf(config, "CouchPotato", configFilename)

    host = config.get("CouchPotato", "host")
    # Must be an INT
    port = config.getint("CouchPotato", "port")
    apikey = config.get("CouchPotato", "apikey")
    # Must be a boolean ("1", "yes", "true", "on", "0", "no" "false" and "off" are supported)
    ssl = config.getboolean("CouchPotato", "ssl")
    web_root = config.get("CouchPotato", "web_root")

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    
    if type == "backup":
        url = protocol + host + ":" + str(port) + web_root + "/api/" + apikey + "/" + "movie.list/?status=active"
        result = apiCall(url)
        backup_list = []
        if result:
            for item in result["movies"]:
                movie_list = []
                if item["identifiers"]["imdb"]:
                    movie_list.append(item["identifiers"]["imdb"])
                    if item["title"]: movie_list.append(item["title"])
                    if item["profile_id"]: movie_list.append(item["profile_id"])
                    backup_list.append(movie_list)
                else:
                    if item["title"]: print "No imdb ID for movie %s, skipping..." % item["title"]
                    else: print "Unable to identify movie, skipping..."
            print "backup list is:", backup_list

            if backup_list:
                print "found %s wanted movies, writing file..." % len(backup_list)
            with open(backup, 'w') as f:
                for movie_list in backup_list:
                    for movie in movie_list:
                        json.dump(movie, f)
                    #    f.write(movie +'\n')
            f.close()
            print "Backup file completed:", backup
        else:
            print "No wanted movies found"

    elif type == "restore":
        with open(backup, 'r') as f:
            imdb_list = [ line.strip() for line in f ]
        f.close()
        baseurl = protocol + host + ":" + str(port) + web_root + "/api/" + apikey + "/" + "movie.add/?identifier="
        for imdb in imdb_list:
            url = baseurl + imdb
            result = apiCall(url)

parser = argparse.ArgumentParser(description='Backup/Restore Couchpotato wanted list',
                                formatter_class=argparse.RawTextHelpFormatter)
# Require this option
parser.add_argument('--type', metavar='backup/restore', choices=['backup', 'restore'],
                    required=True, help='')
parser.add_argument('file', help='''If backup: The file to save the wanted list to.
If restore: The file to restore from.''')
parser.add_argument('--cfg', metavar='cfg-file', help='Specify an alternative cfg file')
args = parser.parse_args()
process(args.type, args.file)
