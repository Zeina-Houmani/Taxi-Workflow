#!/usr/bin/env python3

import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import  random
import sys


start_list = {}
end_list = {}
latency = {}

def send(tripID, clientID, taxiID, distance):
	url = "http://" + sys.argv[2] + ":" + sys.argv[3] + "/trip/" + str(tripID) + "/" + str(clientID) + "/" + str(taxiID) + "/" + str(distance)
	response = requests.get(url)


def send_request():
	with ThreadPoolExecutor(max_workers=10) as pool:
		for i in range(int(sys.argv[1])):
			list(pool.map(send(random.randint(1,10000), 123, 333, 456)))

def start_latency():
	url = "http://" + sys.argv[2] + ":9600/trip/latency"
	response = requests.get(url)
	global start_list
	start_list = response.json()
	print (start_list)


def end_latency():
	url = "http://" + sys.argv[4] + ":9800/payement/latency"
	response = requests.get(url)
	global end_list
	end_list= response.json()
	print (end_list)


def calculate_latency():
	for key, value in start_list.items():
		time_start = datetime.strptime(value, '%H:%M:%S.%f')
		time_end = datetime.strptime(end_list.get(key), '%H:%M:%S.%f')
		diff = time_end - time_start
		print (diff)
		diff_sec = int(diff.total_seconds() * 1000)
		global latency
		latency[key]=diff_sec


def calculate_avg():
	total = 0
	for key, value in latency.items():
		total += value
	average = total/len(latency)
	return average


send_request()
start_latency()
end_latency()
calculate_latency()
print (calculate_avg())


