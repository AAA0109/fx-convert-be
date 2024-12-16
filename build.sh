#! /bin/bash

echo '*****************************'
echo '** Starting Frontend Build **'
echo '*****************************'

cd frontend || exit

# Installing the dependencies
npm install

# Building the frontend
yarn build

# Moving files at the build root inside a root subdirectory
for file in $(ls build | grep -E -v '^(index\.html|static|root)$'); do
    mv "build/$file" build/root;
done

cd ..

ls frontend/build

echo '*****************************'
echo '** Finishing Frontend Build *'
echo '*****************************'
