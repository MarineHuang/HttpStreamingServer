BUILD=prod
if [ ! -d "/home/StreamServer/Videos" ];then
    mkdir -p /home/StreamServer/Videos
fi
if [ ! -d "/home/StreamServer/torrent" ];then
    mkdir -p /home/StreamServer/torrent
fi
if [ ! -d "/home/StreamServer/database" ];then
    mkdir -p /home/StreamServer/database
fi

if [ "$BUILD" = "prod" ]; then
    docker-compose -f docker-compose-$BUILD.yml build
fi
docker-compose -f docker-compose-$BUILD.yml down 
#docker-compose -f docker-compose-$BUILD.yml run --rm web ./wait-for-it.sh db:5432 -- python3 manage.py makemigrations
docker-compose -f docker-compose-$BUILD.yml run --rm web ./wait-for-it.sh db:5432 -- python3 manage.py migrate
docker-compose -f docker-compose-$BUILD.yml run --rm web python3 manage.py createsuperuser
docker-compose -f docker-compose-$BUILD.yml up -d
docker-compose -f docker-compose-$BUILD.yml logs -f
