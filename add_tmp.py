import sys
import random

def main():
     f= open("url_objects1.file","w+")
     nb = int(sys.argv[3])
     for i in range(nb):
         url ="http://"+ sys.argv[1] + ":31380/blur"
         f.write(url + " " + sys.argv[2] +"\n")
     f.close()


if __name__== "__main__":
  main()
