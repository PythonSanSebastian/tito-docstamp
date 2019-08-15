# tito-docstamp

A dockerised setup to generate badges from Tito CSV files and docstamp

## Prepare the script

Every conference has a specific Ti.to setup and different requirements for the badges.
It is hard to make a generic one, but we tried with the `conferences/default.py` file.
Otherwise I invite you to create a new conferences file defining `invoke` tasks
to process the Ti.to Attendees file and call all of them from the `inv all` task.

Then you can change the import in the `tasks.py` file.

Feel free to make a PR to this project adding your new conference file.

## Install dependencies

Make sure you have Docker correctly installed, and install docker-compose:

```bash
pip install docker-compose
```

## Build the container

Change directory to the root folder of this project,

```bash
docker-compose build
```

## Run and bash into the container

Go to where you have your data, and run the container with:

```bash
docker-compose run badges
```

## Installing extra fonts

You can install more fonts by copying the files to the `fonts` folder
before building the container.
