BUILD=prod2
sudo rm -rf Videos
git checkout Videos
ls ./Videos | grep -v Dune.mp4 | xargs -i rm ./Videos/{} -r
if [ "$BUILD" = "prod" ]; then
    docker-compose -f docker-compose-$BUILD.yml build
fi
docker-compose -f docker-compose-$BUILD.yml down -v 
docker-compose -f docker-compose-$BUILD.yml run --rm web ./wait-for-it.sh db:5432 -- python3 manage.py migrate
docker-compose -f docker-compose-$BUILD.yml run --rm web python3 manage.py createsuperuser
docker-compose -f docker-compose-$BUILD.yml up 
