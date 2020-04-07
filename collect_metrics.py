import requests
import sys
import time
import datetime
from argparse import ArgumentParser
from kubernetes import client, config
from pprint import pprint
import json
from collections import OrderedDict

POD_IP = ''
APP_PORT = 0
URI = []
counter_dict = OrderedDict()
dict_to_file = OrderedDict()


def get_metrics(START_TIME, END_TIME):
	global POD_IP
	global APP_PORT
	global URI
	global counter_dict
	global dict_to_file

	config.load_kube_config()
	v1 = client.CoreV1Api()
	services_list= v1.list_namespaced_service("default")
	for service in services_list.items:
		APP_NAME = service.metadata.name
		APP_PORT = service.spec.ports[0].port
		key = service.metadata.labels.keys()[0]
		value = service.metadata.labels.values()[0]
		URI= value.split("-")
		if key != "component":
			print("collect metrics from *" + URI[0] + "* instances ... ")
			label = key + "=" + value
			service_counter =0
			pod_list = v1.list_namespaced_pod("default", label_selector=label)
			for pod in pod_list.items:
				POD_IP = pod.status.pod_ip
				#print("%s\t%s" % (pod.metadata.name, pod.status.pod_ip))
				result = get_Requests_counter()
				if result != "None":
					service_counter += int(result)
			counter_dict[APP_NAME] = service_counter
	dict_to_file['Received requests'].append(counter_dict)
	dict_to_file["Start time"] = START_TIME
	dict_to_file["End time"] = END_TIME
	get_metrics_app()
	with open('result.json', 'w') as fp:
        	 json.dump(dict_to_file, fp,  indent=4)



def get_metrics_app():
	global POD_IP
	global APP_PORT
	global URI
	metrics_app = {}
	app_counter =0
	config.load_kube_config()
	core_api = client.CoreV1Api()
	apps_api = client.AppsV1Api()
	namespace_name = "default"
        apps_list= core_api.list_namespaced_service(namespace_name)
	for app in apps_list.items:
		APP_NAME = app.metadata.name
		metrics_app["name"] = APP_NAME
		key = app.spec.selector.keys()[0]
		value = app.spec.selector.values()[0]
		label = key + "=" + value
		deployment = apps_api.list_namespaced_deployment(namespace_name, label_selector=label)
		metrics_app["replicas"] =  deployment.items[0].spec.replicas
		containers_list = deployment.items[0].spec.template.spec.containers
		total_limit_cpu = 0
		total_limit_mem = 0
		total_limit_disk = 0
		for container in containers_list:
			limits = container.resources.limits
			print container
			print limits
#			if not limits:
			total_limit_cpu = total_limit_cpu + int(limits["cpu"][:-1])
			total_limit_mem = total_limit_mem + int(limits["memory"][:-2])
			total_limit_disk = total_limit_disk + int(limits["ephemeral-storage"][:-2])	
		metrics_app["Limit CPU"] = str(total_limit_cpu) + "m"
		metrics_app["Limit RAM"] = str(total_limit_mem) + "Mi"
		metrics_app["Limit Storage"] = str(total_limit_disk) + "Gi"
        dict_to_file['Microservices'].append(metrics_app)
	#print dict_to_file


	
	
	
def test():
	global POD_IP
	global APP_PORT
	global URI
	metrics_app = {}
	app_counter =0
	config.load_kube_config()
	core_api = client.CoreV1Api()
	apps_api = client.AppsV1Api()
	namespace_name = "default"
        apps_list= core_api.list_namespaced_service(namespace_name)
	for app in apps_list.items:
		APP_NAME = app.metadata.name
		metrics_app["name"] = APP_NAME
		key = app.spec.selector.keys()[0]
		value = app.spec.selector.values()[0]
		label = key + "=" + value
		pod_list = core_api.list_namespaced_pod(namespace_name, label_selector=label)
		metrics_app["replicas"] =  len(pod_list.items)
		containers_list = pod_list.items[0].spec.containers
		print len(containers_list)
		total_limit_cpu = 0
		total_limit_mem = 0
		total_limit_disk = 0
		for container in containers_list:
			limits = container.resources.limits
			print container
			print limits
#			if not limits:
			total_limit_cpu = total_limit_cpu + int(limits["cpu"][:-1])
			total_limit_mem = total_limit_mem + int(limits["memory"][:-2])
			total_limit_disk = total_limit_disk + int(limits["ephemeral-storage"][:-2])	
			print "__________________"
		metrics_app["Limit CPU"] = str(total_limit_cpu) + "m"
		metrics_app["Limit RAM"] = str(total_limit_mem) + "Mi"
		metrics_app["Limit Storage"] = str(total_limit_disk) + "Gi"
        dict_to_file['Microservices'].append(metrics_app)
	#print dict_to_file

#def set_Default():
#	core_api = client.CoreV1Api()
	#limitRange_list= core_api.list_namespaced_limit_range("default")
#	 api_response = api_instance.read_namespaced_limit_range(name, namespace, pretty=pretty, exact=exact, export=export)



def get_Requests_counter():
	metric_URL= "http://"+ POD_IP + ":"+ str(APP_PORT) + "/" + URI[0] + "/metric"
	response = requests.get(metric_URL)
  	if response.status_code == 404:
		return "None"
  	else:
		return response.json()



if __name__ == "__main__":
 	test()
	#get_metrics_app()
