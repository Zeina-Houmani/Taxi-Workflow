import requests

url = 'http://mirror.filearena.net/pub/speed/SpeedTest_2048MB.dat?_ga=2.214932319.973892181.1585884968-607421180.1585884968'

for t in  range(50):
      print('Download a file ... ')
      r = requests.get(url)
