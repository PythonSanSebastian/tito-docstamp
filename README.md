# tito-docstamp

A dockerised setup to generate badges from Tito CSV files and docstamp

## Install dependencies

Make sure you have Docker correctly installed, and install docker-compose:

```
pip install docker-compose
```

## Build the container

Change directory to the root folder of this project, 

```
docker-compose build
```

## Run and bash into the container

Go to where you have your data, and run the container with:

```
docker-compose run badges
```

## Installing extra fonts

You can install more fonts from within the container with:

```
cp <font_files> /usr/local/share/fonts
fc-cache -f -v
```