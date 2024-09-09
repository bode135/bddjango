# bash xxx.sh
# move into docker contianer by match fuzzy name.

fuzzy_name=$1
container_name=`docker ps --format='{{.Ports}} {{.Names}}' | grep -i $fuzzy_name | awk '{print $NF}'`

echo ""
echo "|    Image    |    ContainerName    |       Ports              | ---------"
echo ""

docker ps --format='| {{.Image}} | {{.Names}} | {{.Ports}}  |' | grep -i --color=auto "$fuzzy_name"

echo ""
echo "----------------------------------------------------------"
echo  "------ fuzzy_name: $fuzzy_name"
echo  "------ container_name: $container_name"

docker exec -it $container_name bash
