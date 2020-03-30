import sys
import random

def main():
     f= open("url_objects.file","w+")
     nb = int(sys.argv[3])
     for i in range(nb):
         url ="http://"+ sys.argv[1] + ":31380/trip/" +  str(random.getrandbits(100)) + "/1234/4567/65431"
#         url ="http://"+ sys.argv[1] + ":31380/trip/" +  str(random.randint(1,10000)) + "/1234/4567/65431"
         f.write(url + " " + sys.argv[2] +"\n")
     f.close()


if __name__== "__main__":
  main()
