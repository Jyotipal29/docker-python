# docker-python

# cmd for build image 
 docker build -t test-image .
# check image 
docker images

# run the image 
docker run --name test-container -p 80:80 test-image

# stop fastapi container 
docker stop test-container 


# list all the active container 
docker ps 

