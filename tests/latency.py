#!/usr/bin/env python

import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import  random
import sys
import csv

start_list = {}
end_list = {}
latency = {}

def send(tripID, clientID, taxiID, distance):
	url = "http://" + sys.argv[2] + ":31380" + "/trip/" + str(tripID) + "/" + str(clientID) + "/" + str(taxiID) + "/" + str(distance)
	response = requests.get(url)


def send_request():
	with ThreadPoolExecutor(max_workers=10) as pool:
		for i in range(int(sys.argv[1])):
			x=random.randint(1,10000)
#			print (x)
			list(pool.map(send(x, 123, 333, 456)))

def start_latency():
	url = "http://" + sys.argv[2] + ":31380/trip/latency"
	response = requests.get(url)
	global start_list
	start_list = response.json()


def end_latency():
	url = "http://" + sys.argv[2] + ":31380/payement/latency"
	response = requests.get(url)
	global end_list
	end_list= response.json()


def calculate_latency():
	for key, value in start_list.items():
		time_start = datetime.strptime(value, '%H:%M:%S.%f')
		time_end = datetime.strptime(end_list.get(key), '%H:%M:%S.%f')
		print ( "****************")
		print (time_start)
		print (time_end)
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


def save_results(result):
	with open('latency.csv', 'a') as file:
	    writer = csv.writer(file)
	    writer.writerow([sys.argv[1], result , "one"])


#send_request()
start_latency()
end_latency()
calculate_latency()
result = calculate_avg()
save_results(result)


